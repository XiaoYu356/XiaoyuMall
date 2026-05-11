package com.mall.order.entity;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class Product {

    private Long id;

    private String productName;

    private Long categoryId;

    private BigDecimal price;

    private BigDecimal originalPrice;

    private String mainImage;

    private Integer status;
}
