package com.mall.coupon.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.mall.coupon.entity.UserCoupon;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface UserCouponMapper extends BaseMapper<UserCoupon> {

    @Update("UPDATE user_coupon SET status = 1, order_id = #{orderId}, use_time = NOW() WHERE id = #{couponId} AND status = 0")
    int useCouponCas(@Param("couponId") Long couponId, @Param("orderId") Long orderId);
}
