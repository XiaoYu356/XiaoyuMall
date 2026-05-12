package com.mall.user.controller;

import cn.dev33.satoken.annotation.SaCheckLogin;
import cn.dev33.satoken.stp.StpUtil;
import com.mall.common.result.Result;
import com.mall.user.entity.UserAddress;
import com.mall.user.service.UserAddressService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/v1/users/addresses")
@SaCheckLogin
@Tag(name = "收货地址管理", description = "用户收货地址增删改查接口")
public class UserAddressController {

    @Autowired
    private UserAddressService userAddressService;

    @GetMapping
    @Operation(summary = "获取当前用户地址列表")
    public Result<List<UserAddress>> getAddressList() {
        Long userId = StpUtil.getLoginIdAsLong();
        List<UserAddress> addresses = userAddressService.getAddressList(userId);
        return Result.success(addresses);
    }

    @GetMapping("/{addressId}")
    @Operation(summary = "获取地址详情")
    public Result<UserAddress> getAddressById(@PathVariable Long addressId) {
        UserAddress address = userAddressService.getAddressById(addressId);
        return Result.success(address);
    }

    @PostMapping
    @Operation(summary = "添加收货地址")
    public Result<UserAddress> addAddress(@RequestBody UserAddress address) {
        Long userId = StpUtil.getLoginIdAsLong();
        address.setUserId(userId);
        UserAddress created = userAddressService.addAddress(address);
        return Result.success(created);
    }

    @PutMapping
    @Operation(summary = "更新收货地址")
    public Result<UserAddress> updateAddress(@RequestBody UserAddress address) {
        Long userId = StpUtil.getLoginIdAsLong();
        address.setUserId(userId);
        UserAddress updated = userAddressService.updateAddress(address);
        return Result.success(updated);
    }

    @DeleteMapping("/{addressId}")
    @Operation(summary = "删除收货地址")
    public Result<Void> deleteAddress(@PathVariable Long addressId) {
        Long userId = StpUtil.getLoginIdAsLong();
        userAddressService.deleteAddress(userId, addressId);
        return Result.success();
    }

    @PostMapping("/{addressId}/default")
    @Operation(summary = "设置默认地址")
    public Result<Void> setDefaultAddress(@PathVariable Long addressId) {
        Long userId = StpUtil.getLoginIdAsLong();
        userAddressService.setDefaultAddress(userId, addressId);
        return Result.success();
    }
}
