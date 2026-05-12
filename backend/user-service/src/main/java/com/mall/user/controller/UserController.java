package com.mall.user.controller;

import cn.dev33.satoken.annotation.SaCheckLogin;
import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.annotation.SaCheckRole;
import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.common.result.Result;
import com.mall.user.dto.UserCreateDTO;
import com.mall.user.dto.UserLoginDTO;
import com.mall.user.dto.UserQueryDTO;
import com.mall.user.dto.UserRegisterDTO;
import com.mall.user.entity.User;
import com.mall.user.mapper.PermissionMapper;
import com.mall.user.mapper.RoleMapper;
import com.mall.user.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/users")
@Tag(name = "用户管理", description = "用户注册、登录、信息管理等接口")
public class UserController {
    
    @Autowired
    private UserService userService;

    @Autowired
    private PermissionMapper permissionMapper;

    @Autowired
    private RoleMapper roleMapper;

    @GetMapping("/stats")
    @Operation(summary = "用户统计")
    public Result<Map<String, Object>> getUserStats() {
        Map<String, Object> stats = userService.getUserStats();
        return Result.success(stats);
    }
    
    @PostMapping("/register")
    @Operation(summary = "用户注册")
    public Result<User> register(@Valid @RequestBody UserRegisterDTO dto) {
        User user = userService.register(dto);
        user.setPassword(null);
        return Result.success(user);
    }

    @PostMapping("/create")
    @Operation(summary = "管理员创建用户")
    @SaCheckPermission("user:add")
    public Result<User> createUser(@Valid @RequestBody UserCreateDTO dto) {
        User user = userService.createUser(dto);
        user.setPassword(null);
        return Result.success(user);
    }
    
    @PostMapping("/login")
    @Operation(summary = "用户登录")
    public Result<String> login(@Valid @RequestBody UserLoginDTO dto) {
        String token = userService.login(dto);
        return Result.success(token);
    }
    
    @GetMapping("/info")
    @Operation(summary = "获取当前登录用户信息")
    @SaCheckLogin
    public Result<UserInfoVO> getCurrentUserInfo() {
        Long userId = StpUtil.getLoginIdAsLong();
        User user = userService.getUserById(userId);
        if (user != null) {
            user.setPassword(null);
        }
        List<String> permissions = permissionMapper.selectPermissionCodesByUserId(userId);
        List<String> roles = roleMapper.selectRoleCodesByUserId(userId);
        UserInfoVO vo = new UserInfoVO();
        vo.setUser(user);
        vo.setPermissions(permissions);
        vo.setRoles(roles);
        return Result.success(vo);
    }
    
    @GetMapping
    @Operation(summary = "获取用户列表")
    @SaCheckPermission("user:view")
    public Result<Page<User>> getUserList(UserQueryDTO dto) {
        Page<User> userPage = userService.getUserList(dto);
        return Result.success(userPage);
    }
    
    @GetMapping("/{userId}")
    @Operation(summary = "获取用户信息")
    @SaCheckPermission("user:view")
    public Result<User> getUserInfo(@PathVariable Long userId) {
        User user = userService.getUserById(userId);
        if (user != null) {
            user.setPassword(null);
        }
        return Result.success(user);
    }
    
    @PutMapping
    @Operation(summary = "更新用户信息")
    @SaCheckPermission("user:edit")
    public Result<User> updateUserInfo(@RequestBody User user) {
        User updatedUser = userService.updateUserInfo(user);
        updatedUser.setPassword(null);
        return Result.success(updatedUser);
    }
    
    @DeleteMapping("/{userId}")
    @Operation(summary = "删除用户")
    @SaCheckPermission("user:delete")
    public Result<Void> deleteUser(@PathVariable Long userId) {
        userService.deleteUser(userId);
        return Result.success();
    }

    @Data
    public static class UserInfoVO {
        private User user;
        private List<String> permissions;
        private List<String> roles;
    }
}
