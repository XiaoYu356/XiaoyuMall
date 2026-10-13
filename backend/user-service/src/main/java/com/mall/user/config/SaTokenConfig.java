package com.mall.user.config;

import cn.dev33.satoken.context.SaHolder;
import cn.dev33.satoken.interceptor.SaInterceptor;
import cn.dev33.satoken.stp.StpUtil;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * sa-token 拦截器注册：此前 @SaCheckLogin 等注解因未注册拦截器从未生效。
 * 规则：内部服务间调用凭 X-Internal-Secret 放行；其余请求强制登录。
 * 登录/注册/权限查询（供网关与各服务 Feign 调用）保持公开，与网关白名单对齐。
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
            StpUtil.checkLogin();
        }))
        .addPathPatterns("/**")
        .excludePathPatterns(
                "/api/v1/users/login",
                "/api/v1/users/register",
                "/api/v1/users/auth/permissions",
                "/api/v1/users/auth/roles",
                "/doc.html", "/webjars/**", "/v3/api-docs/**",
                "/swagger-resources/**", "/favicon.ico");
    }
}
