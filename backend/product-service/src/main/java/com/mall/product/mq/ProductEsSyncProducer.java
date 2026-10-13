package com.mall.product.mq;

import com.alibaba.fastjson2.JSON;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.messaging.Message;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

/**
 * 商品ES同步消息生产者
 * 监听事务提交事件，确保MySQL事务提交成功后才发MQ
 */
@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
public class ProductEsSyncProducer {

    public static final String TOPIC = "product-es-sync-topic";

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onProductChange(ProductChangeMessage event) {
        try {
            String json = JSON.toJSONString(event);
            Message<String> message = MessageBuilder
                    .withPayload(json)
                    .setHeader("KEYS", String.valueOf(event.getProductId()))
                    .build();

            rocketMQTemplate.syncSend(TOPIC, message);
            log.info("商品ES同步消息发送成功: productId={}, action={}", event.getProductId(), event.getAction());
        } catch (Exception e) {
            log.error("商品ES同步消息发送失败: productId={}, action={}", event.getProductId(), event.getAction(), e);
        }
    }
}
