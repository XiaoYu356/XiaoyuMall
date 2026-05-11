package com.mall.order.dto;

import lombok.Data;

@Data
public class UpdateCartDTO {
    
    private Long id;
    
    private Long userId;
    
    private Integer quantity;
    
    private Integer selected;
}
