package com.mall.order.dto;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class AddCartDTO {
    
    private Long userId;
    
    private Long productId;
    
    private Long skuId;
    
    private String productName;
    
    private String skuName;
    
    private BigDecimal price;
    
    private Integer quantity;
    
    private String productImage;
}
