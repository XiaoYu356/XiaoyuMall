package com.mall.product.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.common.result.Result;
import com.mall.product.dto.CategoryCreateDTO;
import com.mall.product.dto.ProductCreateDTO;
import com.mall.product.entity.Brand;
import com.mall.product.entity.Product;
import com.mall.product.entity.ProductCategory;
import com.mall.product.entity.ProductSku;
import com.mall.product.entity.ProductVO;
import com.mall.product.es.ProductSearchService;
import com.mall.product.service.ProductService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/products")
@Tag(name = "商品管理", description = "商品查询、管理等接口")
public class ProductController {

    @Autowired
    private ProductService productService;

    @Autowired
    private ProductSearchService productSearchService;

    @GetMapping("/stats")
    @Operation(summary = "商品统计")
    public Result<Map<String, Object>> getProductStats() {
        Map<String, Object> stats = productService.getProductStats();
        return Result.success(stats);
    }

    @GetMapping("/brands")
    @Operation(summary = "品牌列表")
    public Result<List<Brand>> getBrandList() {
        List<Brand> brands = productService.getBrandList();
        return Result.success(brands);
    }

    @GetMapping("/categories")
    @Operation(summary = "商品分类列表")
    public Result<List<ProductCategory>> getCategoryList() {
        List<ProductCategory> categories = productService.getCategoryList();
        return Result.success(categories);
    }

    @PostMapping("/categories")
    @Operation(summary = "创建商品分类")
    @SaCheckPermission("product:add")
    public Result<ProductCategory> createCategory(@RequestBody CategoryCreateDTO dto) {
        ProductCategory category = productService.createCategory(dto);
        return Result.success(category);
    }

    @PutMapping("/categories")
    @Operation(summary = "更新商品分类")
    @SaCheckPermission("product:edit")
    public Result<ProductCategory> updateCategory(@RequestBody ProductCategory category) {
        ProductCategory updated = productService.updateCategory(category);
        return Result.success(updated);
    }

    @DeleteMapping("/categories/{categoryId}")
    @Operation(summary = "删除商品分类")
    @SaCheckPermission("product:delete")
    public Result<Void> deleteCategory(@PathVariable Long categoryId) {
        productService.deleteCategory(categoryId);
        return Result.success();
    }

    @GetMapping
    @Operation(summary = "商品列表查询")
    public Result<Page<ProductVO>> getProductList(
            @RequestParam(required = false) Long categoryId,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) BigDecimal minPrice,
            @RequestParam(required = false) BigDecimal maxPrice,
            @RequestParam(required = false) Long brandId,
            @RequestParam(required = false, defaultValue = "default") String sortBy,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "20") Integer pageSize) {
        Page<ProductVO> page = productService.getProductList(categoryId, keyword, minPrice, maxPrice, brandId, sortBy, pageNum, pageSize);
        return Result.success(page);
    }

    @GetMapping("/{productId}")
    @Operation(summary = "商品详情查询")
    public Result<ProductVO> getProductById(@PathVariable Long productId) {
        ProductVO product = productService.getProductById(productId);
        return Result.success(product);
    }

    @GetMapping("/{productId}/skus")
    @Operation(summary = "商品SKU列表")
    public Result<List<ProductSku>> getProductSkus(@PathVariable Long productId) {
        List<ProductSku> skus = productService.getProductSkuList(productId);
        return Result.success(skus);
    }

    @GetMapping("/skus/{skuId}")
    @Operation(summary = "SKU详情查询")
    public Result<ProductSku> getSkuById(@PathVariable Long skuId) {
        ProductSku sku = productService.getSkuById(skuId);
        return Result.success(sku);
    }

    @PostMapping
    @Operation(summary = "创建商品")
    @SaCheckPermission("product:add")
    public Result<Product> createProduct(@RequestBody ProductCreateDTO dto) {
        Product createdProduct = productService.createProduct(dto);
        return Result.success(createdProduct);
    }

    @PutMapping
    @Operation(summary = "更新商品")
    @SaCheckPermission("product:edit")
    public Result<Product> updateProduct(@RequestBody Product product) {
        Product updatedProduct = productService.updateProduct(product);
        return Result.success(updatedProduct);
    }

    @DeleteMapping("/{productId}")
    @Operation(summary = "删除商品")
    @SaCheckPermission("product:delete")
    public Result<Void> deleteProduct(@PathVariable Long productId) {
        productService.deleteProduct(productId);
        return Result.success();
    }

    @PostMapping("/{skuId}/deduct-stock")
    @Operation(summary = "扣减库存")
    public Result<Boolean> deductStock(
            @PathVariable Long skuId,
            @RequestParam Integer quantity) {
        boolean result = productService.deductStock(skuId, quantity);
        return Result.success(result);
    }

    @PostMapping("/{skuId}/add-stock")
    @Operation(summary = "增加库存")
    public Result<Boolean> addStock(
            @PathVariable Long skuId,
            @RequestParam Integer quantity) {
        boolean result = productService.addStock(skuId, quantity);
        return Result.success(result);
    }

    @PostMapping("/{productId}/increment-sales")
    @Operation(summary = "增加销量")
    public Result<Boolean> incrementSales(
            @PathVariable Long productId,
            @RequestParam Integer quantity) {
        boolean result = productService.incrementSales(productId, quantity);
        return Result.success(result);
    }

    @PostMapping("/{productId}/decrement-sales")
    @Operation(summary = "减少销量")
    public Result<Boolean> decrementSales(
            @PathVariable Long productId,
            @RequestParam Integer quantity) {
        boolean result = productService.decrementSales(productId, quantity);
        return Result.success(result);
    }

    @PostMapping("/es/sync")
    @Operation(summary = "同步商品数据到ES")
    @SaCheckPermission("product:edit")
    public Result<String> syncToElasticsearch() {
        productSearchService.syncAllProducts();
        return Result.success("同步完成");
    }

    @GetMapping("/es/suggest")
    @Operation(summary = "搜索建议")
    public Result<List<String>> searchSuggest(@RequestParam String prefix) {
        List<String> suggestions = productSearchService.suggest(prefix);
        return Result.success(suggestions);
    }

    @GetMapping("/es/hot")
    @Operation(summary = "热门搜索")
    public Result<List<String>> hotSearches(@RequestParam(defaultValue = "10") int size) {
        List<String> hotSearches = productSearchService.getHotSearches(size);
        return Result.success(hotSearches);
    }

    @GetMapping("/es/history")
    @Operation(summary = "搜索历史")
    public Result<List<String>> searchHistory() {
        Long userId = null;
        try {
            userId = StpUtil.getLoginIdAsLong();
        } catch (Exception ignored) {}
        List<String> history = productSearchService.getSearchHistory(userId);
        return Result.success(history);
    }

    @DeleteMapping("/es/history")
    @Operation(summary = "清除搜索历史")
    public Result<Void> clearSearchHistory() {
        Long userId = null;
        try {
            userId = StpUtil.getLoginIdAsLong();
        } catch (Exception ignored) {}
        productSearchService.clearSearchHistory(userId);
        return Result.success();
    }

    @GetMapping("/es/filters")
    @Operation(summary = "搜索筛选条件")
    public Result<Map<String, List<Map<String, Object>>>> searchFilters(
            @RequestParam(required = false) Long categoryId,
            @RequestParam(required = false) String keyword) {
        Map<String, List<Map<String, Object>>> filters = productSearchService.getSearchFilters(categoryId, keyword);
        return Result.success(filters);
    }
}
