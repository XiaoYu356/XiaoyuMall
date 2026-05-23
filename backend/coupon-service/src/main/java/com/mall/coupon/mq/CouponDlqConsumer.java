package com.mall.coupon.mq;

import com.alibaba.fastjson2.JSON;
import com.mall.common.constant.RedisConstant;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
@RocketMQMessageListener(
        topic = "%DLQ%coupon-consumer-group",
        consumerGroup = "coupon-dlq-consumer-group"
)
public class CouponDlqConsumer implements RocketMQListener<String> {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    private static final String ROLLBACK_SCRIPT =
            "local stockKey = KEYS[1] " +
            "local userKey = KEYS[2] " +
            "local userId = ARGV[1] " +
            "redis.call('incr', stockKey) " +
            "redis.call('srem', userKey, userId) " +
            "return 1";

    @Override
    public void onMessage(String message) {
        CouponReceiveMessage msg = JSON.parseObject(message, CouponReceiveMessage.class);
        log.error("优惠券消息进入死信队列: userId={}, templateId={}", msg.getUserId(), msg.getTemplateId());

        rollbackRedis(msg.getTemplateId(), msg.getUserId());

        saveDlqRecord(msg);

        log.info("优惠券DLQ处理完成: userId={}, templateId={}, Redis已回滚, 失败记录已保存", msg.getUserId(), msg.getTemplateId());
    }

    private void rollbackRedis(Long templateId, Long userId) {
        try {
            String stockKey = RedisConstant.COUPON_STOCK_KEY + templateId;
            String userKey = RedisConstant.USER_COUPON_KEY + templateId;
            DefaultRedisScript<Long> rollbackScript = new DefaultRedisScript<>(ROLLBACK_SCRIPT, Long.class);
            stringRedisTemplate.execute(rollbackScript, Arrays.asList(stockKey, userKey), userId.toString());
            log.info("DLQ Redis回滚成功: templateId={}, userId={}", templateId, userId);
        } catch (Exception e) {
            log.error("DLQ Redis回滚失败: templateId={}, userId={}", templateId, userId, e);
        }
    }

    private void saveDlqRecord(CouponReceiveMessage msg) {
        try {
            String key = RedisConstant.DLQ_COUPON_KEY + msg.getUserId() + "_" + msg.getTemplateId();
            Map<String, Object> record = new HashMap<>();
            record.put("userId", msg.getUserId().toString());
            record.put("templateId", msg.getTemplateId().toString());
            record.put("type", "coupon_receive");
            record.put("status", "pending");
            record.put("rawMessage", JSON.toJSONString(msg));
            stringRedisTemplate.opsForHash().putAll(key, record);
            stringRedisTemplate.expire(key, 7, TimeUnit.DAYS);
            log.info("DLQ记录已保存: userId={}, templateId={}", msg.getUserId(), msg.getTemplateId());
        } catch (Exception e) {
            log.error("DLQ记录保存失败: userId={}, templateId={}", msg.getUserId(), msg.getTemplateId(), e);
        }
    }
}
