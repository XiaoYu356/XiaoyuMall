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

    /**
     * 退回优惠券：将已使用(status=1)且 order_id 匹配的券退回为未使用(status=0)，
     * 清空 order_id 和 use_time。CAS 条件保证幂等——重复退款不会重复退券。
     *
     * @return 影响行数，0 表示券不存在 / 不是该订单用的 / 已退回
     */
    @Update("UPDATE user_coupon SET status = 0, order_id = NULL, use_time = NULL WHERE id = #{couponId} AND status = 1 AND order_id = #{orderId}")
    int returnCouponCas(@Param("couponId") Long couponId, @Param("orderId") Long orderId);
}
