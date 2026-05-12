package com.mall.order.controller;

import cn.dev33.satoken.annotation.SaCheckLogin;
import cn.dev33.satoken.stp.StpUtil;
import com.mall.common.result.Result;
import com.mall.order.dto.AddCartDTO;
import com.mall.order.dto.UpdateCartDTO;
import com.mall.order.entity.Cart;
import com.mall.order.service.CartService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/v1/cart")
@SaCheckLogin
@Tag(name = "购物车管理", description = "购物车相关接口")
public class CartController {
    
    @Autowired
    private CartService cartService;
    
    @GetMapping
    @Operation(summary = "获取购物车列表")
    public Result<List<Cart>> getCartList() {
        try {
            Long userId = StpUtil.getLoginIdAsLong();
            List<Cart> cartList = cartService.getCartList(userId);
            return Result.success(cartList);
        } catch (Exception e) {
            log.error("获取购物车列表异常: {} - {}", e.getClass().getName(), e.getMessage(), e);
            throw e;
        }
    }
    
    @PostMapping
    @Operation(summary = "添加商品到购物车")
    public Result<Cart> addCart(@RequestBody AddCartDTO addCartDTO) {
        if (addCartDTO.getUserId() == null) {
            addCartDTO.setUserId(StpUtil.getLoginIdAsLong());
        }
        Cart cart = cartService.addCart(addCartDTO);
        return Result.success(cart);
    }
    
    @PutMapping
    @Operation(summary = "更新购物车商品")
    public Result<Cart> updateCart(@RequestBody UpdateCartDTO updateCartDTO) {
        if (updateCartDTO.getUserId() == null) {
            updateCartDTO.setUserId(StpUtil.getLoginIdAsLong());
        }
        Cart cart = cartService.updateCart(updateCartDTO);
        return Result.success(cart);
    }
    
    @DeleteMapping("/{cartId}")
    @Operation(summary = "删除购物车商品")
    public Result<Void> deleteCart(@PathVariable Long cartId) {
        Long userId = StpUtil.getLoginIdAsLong();
        cartService.deleteCart(userId, cartId);
        return Result.success();
    }
    
    @DeleteMapping("/batch")
    @Operation(summary = "批量删除购物车商品")
    public Result<Void> deleteCartBatch(@RequestBody List<Long> cartIds) {
        Long userId = StpUtil.getLoginIdAsLong();
        cartService.deleteCartBatch(userId, cartIds);
        return Result.success();
    }
    
    @DeleteMapping("/clear")
    @Operation(summary = "清空购物车")
    public Result<Void> clearCart() {
        Long userId = StpUtil.getLoginIdAsLong();
        cartService.clearCart(userId);
        return Result.success();
    }
    
    @PutMapping("/select-all")
    @Operation(summary = "全选/取消全选")
    public Result<Void> selectAll(@RequestParam Integer selected) {
        Long userId = StpUtil.getLoginIdAsLong();
        cartService.selectAll(userId, selected);
        return Result.success();
    }
}
