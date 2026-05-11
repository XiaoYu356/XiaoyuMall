package com.mall.product.dto;

import lombok.Data;

@Data
public class CategoryCreateDTO {
    private Long parentId;
    private String categoryName;
    private Integer categoryLevel;
    private String icon;
    private Integer sort;
    private Integer status;
}
