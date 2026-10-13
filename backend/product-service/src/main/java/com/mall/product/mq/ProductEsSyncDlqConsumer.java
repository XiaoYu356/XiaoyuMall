package com.mall.product.mq;

import com.alibaba.fastjson2.JSON;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 商品ES同步死信队列消费者
 * 消费失败3次后进入DLQ，记录到Redis供人工排查
 * 可通过 POST /api/v1/products/es/sync 全量重建兜底
 */
@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
@RocketMQMessageListener(
        topic = "%DLQ%product-es-sync-consumer-group",
        consumerGroup = "product-es-sync-dlq-consumer-group"
)
public class ProductEsSyncDlqConsumer implements RocketMQListener<String> {

    private static final String DLQ_KEY_PREFIX = "mall:dlq:product-es:";

    private final StringRedisTemplate stringRedisTemplate;

    public ProductEsSyncDlqConsumer(StringRedisTemplate stringRedisTemplate) {
        this.stringRedisTemplate = stringRedisTemplate;
    }

    @Override
    public void onMessage(String message) {
        ProductChangeMessage msg = JSON.parseObject(message, ProductChangeMessage.class);
        log.error("商品ES同步消息进入死信队列: productId={}, action={}", msg.getProductId(), msg.getAction());

        try {
            String key = DLQ_KEY_PREFIX + msg.getProductId();
            Map<String, String> record = new HashMap<>();
            record.put("productId", String.valueOf(msg.getProductId()));
            record.put("action", msg.getAction());
            record.put("status", "pending");
            record.put("rawMessage", JSON.toJSONString(msg));
            stringRedisTemplate.opsForHash().putAll(key, record);
            stringRedisTemplate.expire(key, 7, TimeUnit.DAYS);
            log.info("商品ES同步DLQ记录已保存: productId={}, 可通过 /api/v1/products/es/sync 全量重建", msg.getProductId());
        } catch (Exception e) {
            log.error("DLQ记录保存失败: productId={}", msg.getProductId(), e);
        }
    }
}
