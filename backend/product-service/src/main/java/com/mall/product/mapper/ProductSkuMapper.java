package com.mall.product.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.mall.product.entity.ProductSku;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface ProductSkuMapper extends BaseMapper<ProductSku> {

    @Update("UPDATE product_sku SET stock = stock - #{quantity} WHERE id = #{skuId} AND stock >= #{quantity}")
    int deductStockCas(@Param("skuId") Long skuId, @Param("quantity") Integer quantity);

    @Update("UPDATE product_sku SET stock = stock + #{quantity} WHERE id = #{skuId}")
    int addStockCas(@Param("skuId") Long skuId, @Param("quantity") Integer quantity);
}
