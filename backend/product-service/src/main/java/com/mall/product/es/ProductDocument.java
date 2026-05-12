package com.mall.product.es;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Data
public class ProductDocument {

    public static final String INDEX_NAME = "mall_product";

    private Long id;

    private String productName;

    private Long categoryId;

    private String categoryName;

    private String categoryNameSearch;

    private Long parentCategoryId;

    private Long brandId;

    private String brandName;

    private String brandNameSearch;

    private BigDecimal price;

    private BigDecimal originalPrice;

    private String description;

    private String mainImage;

    private Integer status;

    private Integer sales;

    private Integer totalStock;

    private String createTime;

    private Map<String, Object> suggest;
}
