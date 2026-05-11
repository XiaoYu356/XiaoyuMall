package com.mall.product.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.mall.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.math.BigDecimal;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("product")
public class Product extends BaseEntity {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String productName;
    
    private Long categoryId;
    
    private Long brandId;
    
    private String productCode;
    
    private BigDecimal price;
    
    private BigDecimal originalPrice;
    
    private String description;
    
    private String mainImage;
    
    private String subImages;
    
    private Integer status;
    
    private Integer sort;
    
    private Integer sales;
}
