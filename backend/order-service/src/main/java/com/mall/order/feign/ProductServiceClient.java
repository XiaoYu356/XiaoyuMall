package com.mall.order.feign;

import com.mall.common.result.Result;
import com.mall.order.config.FeignConfig;
import com.mall.order.entity.Product;
import com.mall.order.entity.ProductSku;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.cloud.openfeign.SpringQueryMap;
import org.springframework.web.bind.annotation.*;

@FeignClient(name = "product-service", configuration = FeignConfig.class)
public interface ProductServiceClient {

    @GetMapping("/api/v1/products/{productId}")
    Result<Product> getProductById(@PathVariable("productId") Long productId);

    @GetMapping("/api/v1/products/skus/{skuId}")
    Result<ProductSku> getSkuById(@PathVariable("skuId") Long skuId);

    @PostMapping("/api/v1/products/{skuId}/deduct-stock")
    Result<Boolean> deductStock(@PathVariable("skuId") Long skuId, @RequestParam("quantity") Integer quantity);

    @PostMapping("/api/v1/products/{skuId}/add-stock")
    Result<Boolean> addStock(@PathVariable("skuId") Long skuId, @RequestParam("quantity") Integer quantity);

    @PostMapping("/api/v1/products/{productId}/increment-sales")
    Result<Boolean> incrementSales(@PathVariable("productId") Long productId, @RequestParam("quantity") Integer quantity);

    @PostMapping("/api/v1/products/{productId}/decrement-sales")
    Result<Boolean> decrementSales(@PathVariable("productId") Long productId, @RequestParam("quantity") Integer quantity);
}
