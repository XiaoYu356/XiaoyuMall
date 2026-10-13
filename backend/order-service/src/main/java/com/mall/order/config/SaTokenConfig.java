package com.mall.order.config;

import cn.dev33.satoken.context.SaHolder;
import cn.dev33.satoken.interceptor.SaInterceptor;
import cn.dev33.satoken.stp.StpUtil;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * sa-token 拦截器注册：此前类上的 @SaCheckLogin 因未注册拦截器从未生效。
 * 规则：
 * - 内部服务间调用（AI 服务直连本服务，无用户态 token）：校验 X-Internal-Secret
 *   共享密钥，放行后由 Controller 按 userId 参数做归属校验；
 * - 其余请求（C 端经网关带 satoken）：强制登录；
 * - 方法级注解（如 ship 的 @SaCheckPermission）仍由 SaInterceptor 注解校验兜底。
 */
@Configuration
public class SaTokenConfig implements WebMvcConfigurer {

    public static final String INTERNAL_SECRET_HEADER = "X-Internal-Secret";

    @Value("${internal.secret:}")
    private String internalSecret;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new SaInterceptor(handle -> {
            String secret = SaHolder.getRequest().getHeader(INTERNAL_SECRET_HEADER);
            if (StringUtils.hasText(internalSecret) && internalSecret.equals(secret)) {
                return; // 内部调用放行
            }
            StpUtil.checkLogin();
        }))
        .addPathPatterns("/**")
        // knife4j 接口文档不拦截
        .excludePathPatterns("/doc.html", "/webjars/**", "/v3/api-docs/**",
                "/swagger-resources/**", "/favicon.ico");
    }
}
