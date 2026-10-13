package com.mall.product.mq;

import com.alibaba.fastjson2.JSON;
import com.mall.product.entity.Product;
import com.mall.product.es.ProductSearchService;
import com.mall.product.mapper.ProductMapper;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * 商品ES同步消息消费者
 * 消费MQ消息，执行ES同步操作
 * ES操作天然幂等（按product ID覆盖文档），重试安全
 */
@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
@RocketMQMessageListener(
        topic = ProductEsSyncProducer.TOPIC,
        consumerGroup = "product-es-sync-consumer-group"
)
public class ProductEsSyncConsumer implements RocketMQListener<String> {

    @Autowired
    private ProductMapper productMapper;

    @Autowired
    private ProductSearchService productSearchService;

    @Override
    public void onMessage(String message) {
        ProductChangeMessage msg = JSON.parseObject(message, ProductChangeMessage.class);
        log.info("收到商品ES同步消息: productId={}, action={}", msg.getProductId(), msg.getAction());

        try {
            if (ProductChangeMessage.ACTION_DELETE.equals(msg.getAction())) {
                productSearchService.deleteProduct(msg.getProductId());
            } else {
                Product product = productMapper.selectById(msg.getProductId());
                if (product != null) {
                    productSearchService.syncProduct(product);
                } else {
                    log.warn("商品不存在，跳过ES同步: productId={}", msg.getProductId());
                }
            }
            log.info("商品ES同步完成: productId={}, action={}", msg.getProductId(), msg.getAction());
        } catch (Exception e) {
            log.error("商品ES同步失败: productId={}, action={}", msg.getProductId(), msg.getAction(), e);
            throw e;
        }
    }
}
