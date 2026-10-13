package com.mall.product.config;

import cn.dev33.satoken.context.SaHolder;
import cn.dev33.satoken.interceptor.SaInterceptor;
import cn.dev33.satoken.stp.StpUtil;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * sa-token 拦截器注册：此前 @SaCheckPermission 等注解因未注册拦截器从未生效。
 * 规则：内部服务间调用凭 X-Internal-Secret 放行；商品查询 GET 公开（与网关
 * PUBLIC_PREFIXES 对齐，游客可浏览）；其余请求强制登录。
 */
@Configuration
public class SaTokenConfig implements WebMvcConfigurer {

    @Value("${internal.secret:}")
    private String internalSecret;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new SaInterceptor(handle -> {
            String secret = SaHolder.getRequest().getHeader("X-Internal-Secret");
            if (StringUtils.hasText(internalSecret) && internalSecret.equals(secret)) {
                return; // 内部调用放行
            }
            String path = SaHolder.getRequest().getRequestPath();
            String method = SaHolder.getRequest().getMethod();
            if ("GET".equals(method) && path.startsWith("/api/v1/products")) {
                return; // 商品浏览公开
            }
            StpUtil.checkLogin();
        }))
        .addPathPatterns("/**")
        .excludePathPatterns("/doc.html", "/webjars/**", "/v3/api-docs/**",
                "/swagger-resources/**", "/favicon.ico");
    }
}
