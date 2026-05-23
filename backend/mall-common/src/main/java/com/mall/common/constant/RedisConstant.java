package com.mall.common.constant;

public class RedisConstant {

    public static final String PRODUCT_DETAIL_KEY = "mall:product:detail:";
    public static final String PRODUCT_STOCK_KEY = "mall:product:stock:";

    public static final String USER_INFO_KEY = "mall:user:info:";

    public static final String USER_COUPON_KEY = "mall:coupon:user:";
    public static final String COUPON_STOCK_KEY = "mall:coupon:stock:";

    public static final String DLQ_ORDER_KEY = "mall:dlq:order:";
    public static final String DLQ_COUPON_KEY = "mall:dlq:coupon:";

    public static final Long DEFAULT_EXPIRE_TIME = 3600L;
}
