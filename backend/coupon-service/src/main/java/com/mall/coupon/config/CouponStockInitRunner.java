package com.mall.coupon.config;

import com.mall.coupon.service.CouponService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class CouponStockInitRunner implements CommandLineRunner {

    private final CouponService couponService;

    public CouponStockInitRunner(CouponService couponService) {
        this.couponService = couponService;
    }

    @Override
    public void run(String... args) {
        try {
            log.info("开始同步优惠券库存到Redis...");
            couponService.syncCouponStockToRedis();
            log.info("优惠券库存同步完成");
        } catch (Exception e) {
            log.error("优惠券库存同步失败，将在首次领取时自动补偿", e);
        }
    }
}
