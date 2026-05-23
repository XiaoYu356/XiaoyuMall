package com.mall.order.mq;

import com.alibaba.fastjson2.JSON;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.messaging.Message;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
public class OrderMessageProducer {

    public static final String TOPIC = "order-create-topic";

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    public boolean sendOrderCreateMessage(OrderCreateMessage orderMessage) {
        try {
            String json = JSON.toJSONString(orderMessage);
            Message<String> message = MessageBuilder
                    .withPayload(json)
                    .setHeader("KEYS", orderMessage.getOrderNo())
                    .build();

            rocketMQTemplate.syncSend(TOPIC, message);
            log.info("订单创建消息发送成功: orderNo={}", orderMessage.getOrderNo());
            return true;
        } catch (Exception e) {
            log.error("订单创建消息发送失败: orderNo={}", orderMessage.getOrderNo(), e);
            return false;
        }
    }
}
