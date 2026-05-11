package com.mall.order.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("order_item")
public class OrderItem {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private Long orderId;
    
    private String orderNo;
    
    private Long productId;
    
    private Long skuId;
    
    private String productName;
    
    private String skuName;
    
    private String skuCode;
    
    private BigDecimal price;
    
    private Integer quantity;
    
    private BigDecimal totalAmount;
    
    private String productImage;
    
    private LocalDateTime createTime;
}
