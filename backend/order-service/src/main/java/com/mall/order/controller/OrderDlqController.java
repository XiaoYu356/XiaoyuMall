package com.mall.order.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.mall.common.constant.RedisConstant;
import com.mall.common.result.Result;
import com.mall.order.mq.OrderCreateMessage;
import com.mall.order.mq.OrderMessageProducer;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Slf4j
@RestController
@RequestMapping("/api/v1/orders/dlq")
@SaCheckPermission("order:manage")
@Tag(name = "订单死信队列管理", description = "查询和重试失败的订单消息")
public class OrderDlqController {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Autowired(required = false)
    private OrderMessageProducer orderMessageProducer;

    @GetMapping
    @Operation(summary = "查询DLQ失败记录")
    public Result<List<Map<Object, Object>>> listDlqRecords() {
        if (orderMessageProducer == null) {
            return Result.failed("RocketMQ未启用");
        }
        Set<String> keys = stringRedisTemplate.keys(RedisConstant.DLQ_ORDER_KEY + "*");
        List<Map<Object, Object>> records = new ArrayList<>();
        if (keys != null) {
            for (String key : keys) {
                Map<Object, Object> record = stringRedisTemplate.opsForHash().entries(key);
                if (!record.isEmpty()) {
                    record.put("_key", key);
                    records.add(record);
                }
            }
        }
        return Result.success(records);
    }

    @PostMapping("/retry/{orderNo}")
    @Operation(summary = "手动重试DLQ消息")
    public Result<String> retryDlqMessage(@PathVariable String orderNo) {
        if (orderMessageProducer == null) {
            return Result.failed("RocketMQ未启用，无法重试");
        }
        String key = RedisConstant.DLQ_ORDER_KEY + orderNo;
        Map<Object, Object> record = stringRedisTemplate.opsForHash().entries(key);
        if (record.isEmpty()) {
            return Result.failed("未找到DLQ记录: " + orderNo);
        }

        String rawMessage = (String) record.get("rawMessage");
        if (rawMessage == null) {
            return Result.failed("DLQ记录缺少原始消息");
        }

        OrderCreateMessage msg = com.alibaba.fastjson2.JSON.parseObject(rawMessage, OrderCreateMessage.class);
        boolean sent = orderMessageProducer.sendOrderCreateMessage(msg);
        if (!sent) {
            return Result.failed("重新发送消息失败");
        }

        stringRedisTemplate.delete(key);
        log.info("DLQ消息手动重试: orderNo={}", orderNo);
        return Result.success("消息已重新发送");
    }

    @DeleteMapping("/{orderNo}")
    @Operation(summary = "删除DLQ记录（已人工线下处理）")
    public Result<String> deleteDlqRecord(@PathVariable String orderNo) {
        String key = RedisConstant.DLQ_ORDER_KEY + orderNo;
        stringRedisTemplate.delete(key);
        log.info("DLQ记录已删除: orderNo={}", orderNo);
        return Result.success("记录已删除");
    }
}
