package com.mall.product.es;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.FieldValue;
import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.aggregations.Aggregation;
import co.elastic.clients.elasticsearch._types.aggregations.StringTermsBucket;
import co.elastic.clients.elasticsearch._types.query_dsl.BoolQuery;
import co.elastic.clients.elasticsearch._types.query_dsl.FunctionScore;
import co.elastic.clients.elasticsearch._types.query_dsl.FunctionScoreMode;
import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import co.elastic.clients.elasticsearch.core.BulkRequest;
import co.elastic.clients.elasticsearch.core.BulkResponse;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import co.elastic.clients.elasticsearch.core.search.HighlightField;
import co.elastic.clients.elasticsearch.core.search.Hit;
import co.elastic.clients.elasticsearch.indices.CreateIndexRequest;
import co.elastic.clients.elasticsearch.indices.CreateIndexResponse;
import co.elastic.clients.elasticsearch.indices.ExistsRequest;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.product.entity.Brand;
import com.mall.product.entity.Product;
import com.mall.product.entity.ProductCategory;
import com.mall.product.entity.ProductSku;
import com.mall.product.mapper.BrandMapper;
import com.mall.product.mapper.ProductCategoryMapper;
import com.mall.product.mapper.ProductMapper;
import com.mall.product.mapper.ProductSkuMapper;
import com.mall.product.entity.ProductVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.io.IOException;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ProductSearchService {

    private static final String HOT_SEARCH_KEY = "search:hot";
    private static final String SEARCH_HISTORY_PREFIX = "search:history:";
    private static final int MAX_HISTORY_SIZE = 10;
    private static final DateTimeFormatter DTF = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");

    @Autowired
    private ElasticsearchClient esClient;

    @Autowired
    private ProductMapper productMapper;

    @Autowired
    private ProductCategoryMapper categoryMapper;

    @Autowired
    private BrandMapper brandMapper;

    @Autowired
    private ProductSkuMapper skuMapper;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    public void createIndexIfNeeded() {
        try {
            boolean exists = esClient.indices().exists(
                    ExistsRequest.of(e -> e.index(ProductDocument.INDEX_NAME))).value();
            if (!exists) {
                doCreateIndex();
            } else {
                log.info("ES索引已存在, 跳过创建");
            }
        } catch (IOException e) {
            log.error("检查ES索引失败", e);
        }
    }

    public void recreateIndex() {
        try {
            boolean exists = esClient.indices().exists(
                    ExistsRequest.of(e -> e.index(ProductDocument.INDEX_NAME))).value();
            if (exists) {
                esClient.indices().delete(d -> d.index(ProductDocument.INDEX_NAME));
                log.info("删除旧ES索引");
            }
            doCreateIndex();
        } catch (IOException e) {
            log.error("重建ES索引失败", e);
        }
    }

    private void doCreateIndex() throws IOException {
        CreateIndexResponse response = esClient.indices().create(
                CreateIndexRequest.of(c -> c
                        .index(ProductDocument.INDEX_NAME)
                        .mappings(m -> m
                                .properties("id", p -> p.long_(l -> l))
                                .properties("productName", p -> p.text(t -> t
                                        .analyzer("ik_max_word")
                                        .searchAnalyzer("ik_smart")
                                        .fields("keyword", f -> f.keyword(k -> k.ignoreAbove(256)))))
                                .properties("categoryId", p -> p.long_(l -> l))
                                .properties("categoryName", p -> p.keyword(k -> k))
                                .properties("categoryNameSearch", p -> p.text(t -> t.analyzer("ik_max_word").searchAnalyzer("ik_smart")))
                                .properties("parentCategoryId", p -> p.long_(l -> l))
                                .properties("brandId", p -> p.long_(l -> l))
                                .properties("brandName", p -> p.keyword(k -> k))
                                .properties("brandNameSearch", p -> p.text(t -> t.analyzer("ik_max_word").searchAnalyzer("ik_smart")))
                                .properties("price", p -> p.double_(d -> d))
                                .properties("originalPrice", p -> p.double_(d -> d))
                                .properties("description", p -> p.text(t -> t.analyzer("ik_max_word").searchAnalyzer("ik_smart")))
                                .properties("mainImage", p -> p.keyword(k -> k))
                                .properties("status", p -> p.integer(i -> i))
                                .properties("sales", p -> p.integer(i -> i))
                                .properties("totalStock", p -> p.integer(i -> i))
                                .properties("createTime", p -> p.date(d -> d.format("yyyy-MM-dd'T'HH:mm:ss")))
                                .properties("suggest", p -> p.completion(cp -> cp.analyzer("ik_max_word")))
                        )));
        log.info("ES索引创建结果: {}", response.acknowledged());
    }

    public void syncAllProducts() {
        recreateIndex();

        List<Product> products = productMapper.selectList(
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<Product>()
                        .eq(Product::getStatus, 1));

        if (products.isEmpty()) {
            log.info("没有需要同步的商品");
            return;
        }

        List<Long> productIds = products.stream().map(Product::getId).collect(Collectors.toList());
        List<Long> categoryIds = products.stream().map(Product::getCategoryId).distinct().collect(Collectors.toList());
        List<Long> brandIds = products.stream().map(Product::getBrandId).filter(id -> id != null).distinct().collect(Collectors.toList());

        Map<Long, String> categoryNameMap = new HashMap<>();
        Map<Long, Long> parentCategoryMap = new HashMap<>();
        if (!categoryIds.isEmpty()) {
            List<ProductCategory> categories = categoryMapper.selectBatchIds(categoryIds);
            categories.forEach(c -> {
                categoryNameMap.put(c.getId(), c.getCategoryName());
                parentCategoryMap.put(c.getId(), c.getParentId());
            });
        }

        Map<Long, String> brandNameMap = new HashMap<>();
        if (!brandIds.isEmpty()) {
            List<Brand> brands = brandMapper.selectBatchIds(brandIds);
            brands.forEach(b -> brandNameMap.put(b.getId(), b.getBrandName()));
        }

        List<ProductSku> allSkus = skuMapper.selectList(
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<ProductSku>()
                        .in(ProductSku::getProductId, productIds)
                        .eq(ProductSku::getStatus, 1));
        Map<Long, Integer> stockMap = allSkus.stream()
                .collect(Collectors.groupingBy(ProductSku::getProductId,
                        Collectors.summingInt(ProductSku::getStock)));

        try {
            int batchSize = 2000;
            int totalSynced = 0;
            for (int i = 0; i < products.size(); i += batchSize) {
                List<Product> batch = products.subList(i, Math.min(i + batchSize, products.size()));
                BulkRequest.Builder bulkBuilder = new BulkRequest.Builder();
                for (Product p : batch) {
                    ProductDocument doc = buildDocumentFromProduct(p, categoryNameMap, parentCategoryMap, brandNameMap, stockMap);
                    bulkBuilder.operations(op -> op
                            .index(idx -> idx
                                    .index(ProductDocument.INDEX_NAME)
                                    .id(String.valueOf(p.getId()))
                                    .document(doc)));
                }
                BulkResponse response = esClient.bulk(bulkBuilder.build());
                if (response.errors()) {
                    log.error("ES批量同步部分失败, 批次: {}-{}", i, i + batch.size());
                    response.items().stream().filter(item -> item.error() != null).forEach(item ->
                            log.error("同步失败: id={}, error={}", item.id(), item.error().reason()));
                } else {
                    totalSynced += batch.size();
                }
            }
            log.info("ES批量同步完成, 共同步{}条商品", totalSynced);
        } catch (IOException e) {
            log.error("ES批量同步异常", e);
        }
    }

    public void syncProduct(Product product) {
        try {
            ProductDocument doc = buildDocumentSingle(product);
            esClient.index(i -> i
                    .index(ProductDocument.INDEX_NAME)
                    .id(String.valueOf(product.getId()))
                    .document(doc));
            log.info("ES同步商品: id={}", product.getId());
        } catch (Exception e) {
            log.error("ES同步商品失败: id={}", product.getId(), e);
        }
    }

    public void deleteProduct(Long productId) {
        try {
            esClient.delete(d -> d
                    .index(ProductDocument.INDEX_NAME)
                    .id(String.valueOf(productId)));
            log.info("ES删除商品: id={}", productId);
        } catch (Exception e) {
            log.error("ES删除商品失败: id={}", productId, e);
        }
    }

    public Page<ProductVO> search(Long categoryId, String keyword, BigDecimal minPrice,
                                   BigDecimal maxPrice, Long brandId, String sortBy,
                                   Integer pageNum, Integer pageSize) {
        try {
            List<Query> mustQueries = new ArrayList<>();
            mustQueries.add(Query.of(q -> q.term(t -> t.field("status").value(1))));

            if (categoryId != null) {
                List<Long> categoryIds = new ArrayList<>();
                categoryIds.add(categoryId);
                List<ProductCategory> children = categoryMapper.selectList(
                        new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<ProductCategory>()
                                .eq(ProductCategory::getParentId, categoryId));
                children.forEach(c -> categoryIds.add(c.getId()));

                List<FieldValue> values = categoryIds.stream()
                        .map(id -> FieldValue.of(id))
                        .collect(Collectors.toList());
                mustQueries.add(Query.of(q -> q.terms(t -> t.field("categoryId").terms(
                        tv -> tv.value(values)))));
            }

            if (StringUtils.hasText(keyword)) {
                mustQueries.add(Query.of(q -> q.multiMatch(m -> m
                        .fields("productName^3", "brandNameSearch^2", "categoryNameSearch^1.5", "description^1")
                        .query(keyword)
                        .type(co.elastic.clients.elasticsearch._types.query_dsl.TextQueryType.BestFields)
                        .fuzziness("AUTO"))));
            }

            if (minPrice != null || maxPrice != null) {
                mustQueries.add(Query.of(q -> q.range(r -> {
                    var range = r.field("price");
                    if (minPrice != null) range.gte(co.elastic.clients.json.JsonData.of(minPrice));
                    if (maxPrice != null) range.lte(co.elastic.clients.json.JsonData.of(maxPrice));
                    return range;
                })));
            }

            if (brandId != null) {
                mustQueries.add(Query.of(q -> q.term(t -> t.field("brandId").value(brandId))));
            }

            BoolQuery boolQuery = BoolQuery.of(b -> b.must(mustQueries));

            Query finalQuery;
            if (StringUtils.hasText(keyword)) {
                finalQuery = Query.of(q -> q.functionScore(fs -> fs
                        .query(Query.of(qb -> qb.bool(boolQuery)))
                        .functions(
                                FunctionScore.of(f -> f.fieldValueFactor(fvf -> fvf
                                        .field("sales")
                                        .factor(0.1)
                                        .modifier(co.elastic.clients.elasticsearch._types.query_dsl.FieldValueFactorModifier.Log1p)))
                        )
                        .scoreMode(FunctionScoreMode.Sum)
                        .boostMode(co.elastic.clients.elasticsearch._types.query_dsl.FunctionBoostMode.Multiply)));
            } else {
                finalQuery = Query.of(q -> q.bool(boolQuery));
            }

            int from = (pageNum - 1) * pageSize;

            var searchBuilder = esClient.search(s -> {
                s.index(ProductDocument.INDEX_NAME)
                        .query(finalQuery)
                        .from(from)
                        .size(pageSize);

                if (StringUtils.hasText(keyword)) {
                    s.highlight(h -> h
                            .preTags("<em class='highlight'>")
                            .postTags("</em>")
                            .fields("productName", HighlightField.of(hf -> hf))
                            .fields("description", HighlightField.of(hf -> hf))
                            .fields("brandNameSearch", HighlightField.of(hf -> hf)));
                }

                applySort(s, sortBy);
                return s;
            }, ProductDocument.class);

            SearchResponse<ProductDocument> response = searchBuilder;

            Page<ProductVO> voPage = new Page<>(pageNum, pageSize, response.hits().total().value());
            List<ProductVO> voList = response.hits().hits().stream().map(hit -> {
                ProductDocument doc = hit.source();
                ProductVO vo = new ProductVO();
                vo.setId(doc.getId());
                vo.setProductName(getHighlightedField(hit, "productName", doc.getProductName()));
                vo.setCategoryId(doc.getCategoryId());
                vo.setBrandId(doc.getBrandId());
                vo.setBrandName(doc.getBrandName());
                vo.setPrice(doc.getPrice());
                vo.setOriginalPrice(doc.getOriginalPrice());
                vo.setDescription(getHighlightedField(hit, "description", doc.getDescription()));
                vo.setMainImage(doc.getMainImage());
                vo.setStatus(doc.getStatus());
                vo.setSales(doc.getSales());
                vo.setTotalStock(doc.getTotalStock());
                if (doc.getCreateTime() != null) {
                    vo.setCreateTime(LocalDateTime.parse(doc.getCreateTime(), DTF));
                }
                return vo;
            }).collect(Collectors.toList());

            voPage.setRecords(voList);
            return voPage;
        } catch (Exception e) {
            log.error("ES搜索失败, 降级到数据库查询", e);
            return null;
        }
    }

    private void applySort(co.elastic.clients.elasticsearch.core.SearchRequest.Builder s, String sortBy) {
        if (sortBy == null) sortBy = "default";
        switch (sortBy) {
            case "price_asc":
                s.sort(so -> so.field(f -> f.field("price").order(SortOrder.Asc)));
                break;
            case "price_desc":
                s.sort(so -> so.field(f -> f.field("price").order(SortOrder.Desc)));
                break;
            case "sales":
                s.sort(so -> so.field(f -> f.field("sales").order(SortOrder.Desc)));
                break;
            case "newest":
                s.sort(so -> so.field(f -> f.field("createTime").order(SortOrder.Desc)));
                break;
            default:
                s.sort(so -> so.field(f -> f.field("sales").order(SortOrder.Desc)));
                s.sort(so -> so.field(f -> f.field("createTime").order(SortOrder.Desc)));
                break;
        }
    }

    private String getHighlightedField(Hit<ProductDocument> hit, String field, String original) {
        if (hit.highlight() != null && hit.highlight().containsKey(field)) {
            List<String> highlights = hit.highlight().get(field);
            if (!highlights.isEmpty()) {
                return highlights.get(0);
            }
        }
        return original;
    }

    public List<String> suggest(String prefix) {
        if (!StringUtils.hasText(prefix) || prefix.length() < 1) {
            return List.of();
        }
        try {
            SearchResponse<ProductDocument> response = esClient.search(s -> s
                            .index(ProductDocument.INDEX_NAME)
                            .query(q -> q.term(t -> t.field("status").value(1)))
                            .suggest(su -> su
                                    .suggesters("product_suggest", sg -> sg
                                            .prefix(prefix)
                                            .completion(cs -> cs
                                                    .field("suggest")
                                                    .size(10)
                                            )
                                    )
                            ),
                    ProductDocument.class);

            List<String> suggestions = new ArrayList<>();
            var suggestResponse = response.suggest();
            if (suggestResponse != null) {
                var productSuggest = suggestResponse.get("product_suggest");
                if (productSuggest != null) {
                    productSuggest.stream()
                            .flatMap(entry -> entry.completion().options().stream())
                            .map(option -> option.text())
                            .distinct()
                            .forEach(suggestions::add);
                }
            }

            return suggestions.stream().limit(10).collect(Collectors.toList());
        } catch (Exception e) {
            log.error("ES搜索建议失败", e);
            return List.of();
        }
    }

    public void recordSearch(String keyword, Long userId) {
        if (!StringUtils.hasText(keyword)) return;

        try {
            redisTemplate.opsForZSet().incrementScore(HOT_SEARCH_KEY, keyword, 1);
            redisTemplate.expire(HOT_SEARCH_KEY, 7, TimeUnit.DAYS);
        } catch (Exception e) {
            log.warn("记录热门搜索失败", e);
        }

        if (userId != null) {
            try {
                String historyKey = SEARCH_HISTORY_PREFIX + userId;
                redisTemplate.opsForList().remove(historyKey, 0, keyword);
                redisTemplate.opsForList().leftPush(historyKey, keyword);
                Long size = redisTemplate.opsForList().size(historyKey);
                if (size != null && size > MAX_HISTORY_SIZE) {
                    redisTemplate.opsForList().rightPop(historyKey);
                }
                redisTemplate.expire(historyKey, 30, TimeUnit.DAYS);
            } catch (Exception e) {
                log.warn("记录搜索历史失败", e);
            }
        }
    }

    public List<String> getHotSearches(int size) {
        try {
            var results = redisTemplate.opsForZSet().reverseRange(HOT_SEARCH_KEY, 0, size - 1);
            if (results != null) {
                return results.stream().map(Object::toString).collect(Collectors.toList());
            }
        } catch (Exception e) {
            log.warn("获取热门搜索失败", e);
        }
        return getDefaultHotSearches();
    }

    private List<String> getDefaultHotSearches() {
        return List.of("手机", "电脑", "耳机", "衣服", "鞋子");
    }

    public List<String> getSearchHistory(Long userId) {
        if (userId == null) return List.of();
        try {
            String historyKey = SEARCH_HISTORY_PREFIX + userId;
            List<Object> results = redisTemplate.opsForList().range(historyKey, 0, MAX_HISTORY_SIZE - 1);
            if (results != null) {
                return results.stream().map(Object::toString).collect(Collectors.toList());
            }
        } catch (Exception e) {
            log.warn("获取搜索历史失败", e);
        }
        return List.of();
    }

    public void clearSearchHistory(Long userId) {
        if (userId == null) return;
        try {
            redisTemplate.delete(SEARCH_HISTORY_PREFIX + userId);
        } catch (Exception e) {
            log.warn("清除搜索历史失败", e);
        }
    }

    public Map<String, List<Map<String, Object>>> getSearchFilters(Long categoryId, String keyword) {
        Map<String, List<Map<String, Object>>> filters = new HashMap<>();
        try {
            List<Query> mustQueries = new ArrayList<>();
            mustQueries.add(Query.of(q -> q.term(t -> t.field("status").value(1))));

            if (categoryId != null) {
                List<Long> categoryIds = new ArrayList<>();
                categoryIds.add(categoryId);
                List<ProductCategory> children = categoryMapper.selectList(
                        new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<ProductCategory>()
                                .eq(ProductCategory::getParentId, categoryId));
                children.forEach(c -> categoryIds.add(c.getId()));
                List<FieldValue> values = categoryIds.stream()
                        .map(id -> FieldValue.of(id))
                        .collect(Collectors.toList());
                mustQueries.add(Query.of(q -> q.terms(t -> t.field("categoryId").terms(
                        tv -> tv.value(values)))));
            }

            if (StringUtils.hasText(keyword)) {
                mustQueries.add(Query.of(q -> q.multiMatch(m -> m
                        .fields("productName^3", "brandNameSearch^2", "categoryNameSearch^1.5", "description^1")
                        .query(keyword))));
            }

            BoolQuery boolQuery = BoolQuery.of(b -> b.must(mustQueries));

            SearchResponse<ProductDocument> response = esClient.search(s -> s
                            .index(ProductDocument.INDEX_NAME)
                            .query(Query.of(q -> q.bool(boolQuery)))
                            .size(0)
                            .aggregations("brand_filter", Aggregation.of(a -> a
                                    .terms(t -> t.field("brandName").size(20))))
                            .aggregations("price_stats", Aggregation.of(a -> a
                                    .stats(st -> st.field("price")))),
                    ProductDocument.class);

            if (response.aggregations() != null) {
                var brandAgg = response.aggregations().get("brand_filter");
                if (brandAgg != null) {
                    List<Map<String, Object>> brandFilters = brandAgg.sterms().buckets().array().stream()
                            .map(b -> {
                                Map<String, Object> item = new HashMap<>();
                                item.put("name", b.key().stringValue());
                                item.put("count", b.docCount());
                                return item;
                            })
                            .collect(Collectors.toList());
                    filters.put("brands", brandFilters);
                }

                var priceAgg = response.aggregations().get("price_stats");
                if (priceAgg != null) {
                    List<Map<String, Object>> priceRanges = new ArrayList<>();
                    var stats = priceAgg.stats();
                    double min = Math.floor(stats.min() / 100) * 100;
                    double max = Math.ceil(stats.max() / 100) * 100;

                    if (max > min) {
                        double range = max - min;
                        int targetRanges = 6;
                        double step = Math.ceil(range / targetRanges / 100) * 100;
                        if (step < 100) step = 100;

                        double current = min;
                        while (current < max) {
                            double next = current + step;
                            if (next >= max) next = max;
                            Map<String, Object> priceRange = new HashMap<>();
                            priceRange.put("label", String.format("%.0f-%.0f", current, next));
                            priceRange.put("min", current);
                            priceRange.put("max", next);
                            priceRanges.add(priceRange);
                            current = next;
                        }
                    }
                    filters.put("priceRanges", priceRanges);
                }
            }
        } catch (Exception e) {
            log.error("获取搜索筛选条件失败", e);
        }
        return filters;
    }

    private ProductDocument buildDocumentFromProduct(Product p, Map<Long, String> categoryNameMap,
                                                      Map<Long, Long> parentCategoryMap,
                                                      Map<Long, String> brandNameMap,
                                                      Map<Long, Integer> stockMap) {
        ProductDocument doc = new ProductDocument();
        doc.setId(p.getId());
        doc.setProductName(p.getProductName());
        doc.setCategoryId(p.getCategoryId());
        doc.setCategoryName(categoryNameMap.get(p.getCategoryId()));
        doc.setCategoryNameSearch(categoryNameMap.get(p.getCategoryId()));
        doc.setParentCategoryId(parentCategoryMap.get(p.getCategoryId()));
        doc.setBrandId(p.getBrandId());
        String brandName = p.getBrandId() != null ? brandNameMap.get(p.getBrandId()) : null;
        doc.setBrandName(brandName);
        doc.setBrandNameSearch(brandName);
        doc.setPrice(p.getPrice());
        doc.setOriginalPrice(p.getOriginalPrice());
        doc.setDescription(p.getDescription());
        doc.setMainImage(p.getMainImage());
        doc.setStatus(p.getStatus());
        doc.setSales(p.getSales());
        doc.setTotalStock(stockMap.getOrDefault(p.getId(), 0));
        if (p.getCreateTime() != null) {
            doc.setCreateTime(p.getCreateTime().format(DTF));
        }
        List<String> suggestInputs = new ArrayList<>();
        suggestInputs.add(p.getProductName());
        if (brandNameMap.get(p.getBrandId()) != null) {
            suggestInputs.add(brandNameMap.get(p.getBrandId()));
        }
        if (categoryNameMap.get(p.getCategoryId()) != null) {
            suggestInputs.add(categoryNameMap.get(p.getCategoryId()));
        }
        doc.setSuggest(Map.of("input", suggestInputs));
        return doc;
    }

    private ProductDocument buildDocumentSingle(Product p) {
        ProductDocument doc = new ProductDocument();
        doc.setId(p.getId());
        doc.setProductName(p.getProductName());
        doc.setCategoryId(p.getCategoryId());
        doc.setBrandId(p.getBrandId());
        doc.setPrice(p.getPrice());
        doc.setOriginalPrice(p.getOriginalPrice());
        doc.setDescription(p.getDescription());
        doc.setMainImage(p.getMainImage());
        doc.setStatus(p.getStatus());
        doc.setSales(p.getSales());
        if (p.getCreateTime() != null) {
            doc.setCreateTime(p.getCreateTime().format(DTF));
        }

        List<String> suggestInputs = new ArrayList<>();
        suggestInputs.add(p.getProductName());

        if (p.getCategoryId() != null) {
            ProductCategory cat = categoryMapper.selectById(p.getCategoryId());
            if (cat != null) {
                doc.setCategoryName(cat.getCategoryName());
                doc.setCategoryNameSearch(cat.getCategoryName());
                doc.setParentCategoryId(cat.getParentId());
                suggestInputs.add(cat.getCategoryName());
            }
        }
        if (p.getBrandId() != null) {
            Brand brand = brandMapper.selectById(p.getBrandId());
            if (brand != null) {
                doc.setBrandName(brand.getBrandName());
                doc.setBrandNameSearch(brand.getBrandName());
                suggestInputs.add(brand.getBrandName());
            }
        }

        doc.setSuggest(Map.of("input", suggestInputs));

        List<ProductSku> skus = skuMapper.selectList(
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<ProductSku>()
                        .eq(ProductSku::getProductId, p.getId())
                        .eq(ProductSku::getStatus, 1));
        doc.setTotalStock(skus.stream().mapToInt(ProductSku::getStock).sum());

        return doc;
    }
}
