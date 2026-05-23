package com.mall.coupon.mq;

import lombok.Data;

import java.io.Serializable;

@Data
public class CouponReceiveMessage implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long userId;

    private Long templateId;
}
