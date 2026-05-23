package com.mall.product.config;

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

    @Override
    public void run(String... args) {
        try {
            log.info("开始同步库存数据到Redis...");
            productService.syncStockToRedis();
        } catch (Exception e) {
            log.warn("启动时库存同步失败，可手动调用 /api/v1/products/stock/sync 接口同步", e);
        }
    }
}
