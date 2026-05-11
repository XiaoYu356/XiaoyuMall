package com.mall.product.feign;

import com.mall.common.result.Result;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;

@FeignClient(name = "user-service")
public interface UserServiceClient {

    @GetMapping("/api/v1/users/auth/permissions")
    Result<List<String>> getPermissionList(@RequestParam("userId") Long userId);

    @GetMapping("/api/v1/users/auth/roles")
    Result<List<String>> getRoleList(@RequestParam("userId") Long userId);
}
