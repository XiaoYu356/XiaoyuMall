package com.mall.order.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("cart")
public class Cart {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long userId;
    
    private Long productId;
    
    private Long skuId;
    
    private String productName;
    
    private String skuName;
    
    private BigDecimal price;
    
    private Integer quantity;
    
    private String productImage;
    
    private Integer selected;
    
    private LocalDateTime createTime;
    
    private LocalDateTime updateTime;
}
