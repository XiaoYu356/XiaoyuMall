package com.mall.common.constant;

public class RedisConstant {
    
    public static final String PRODUCT_DETAIL_KEY = "mall:product:detail:";
    public static final String PRODUCT_LIST_KEY = "mall:product:list:";
    public static final String PRODUCT_STOCK_KEY = "mall:product:stock:";
    public static final String PRODUCT_CATEGORY_KEY = "mall:product:category";
    
    public static final String USER_INFO_KEY = "mall:user:info:";
    public static final String USER_TOKEN_KEY = "mall:user:token:";
    
    public static final String COUPON_TEMPLATE_KEY = "mall:coupon:template:";
    public static final String USER_COUPON_KEY = "mall:coupon:user:";
    
    public static final String ORDER_KEY = "mall:order:";
    public static final String ORDER_USER_KEY = "mall:order:user:";
    
    public static final String LOCK_PRODUCT_STOCK = "lock:product:stock:";
    public static final String LOCK_ORDER_CREATE = "lock:order:create:";
    
    public static final Long DEFAULT_EXPIRE_TIME = 3600L;
    public static final Long TOKEN_EXPIRE_TIME = 7200L;
}
