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

    void receiveCouponAsync(Long userId, Long templateId);

    /**
     * 按配置版本路由领券请求（v0先查再减/v1数据库原子扣减/v2同步Lua/v3异步MQ）
     */
    Map<String, Object> receiveCouponByStrategy(Long userId, Long templateId);
    
    BigDecimal calculateDiscount(Long couponId, BigDecimal orderAmount);
    
    boolean useCoupon(Long couponId, Long orderId);

    /**
     * 退回已使用的优惠券（售后退款时调用）。
     * CAS 幂等：同一订单多次退款不会重复退券。
     *
     * @param couponId 用户券记录 ID（user_coupon.id）
     * @param orderId  原订单 ID（用于校验，防止退错券）
     * @return true=退回成功，false=券不存在 / 不是该订单用的 / 已退回
     */
    boolean returnCoupon(Long couponId, Long orderId);
    
    Page<UserCouponVO> getUserCouponList(Long userId, Integer status, Integer pageNum, Integer pageSize);

    void syncCouponStockToRedis();
}
