package com.mall.user.controller;

import cn.dev33.satoken.stp.StpUtil;
import com.mall.common.result.Result;
import com.mall.user.mapper.PermissionMapper;
import com.mall.user.mapper.RoleMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/v1/users/auth")
@Tag(name = "内部鉴权接口", description = "供其他微服务调用的权限查询接口")
public class AuthController {

    @Autowired
    private PermissionMapper permissionMapper;

    @Autowired
    private RoleMapper roleMapper;

    @GetMapping("/permissions")
    @Operation(summary = "获取用户权限列表")
    public Result<List<String>> getPermissionList(@RequestParam Long userId) {
        List<String> permissions = permissionMapper.selectPermissionCodesByUserId(userId);
        return Result.success(permissions);
    }

    @GetMapping("/roles")
    @Operation(summary = "获取用户角色列表")
    public Result<List<String>> getRoleList(@RequestParam Long userId) {
        List<String> roles = roleMapper.selectRoleCodesByUserId(userId);
        return Result.success(roles);
    }
}
