package com.mall.order.feign;

import com.mall.common.result.Result;
import com.mall.order.config.FeignConfig;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.math.BigDecimal;

@FeignClient(name = "coupon-service", configuration = FeignConfig.class)
public interface CouponServiceClient {
    
    @PostMapping("/api/v1/coupons/calculate")
    Result<BigDecimal> calculateDiscount(@RequestParam("couponId") Long couponId, @RequestParam("orderAmount") BigDecimal orderAmount);
    
    @PostMapping("/api/v1/coupons/{couponId}/use")
    Result<Boolean> useCoupon(@PathVariable("couponId") Long couponId, @RequestParam("orderId") Long orderId);
}
