package com.mall.order.mq;

import com.alibaba.fastjson2.JSON;
import com.mall.common.constant.RedisConstant;
import com.mall.order.service.StockRedisService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
@RocketMQMessageListener(
        topic = "%DLQ%order-consumer-group",
        consumerGroup = "order-dlq-consumer-group"
)
public class OrderDlqConsumer implements RocketMQListener<String> {

    @Autowired
    private StockRedisService stockRedisService;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Override
    public void onMessage(String message) {
        OrderCreateMessage orderMsg = JSON.parseObject(message, OrderCreateMessage.class);
        log.error("订单消息进入死信队列: orderNo={}", orderMsg.getOrderNo());

        rollbackRedisStock(orderMsg);

        saveDlqRecord(orderMsg);

        log.info("订单DLQ处理完成: orderNo={}, Redis库存已回滚, 失败记录已保存", orderMsg.getOrderNo());
    }

    private void rollbackRedisStock(OrderCreateMessage orderMsg) {
        try {
            List<Long> skuIds = new ArrayList<>();
            List<Integer> quantities = new ArrayList<>();
            for (OrderCreateMessage.OrderItemMessage item : orderMsg.getItems()) {
                if (item.getSkuId() != null) {
                    skuIds.add(item.getSkuId());
                    quantities.add(item.getQuantity());
                }
            }
            if (!skuIds.isEmpty()) {
                stockRedisService.addStock(skuIds, quantities);
                log.info("DLQ Redis库存回滚成功: orderNo={}", orderMsg.getOrderNo());
            }
        } catch (Exception e) {
            log.error("DLQ Redis库存回滚失败: orderNo={}", orderMsg.getOrderNo(), e);
        }
    }

    private void saveDlqRecord(OrderCreateMessage orderMsg) {
        try {
            String key = RedisConstant.DLQ_ORDER_KEY + orderMsg.getOrderNo();
            Map<String, Object> record = new HashMap<>();
            record.put("orderNo", orderMsg.getOrderNo());
            record.put("userId", orderMsg.getUserId());
            record.put("type", "order_create");
            record.put("status", "pending");
            record.put("rawMessage", JSON.toJSONString(orderMsg));
            stringRedisTemplate.opsForHash().putAll(key, record);
            stringRedisTemplate.expire(key, 7, TimeUnit.DAYS);
            log.info("DLQ记录已保存: orderNo={}", orderMsg.getOrderNo());
        } catch (Exception e) {
            log.error("DLQ记录保存失败: orderNo={}", orderMsg.getOrderNo(), e);
        }
    }
}
