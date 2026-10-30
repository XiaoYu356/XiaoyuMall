package com.mall.product.config;

import com.mall.product.es.ProductSearchService;
import com.mall.product.service.ProductService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class StockInitRunner implements CommandLineRunner {

    @Autowired
    private ProductService productService;

    @Autowired
    private ProductSearchService productSearchService;

    @Override
    public void run(String... args) {
        try {
            log.info("开始同步库存数据到Redis...");
            productService.syncStockToRedis();
        } catch (Exception e) {
            log.warn("启动时库存同步失败，可手动调用 /api/v1/products/stock/sync 接口同步", e);
        }

        try {
            log.info("开始同步商品数据到Elasticsearch...");
            // 启动只建索引不删索引，避免重启期间搜索不可用
            productSearchService.createIndexIfNeeded();
            // 索引为空时才全量同步，否则靠 MQ 增量同步
            productSearchService.syncAllProductsIfEmpty();
        } catch (Exception e) {
            log.warn("启动时ES同步失败，可手动调用 /api/v1/products/es/sync 接口同步", e);
        }
    }
}
