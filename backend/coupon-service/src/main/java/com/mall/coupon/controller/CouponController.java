package com.mall.coupon.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.common.result.Result;
import com.mall.coupon.entity.AvailableCouponVO;
import com.mall.coupon.entity.CouponTemplate;
import com.mall.coupon.entity.UserCoupon;
import com.mall.coupon.entity.UserCouponVO;
import com.mall.coupon.service.CouponService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;

@Slf4j
@RestController
@RequestMapping("/api/v1/coupons")
@Tag(name = "优惠券管理", description = "优惠券发放、核销等接口")
public class CouponController {
    
    @Autowired
    private CouponService couponService;
    
    @GetMapping
    @Operation(summary = "优惠券模板列表")
    @SaCheckPermission("coupon:view")
    public Result<Page<CouponTemplate>> getCouponTemplateList(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        Page<CouponTemplate> page = couponService.getCouponTemplateList(pageNum, pageSize);
        return Result.success(page);
    }
    
    @PostMapping
    @Operation(summary = "创建优惠券模板")
    @SaCheckPermission("coupon:add")
    public Result<CouponTemplate> createCouponTemplate(@RequestBody CouponTemplate template) {
        CouponTemplate created = couponService.createCouponTemplate(template);
        return Result.success(created);
    }
    
    @PutMapping
    @Operation(summary = "更新优惠券模板")
    @SaCheckPermission("coupon:edit")
    public Result<CouponTemplate> updateCouponTemplate(@RequestBody CouponTemplate template) {
        CouponTemplate updated = couponService.updateCouponTemplate(template);
        return Result.success(updated);
    }
    
    @DeleteMapping("/{templateId}")
    @Operation(summary = "删除优惠券模板")
    @SaCheckPermission("coupon:delete")
    public Result<Void> deleteCouponTemplate(@PathVariable Long templateId) {
        couponService.deleteCouponTemplate(templateId);
        return Result.success();
    }
    
    @GetMapping("/available")
    @Operation(summary = "领券中心-可领取的优惠券列表")
    public Result<Page<AvailableCouponVO>> getAvailableCoupons(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "20") Integer pageSize) {
        Long userId = null;
        try {
            userId = StpUtil.getLoginIdAsLong();
        } catch (Exception ignored) {
        }
        Page<AvailableCouponVO> page = couponService.getAvailableCouponList(userId, pageNum, pageSize);
        return Result.success(page);
    }
    
    @PostMapping("/receive/{templateId}")
    @Operation(summary = "领取优惠券")
    public Result<UserCoupon> receiveCoupon(@PathVariable Long templateId) {
        Long userId = StpUtil.getLoginIdAsLong();
        UserCoupon userCoupon = couponService.receiveCoupon(userId, templateId);
        return Result.success(userCoupon);
    }
    
    @GetMapping("/mine")
    @Operation(summary = "我的优惠券列表")
    public Result<Page<UserCouponVO>> getMyCoupons(
            @RequestParam(required = false) Integer status,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "20") Integer pageSize) {
        Long userId = StpUtil.getLoginIdAsLong();
        Page<UserCouponVO> page = couponService.getUserCouponList(userId, status, pageNum, pageSize);
        return Result.success(page);
    }
    
    @PostMapping("/calculate")
    @Operation(summary = "计算优惠金额")
    public Result<BigDecimal> calculateDiscount(
            @RequestParam Long couponId,
            @RequestParam BigDecimal orderAmount) {
        BigDecimal discount = couponService.calculateDiscount(couponId, orderAmount);
        return Result.success(discount);
    }
    
    @PostMapping("/{couponId}/use")
    @Operation(summary = "使用优惠券")
    public Result<Boolean> useCoupon(
            @PathVariable Long couponId,
            @RequestParam Long orderId) {
        boolean result = couponService.useCoupon(couponId, orderId);
        return Result.success(result);
    }
    
    @GetMapping("/user/{userId}")
    @Operation(summary = "用户优惠券列表(内部)")
    public Result<Page<UserCouponVO>> getUserCouponList(
            @PathVariable Long userId,
            @RequestParam(required = false) Integer status,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        Page<UserCouponVO> page = couponService.getUserCouponList(userId, status, pageNum, pageSize);
        return Result.success(page);
    }
}
