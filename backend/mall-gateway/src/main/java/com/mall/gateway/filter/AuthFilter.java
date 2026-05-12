package com.mall.gateway.filter;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.http.server.reactive.ServerHttpResponseDecorator;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

@Component
public class AuthFilter implements GlobalFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(AuthFilter.class);

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private static final Set<String> WHITE_LIST = Set.of(
            "/api/v1/users/login",
            "/api/v1/users/register",
            "/api/v1/users/auth/permissions",
            "/api/v1/users/auth/roles"
    );

    private static final Set<String> PUBLIC_PREFIXES = Set.of(
            "/api/v1/products",
            "/api/v1/upload"
    );

    private static final Set<String> PUBLIC_GET_PREFIXES = Set.of(
            "/api/v1/coupons/templates",
            "/api/v1/coupons/available"
    );

    private final ReactiveStringRedisTemplate redisTemplate;

    public AuthFilter(ReactiveStringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getPath().value();
        String method = request.getMethod().name();

        if (isWhiteListed(path)) {
            return chain.filter(exchange);
        }

        if (isPublicGet(path, method)) {
            return chain.filter(exchange);
        }

        String satoken = request.getHeaders().getFirst("satoken");
        if (satoken == null || satoken.isEmpty()) {
            log.warn("未携带token, path={}", path);
            return unauthorized(exchange.getResponse(), "请先登录");
        }

        String tokenKey = "satoken:login:token:" + satoken;
        return redisTemplate.opsForValue().get(tokenKey)
                .flatMap(loginId -> {
                    log.debug("token验证通过, loginId={}, path={}", loginId, path);
                    return chain.filter(exchange);
                })
                .switchIfEmpty(Mono.defer(() -> {
                    log.warn("token无效或已过期, path={}", path);
                    return unauthorized(exchange.getResponse(), "登录已过期，请重新登录");
                }))
                .onErrorResume(e -> {
                    log.warn("token验证异常, path={}, error={}", path, e.getMessage());
                    return unauthorized(exchange.getResponse(), "登录已过期，请重新登录");
                });
    }

    private boolean isWhiteListed(String path) {
        return WHITE_LIST.contains(path);
    }

    private boolean isPublicGet(String path, String method) {
        if (!"GET".equals(method)) {
            return false;
        }
        for (String prefix : PUBLIC_PREFIXES) {
            if (path.startsWith(prefix)) {
                return true;
            }
        }
        for (String prefix : PUBLIC_GET_PREFIXES) {
            if (path.startsWith(prefix)) {
                return true;
            }
        }
        return false;
    }

    private Mono<Void> unauthorized(ServerHttpResponse response, String message) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", 401);
        result.put("message", message);
        result.put("data", null);
        try {
            byte[] bytes = OBJECT_MAPPER.writeValueAsBytes(result);
            DataBuffer buffer = response.bufferFactory().wrap(bytes);
            HttpHeaders writableHeaders = new HttpHeaders();
            writableHeaders.setContentType(MediaType.APPLICATION_JSON);
            ServerHttpResponse decorated = new ServerHttpResponseDecorator(response) {
                @Override
                public HttpHeaders getHeaders() {
                    return writableHeaders;
                }
            };
            decorated.setStatusCode(HttpStatus.UNAUTHORIZED);
            return decorated.writeWith(Mono.just(buffer));
        } catch (JsonProcessingException e) {
            return response.setComplete();
        }
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 1;
    }
}
