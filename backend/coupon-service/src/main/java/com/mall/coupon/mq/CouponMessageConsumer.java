package com.mall.coupon.mq;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.mall.common.constant.RedisConstant;
import com.mall.coupon.entity.CouponTemplate;
import com.mall.coupon.entity.UserCoupon;
import com.mall.coupon.mapper.CouponTemplateMapper;
import com.mall.coupon.mapper.UserCouponMapper;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Arrays;
import java.util.UUID;

@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
@RocketMQMessageListener(
        topic = CouponMessageProducer.TOPIC,
        consumerGroup = "coupon-consumer-group"
)
public class CouponMessageConsumer implements RocketMQListener<String> {

    private static final int MAX_RETRY_TIMES = 3;

    @Autowired
    private CouponTemplateMapper couponTemplateMapper;

    @Autowired
    private UserCouponMapper userCouponMapper;

    @Autowired
    private TransactionTemplate transactionTemplate;

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
        log.info("收到优惠券领取消息: userId={}, templateId={}", msg.getUserId(), msg.getTemplateId());

        if (isAlreadyProcessed(msg)) {
            log.info("优惠券已领取过，跳过: userId={}, templateId={}", msg.getUserId(), msg.getTemplateId());
            return;
        }

        try {
            processReceive(msg);
            log.info("优惠券领取完成: userId={}, templateId={}", msg.getUserId(), msg.getTemplateId());
        } catch (Exception e) {
            log.error("优惠券领取失败: userId={}, templateId={}", msg.getUserId(), msg.getTemplateId(), e);
            throw e;
        }
    }

    private boolean isAlreadyProcessed(CouponReceiveMessage msg) {
        LambdaQueryWrapper<UserCoupon> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserCoupon::getUserId, msg.getUserId())
               .eq(UserCoupon::getTemplateId, msg.getTemplateId());
        return userCouponMapper.selectCount(wrapper) > 0;
    }

    private void processReceive(CouponReceiveMessage msg) {
        CouponTemplate template = couponTemplateMapper.selectById(msg.getTemplateId());
        if (template == null) {
            log.error("优惠券模板不存在，回滚Redis: templateId={}", msg.getTemplateId());
            rollbackRedis(msg.getTemplateId(), msg.getUserId());
            return;
        }
        if (template.getStatus() != 1) {
            log.warn("优惠券已禁用，回滚Redis: templateId={}", msg.getTemplateId());
            rollbackRedis(msg.getTemplateId(), msg.getUserId());
            return;
        }
        if (LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isAfter(template.getEndTime())) {
            log.warn("优惠券已过期，回滚Redis: templateId={}", msg.getTemplateId());
            rollbackRedis(msg.getTemplateId(), msg.getUserId());
            return;
        }

        try {
            transactionTemplate.executeWithoutResult(status -> {
                UserCoupon userCoupon = new UserCoupon();
                userCoupon.setUserId(msg.getUserId());
                userCoupon.setTemplateId(msg.getTemplateId());
                userCoupon.setCouponCode("CPN" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
                userCoupon.setStatus(0);
                userCoupon.setExpireTime(template.getEndTime());
                userCouponMapper.insert(userCoupon);

                int updated = couponTemplateMapper.incrementUsedCount(msg.getTemplateId());
                if (updated == 0) {
                    status.setRollbackOnly();
                    throw new RuntimeException("优惠券已领完");
                }

                log.info("优惠券写入MySQL成功: userId={}, templateId={}, couponId={}", msg.getUserId(), msg.getTemplateId(), userCoupon.getId());
            });
        } catch (Exception e) {
            if (isBusinessError(e)) {
                log.warn("业务异常，回滚Redis: userId={}, templateId={}, error={}", msg.getUserId(), msg.getTemplateId(), e.getMessage());
                rollbackRedis(msg.getTemplateId(), msg.getUserId());
                return;
            }
            log.error("系统异常，等待RocketMQ重试: userId={}, templateId={}", msg.getUserId(), msg.getTemplateId(), e);
            throw e;
        }
    }

    private boolean isBusinessError(Exception e) {
        String msg = e.getMessage();
        if (msg == null) return false;
        return msg.contains("已领完") || msg.contains("不存在");
    }

    private void rollbackRedis(Long templateId, Long userId) {
        try {
            String stockKey = RedisConstant.COUPON_STOCK_KEY + templateId;
            String userKey = RedisConstant.USER_COUPON_KEY + templateId;
            DefaultRedisScript<Long> rollbackScript = new DefaultRedisScript<>(ROLLBACK_SCRIPT, Long.class);
            stringRedisTemplate.execute(rollbackScript, Arrays.asList(stockKey, userKey), userId.toString());
            log.info("Redis回滚成功: templateId={}, userId={}", templateId, userId);
        } catch (Exception e) {
            log.error("Redis回滚失败，需人工处理: templateId={}, userId={}", templateId, userId, e);
        }
    }
}
