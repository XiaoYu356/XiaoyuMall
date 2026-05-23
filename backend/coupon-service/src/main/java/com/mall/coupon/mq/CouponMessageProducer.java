package com.mall.coupon.mq;

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
public class CouponMessageProducer {

    public static final String TOPIC = "coupon-receive-topic";

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    public boolean sendReceiveMessage(CouponReceiveMessage message) {
        try {
            String json = JSON.toJSONString(message);
            Message<String> msg = MessageBuilder
                    .withPayload(json)
                    .setHeader("KEYS", message.getUserId() + "_" + message.getTemplateId())
                    .build();

            rocketMQTemplate.syncSend(TOPIC, msg);
            log.info("优惠券领取消息发送成功: userId={}, templateId={}", message.getUserId(), message.getTemplateId());
            return true;
        } catch (Exception e) {
            log.error("优惠券领取消息发送失败: userId={}, templateId={}", message.getUserId(), message.getTemplateId(), e);
            return false;
        }
    }
}
