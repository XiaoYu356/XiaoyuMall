package com.mall.order.mq;

import lombok.Data;

import java.io.Serializable;
import java.util.List;

@Data
public class OrderCreateMessage implements Serializable {

    private static final long serialVersionUID = 1L;

    private String orderNo;

    private Long userId;

    private String receiverName;

    private String receiverPhone;

    private String receiverAddress;

    private String remark;

    private Long couponId;

    private List<OrderItemMessage> items;

    @Data
    public static class OrderItemMessage implements Serializable {
        private static final long serialVersionUID = 1L;
        private Long productId;
        private Long skuId;
        private Integer quantity;
    }
}
