package com.mall.order.config;

import cn.dev33.satoken.stp.StpUtil;
import feign.RequestInterceptor;
import feign.RequestTemplate;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

@Slf4j
@Configuration
public class FeignConfig {

    @Bean
    public RequestInterceptor feignRequestInterceptor() {
        return new RequestInterceptor() {
            @Override
            public void apply(RequestTemplate template) {
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
