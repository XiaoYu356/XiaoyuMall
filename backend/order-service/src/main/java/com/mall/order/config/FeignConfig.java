package com.mall.order.config;

import cn.dev33.satoken.stp.StpUtil;
import feign.RequestInterceptor;
import feign.RequestTemplate;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

@Slf4j
@Configuration
public class FeignConfig {

    /** 与 order/coupon 等各服务 application.yaml 的 internal.secret 一致 */
    @Value("${internal.secret:}")
    private String internalSecret;

    @Bean
    public RequestInterceptor feignRequestInterceptor() {
        return new RequestInterceptor() {
            @Override
            public void apply(RequestTemplate template) {
                // 内部服务间调用凭证：目标服务拦截器据此放行（归属校验仍按业务参数执行）
                if (internalSecret != null && !internalSecret.isEmpty()) {
                    template.header("X-Internal-Secret", internalSecret);
                }
                ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
                if (attributes != null) {
                    String satoken = attributes.getRequest().getHeader("satoken");
                    if (satoken != null && !satoken.isEmpty()) {
                        template.header("satoken", satoken);
                    }
                } else {
                    try {
                        String tokenValue = StpUtil.getTokenValue();
                        if (tokenValue != null && !tokenValue.isEmpty()) {
                            template.header("satoken", tokenValue);
                        }
                    } catch (Exception e) {
                        log.warn("Feign拦截器获取satoken失败: {}", e.getMessage());
                    }
                }
            }
        };
    }
}
