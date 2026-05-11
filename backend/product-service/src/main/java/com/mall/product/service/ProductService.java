package com.mall.product.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.product.dto.CategoryCreateDTO;
import com.mall.product.dto.ProductCreateDTO;
import com.mall.product.entity.Product;
import com.mall.product.entity.ProductCategory;
import com.mall.product.entity.ProductSku;
import com.mall.product.entity.ProductVO;

import java.util.List;
import java.util.Map;

public interface ProductService {

    Map<String, Object> getProductStats();

    Page<ProductVO> getProductList(Long categoryId, String keyword, Integer pageNum, Integer pageSize);

    Product getProductById(Long productId);

    Product createProduct(ProductCreateDTO dto);

    Product updateProduct(Product product);

    void deleteProduct(Long productId);

    boolean deductStock(Long skuId, Integer quantity);

    boolean addStock(Long skuId, Integer quantity);

    List<ProductCategory> getCategoryList();

    ProductCategory createCategory(CategoryCreateDTO dto);

    ProductCategory updateCategory(ProductCategory category);

    void deleteCategory(Long categoryId);

    List<ProductSku> getProductSkuList(Long productId);

    ProductSku getSkuById(Long skuId);
}
