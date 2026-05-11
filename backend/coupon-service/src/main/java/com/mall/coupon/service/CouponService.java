package com.mall.coupon.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.coupon.entity.AvailableCouponVO;
import com.mall.coupon.entity.CouponTemplate;
import com.mall.coupon.entity.UserCoupon;
import com.mall.coupon.entity.UserCouponVO;

import java.math.BigDecimal;
import java.util.Map;

public interface CouponService {

    Map<String, Object> getCouponStats();

    Page<CouponTemplate> getCouponTemplateList(Integer pageNum, Integer pageSize);
    
    Page<AvailableCouponVO> getAvailableCouponList(Long userId, Integer pageNum, Integer pageSize);
    
    CouponTemplate createCouponTemplate(CouponTemplate template);
    
    CouponTemplate updateCouponTemplate(CouponTemplate template);
    
    void deleteCouponTemplate(Long templateId);
    
    UserCoupon receiveCoupon(Long userId, Long templateId);
    
    BigDecimal calculateDiscount(Long couponId, BigDecimal orderAmount);
    
    boolean useCoupon(Long couponId, Long orderId);
    
    Page<UserCouponVO> getUserCouponList(Long userId, Integer status, Integer pageNum, Integer pageSize);
}
