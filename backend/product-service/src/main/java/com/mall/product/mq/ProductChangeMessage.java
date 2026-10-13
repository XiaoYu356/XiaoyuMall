package com.mall.product.mq;

import lombok.Data;

import java.io.Serializable;

/**
 * 商品变更MQ消息
 * action: SYNC=同步商品到ES, DELETE=从ES删除商品
 */
@Data
public class ProductChangeMessage implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long productId;

    private String action;

    public ProductChangeMessage() {}

    public ProductChangeMessage(Long productId, String action) {
        this.productId = productId;
        this.action = action;
    }

    public static final String ACTION_SYNC = "SYNC";
    public static final String ACTION_DELETE = "DELETE";
}
