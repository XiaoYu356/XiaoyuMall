package com.mall.order.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.List;

@Data
public class CreateOrderDTO {

    private Long userId;

    private Long addressId;

    private Long couponId;

    @NotBlank(message = "收货人姓名不能为空")
    private String receiverName;

    @NotBlank(message = "收货人电话不能为空")
    private String receiverPhone;

    @NotBlank(message = "收货地址不能为空")
    private String receiverAddress;

    @NotEmpty(message = "订单商品不能为空")
    private List<OrderItemDTO> items;

    private String remark;

    @Data
    public static class OrderItemDTO {
        private Long productId;
        private Long skuId;
        private Integer quantity;
    }
}
