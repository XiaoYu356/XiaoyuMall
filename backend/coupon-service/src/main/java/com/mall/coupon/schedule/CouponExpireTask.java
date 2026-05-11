package com.mall.coupon.schedule;

import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.mall.coupon.entity.UserCoupon;
import com.mall.coupon.mapper.UserCouponMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

@Slf4j
@Component
public class CouponExpireTask {

    @Autowired
    private UserCouponMapper userCouponMapper;

    @Scheduled(cron = "0 0 * * * ?")
    public void expireCoupons() {
        LambdaUpdateWrapper<UserCoupon> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(UserCoupon::getStatus, 0)
               .lt(UserCoupon::getExpireTime, LocalDateTime.now())
               .set(UserCoupon::getStatus, 2);
        int count = userCouponMapper.update(null, wrapper);
        if (count > 0) {
            log.info("定时任务: 已将 {} 张过期优惠券状态更新为已过期", count);
        }
    }
}
