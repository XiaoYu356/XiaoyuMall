package com.mall.order.entity;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class ProductSku {
    private Long id;
    private Long productId;
    private String skuCode;
    private String skuName;
    private BigDecimal price;
    private Integer stock;
    private String specs;
    private String image;
    private Integer status;
}
