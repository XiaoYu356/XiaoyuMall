package com.mall.product.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Data
public class ProductCreateDTO {
    private String productName;
    private Long categoryId;
    private Long brandId;
    private String productCode;
    private BigDecimal price;
    private BigDecimal originalPrice;
    private String description;
    private String mainImage;
    private String subImages;
    private Integer sort;

    private List<SkuItem> skuList;

    @Data
    public static class SkuItem {
        private String skuName;
        private String skuCode;
        private BigDecimal price;
        private Integer stock;
        private String image;
        private Map<String, String> specs;
    }
}
