package com.mall.product.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.common.constant.RedisConstant;
import com.mall.common.exception.BusinessException;
import com.mall.product.dto.CategoryCreateDTO;
import com.mall.product.dto.ProductCreateDTO;
import com.mall.product.entity.Product;
import com.mall.product.entity.ProductCategory;
import com.mall.product.entity.ProductSku;
import com.mall.product.entity.ProductVO;
import com.mall.product.mapper.ProductMapper;
import com.mall.product.mapper.ProductCategoryMapper;
import com.mall.product.mapper.ProductSkuMapper;
import com.mall.product.service.ProductService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ProductServiceImpl implements ProductService {

    @Autowired
    private ProductMapper productMapper;

    @Autowired
    private ProductCategoryMapper productCategoryMapper;

    @Autowired
    private ProductSkuMapper productSkuMapper;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Override
    public Page<ProductVO> getProductList(Long categoryId, String keyword, Integer pageNum, Integer pageSize) {
        Page<Product> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<Product> wrapper = new LambdaQueryWrapper<>();

        if (categoryId != null) {
            wrapper.eq(Product::getCategoryId, categoryId);
        }

        if (StringUtils.hasText(keyword)) {
            wrapper.like(Product::getProductName, keyword);
        }

        wrapper.eq(Product::getStatus, 1)
               .orderByDesc(Product::getSort)
               .orderByDesc(Product::getCreateTime);

        Page<Product> productPage = productMapper.selectPage(page, wrapper);

        Page<ProductVO> voPage = new Page<>(pageNum, pageSize, productPage.getTotal());
        if (productPage.getRecords().isEmpty()) {
            voPage.setRecords(List.of());
            return voPage;
        }

        List<Long> productIds = productPage.getRecords().stream()
                .map(Product::getId)
                .collect(Collectors.toList());

        LambdaQueryWrapper<ProductSku> skuWrapper = new LambdaQueryWrapper<>();
        skuWrapper.in(ProductSku::getProductId, productIds)
                  .eq(ProductSku::getStatus, 1);
        List<ProductSku> allSkus = productSkuMapper.selectList(skuWrapper);

        Map<Long, Integer> stockMap = allSkus.stream()
                .collect(Collectors.groupingBy(
                        ProductSku::getProductId,
                        Collectors.summingInt(ProductSku::getStock)
                ));

        List<ProductVO> voList = productPage.getRecords().stream().map(p -> {
            ProductVO vo = new ProductVO();
            vo.setId(p.getId());
            vo.setProductName(p.getProductName());
            vo.setCategoryId(p.getCategoryId());
            vo.setBrandId(p.getBrandId());
            vo.setProductCode(p.getProductCode());
            vo.setPrice(p.getPrice());
            vo.setOriginalPrice(p.getOriginalPrice());
            vo.setDescription(p.getDescription());
            vo.setMainImage(p.getMainImage());
            vo.setSubImages(p.getSubImages());
            vo.setStatus(p.getStatus());
            vo.setSort(p.getSort());
            vo.setSales(p.getSales());
            vo.setCreateTime(p.getCreateTime());
            vo.setUpdateTime(p.getUpdateTime());
            vo.setDeleted(p.getDeleted());
            vo.setTotalStock(stockMap.getOrDefault(p.getId(), 0));
            return vo;
        }).collect(Collectors.toList());

        voPage.setRecords(voList);
        return voPage;
    }

    @Override
    public Product getProductById(Long productId) {
        String productKey = RedisConstant.PRODUCT_DETAIL_KEY + productId;
        Product product = (Product) redisTemplate.opsForValue().get(productKey);

        if (product == null) {
            product = productMapper.selectById(productId);
            if (product != null) {
                redisTemplate.opsForValue().set(productKey, product, RedisConstant.DEFAULT_EXPIRE_TIME, TimeUnit.SECONDS);
            }
        }

        return product;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Product createProduct(ProductCreateDTO dto) {
        Product product = new Product();
        product.setProductName(dto.getProductName());
        product.setCategoryId(dto.getCategoryId());
        product.setProductCode(dto.getProductCode());
        product.setPrice(dto.getPrice());
        product.setOriginalPrice(dto.getOriginalPrice());
        product.setDescription(dto.getDescription());
        product.setMainImage(dto.getMainImage());
        product.setSubImages(dto.getSubImages());
        product.setSort(dto.getSort() != null ? dto.getSort() : 0);
        product.setStatus(1);
        product.setSales(0);

        if (dto.getSkuList() != null && !dto.getSkuList().isEmpty()) {
            BigDecimal minPrice = dto.getPrice();
            for (ProductCreateDTO.SkuItem item : dto.getSkuList()) {
                if (item.getPrice() != null && (minPrice == null || item.getPrice().compareTo(minPrice) < 0)) {
                    minPrice = item.getPrice();
                }
            }
            product.setPrice(minPrice);
            product.setOriginalPrice(dto.getOriginalPrice() != null ? dto.getOriginalPrice() : minPrice);
        } else {
            product.setOriginalPrice(dto.getOriginalPrice() != null ? dto.getOriginalPrice() : dto.getPrice());
        }

        productMapper.insert(product);

        if (dto.getSkuList() != null && !dto.getSkuList().isEmpty()) {
            for (ProductCreateDTO.SkuItem item : dto.getSkuList()) {
                ProductSku sku = new ProductSku();
                sku.setProductId(product.getId());
                sku.setSkuCode(item.getSkuCode() != null ? item.getSkuCode() : dto.getProductCode() + "-" + product.getId() + "-" + System.nanoTime());
                sku.setSkuName(item.getSkuName());
                sku.setPrice(item.getPrice() != null ? item.getPrice() : dto.getPrice());
                sku.setStock(item.getStock() != null ? item.getStock() : 0);
                sku.setImage(item.getImage());
                sku.setSpecs(item.getSpecs() != null ? com.alibaba.fastjson2.JSON.toJSONString(item.getSpecs()) : null);
                sku.setStatus(1);
                productSkuMapper.insert(sku);
            }
        } else {
            ProductSku defaultSku = new ProductSku();
            defaultSku.setProductId(product.getId());
            defaultSku.setSkuCode(dto.getProductCode() + "-DEFAULT");
            defaultSku.setSkuName(dto.getProductName() + " 默认规格");
            defaultSku.setPrice(dto.getPrice());
            defaultSku.setStock(0);
            defaultSku.setStatus(1);
            productSkuMapper.insert(defaultSku);
        }

        log.info("商品创建成功: {}, SKU数量: {}", product.getProductName(),
                dto.getSkuList() != null ? dto.getSkuList().size() : 1);

        return product;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Product updateProduct(Product product) {
        productMapper.updateById(product);

        String productKey = RedisConstant.PRODUCT_DETAIL_KEY + product.getId();
        redisTemplate.delete(productKey);

        log.info("商品更新成功: {}", product.getProductName());

        return product;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteProduct(Long productId) {
        Product product = new Product();
        product.setId(productId);
        product.setStatus(0);
        productMapper.updateById(product);

        String productKey = RedisConstant.PRODUCT_DETAIL_KEY + productId;
        redisTemplate.delete(productKey);

        log.info("商品删除成功: {}", productId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean deductStock(Long skuId, Integer quantity) {
        ProductSku sku = productSkuMapper.selectById(skuId);
        if (sku == null) {
            throw new BusinessException("商品SKU不存在");
        }

        if (sku.getStock() < quantity) {
            throw new BusinessException("库存不足");
        }

        sku.setStock(sku.getStock() - quantity);
        int rows = productSkuMapper.updateById(sku);

        if (rows > 0) {
            String stockKey = RedisConstant.PRODUCT_STOCK_KEY + skuId;
            redisTemplate.opsForValue().decrement(stockKey, quantity);
            log.info("库存扣减成功: skuId={}, quantity={}", skuId, quantity);
            return true;
        }

        return false;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean addStock(Long skuId, Integer quantity) {
        ProductSku sku = productSkuMapper.selectById(skuId);
        if (sku == null) {
            throw new BusinessException("商品SKU不存在");
        }

        sku.setStock(sku.getStock() + quantity);
        int rows = productSkuMapper.updateById(sku);

        if (rows > 0) {
            String stockKey = RedisConstant.PRODUCT_STOCK_KEY + skuId;
            redisTemplate.opsForValue().increment(stockKey, quantity);
            log.info("库存增加成功: skuId={}, quantity={}", skuId, quantity);
            return true;
        }

        return false;
    }

    @Override
    public List<ProductCategory> getCategoryList() {
        LambdaQueryWrapper<ProductCategory> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ProductCategory::getStatus, 1)
               .orderByAsc(ProductCategory::getSort);
        return productCategoryMapper.selectList(wrapper);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ProductCategory createCategory(CategoryCreateDTO dto) {
        ProductCategory category = new ProductCategory();
        Long parentId = dto.getParentId() != null ? dto.getParentId() : 0L;
        category.setParentId(parentId);
        category.setCategoryName(dto.getCategoryName());

        int level = 1;
        if (parentId > 0) {
            ProductCategory parent = productCategoryMapper.selectById(parentId);
            if (parent != null) {
                level = parent.getCategoryLevel() + 1;
            }
        }
        category.setCategoryLevel(level);

        category.setIcon(dto.getIcon());

        if (dto.getSort() != null) {
            category.setSort(dto.getSort());
        } else {
            LambdaQueryWrapper<ProductCategory> sortWrapper = new LambdaQueryWrapper<>();
            sortWrapper.eq(ProductCategory::getParentId, parentId)
                       .orderByDesc(ProductCategory::getSort)
                       .last("LIMIT 1");
            ProductCategory maxSortCategory = productCategoryMapper.selectOne(sortWrapper);
            category.setSort(maxSortCategory != null ? maxSortCategory.getSort() + 1 : 1);
        }

        category.setStatus(dto.getStatus() != null ? dto.getStatus() : 1);
        productCategoryMapper.insert(category);
        log.info("分类创建成功: {}", category.getCategoryName());
        return category;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ProductCategory updateCategory(ProductCategory category) {
        productCategoryMapper.updateById(category);
        log.info("分类更新成功: {}", category.getCategoryName());
        return category;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteCategory(Long categoryId) {
        LambdaQueryWrapper<Product> productWrapper = new LambdaQueryWrapper<>();
        productWrapper.eq(Product::getCategoryId, categoryId)
                      .eq(Product::getStatus, 1);
        Long productCount = productMapper.selectCount(productWrapper);
        if (productCount > 0) {
            throw new BusinessException("该分类下存在商品，无法删除");
        }

        LambdaQueryWrapper<ProductCategory> childWrapper = new LambdaQueryWrapper<>();
        childWrapper.eq(ProductCategory::getParentId, categoryId)
                    .eq(ProductCategory::getStatus, 1);
        Long childCount = productCategoryMapper.selectCount(childWrapper);
        if (childCount > 0) {
            throw new BusinessException("该分类下存在子分类，无法删除");
        }

        ProductCategory update = new ProductCategory();
        update.setId(categoryId);
        update.setStatus(0);
        productCategoryMapper.updateById(update);
        log.info("分类删除成功: {}", categoryId);
    }

    @Override
    public List<ProductSku> getProductSkuList(Long productId) {
        LambdaQueryWrapper<ProductSku> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ProductSku::getProductId, productId)
               .eq(ProductSku::getStatus, 1);
        return productSkuMapper.selectList(wrapper);
    }

    @Override
    public ProductSku getSkuById(Long skuId) {
        return productSkuMapper.selectById(skuId);
    }
}
