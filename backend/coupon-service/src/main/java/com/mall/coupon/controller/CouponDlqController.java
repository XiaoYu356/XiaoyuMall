package com.mall.coupon.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.mall.common.constant.RedisConstant;
import com.mall.common.result.Result;
import com.mall.coupon.mq.CouponMessageProducer;
import com.mall.coupon.mq.CouponReceiveMessage;
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
@RequestMapping("/api/v1/coupons/dlq")
@SaCheckPermission("coupon:manage")
@Tag(name = "优惠券死信队列管理", description = "查询和重试失败的优惠券消息")
public class CouponDlqController {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @Autowired(required = false)
    private CouponMessageProducer couponMessageProducer;

    @GetMapping
    @Operation(summary = "查询DLQ失败记录")
    public Result<List<Map<Object, Object>>> listDlqRecords() {
        if (couponMessageProducer == null) {
            return Result.failed("RocketMQ未启用");
        }
        Set<String> keys = stringRedisTemplate.keys(RedisConstant.DLQ_COUPON_KEY + "*");
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

    @PostMapping("/retry/{userId}/{templateId}")
    @Operation(summary = "手动重试DLQ消息")
    public Result<String> retryDlqMessage(@PathVariable Long userId, @PathVariable Long templateId) {
        if (couponMessageProducer == null) {
            return Result.failed("RocketMQ未启用，无法重试");
        }
        String key = RedisConstant.DLQ_COUPON_KEY + userId + "_" + templateId;
        Map<Object, Object> record = stringRedisTemplate.opsForHash().entries(key);
        if (record.isEmpty()) {
            return Result.failed("未找到DLQ记录");
        }

        String rawMessage = (String) record.get("rawMessage");
        if (rawMessage == null) {
            return Result.failed("DLQ记录缺少原始消息");
        }

        CouponReceiveMessage msg = com.alibaba.fastjson2.JSON.parseObject(rawMessage, CouponReceiveMessage.class);
        boolean sent = couponMessageProducer.sendReceiveMessage(msg);
        if (!sent) {
            return Result.failed("重新发送消息失败");
        }

        stringRedisTemplate.delete(key);
        log.info("DLQ消息手动重试: userId={}, templateId={}", userId, templateId);
        return Result.success("消息已重新发送");
    }

    @DeleteMapping("/{userId}/{templateId}")
    @Operation(summary = "删除DLQ记录（已人工线下处理）")
    public Result<String> deleteDlqRecord(@PathVariable Long userId, @PathVariable Long templateId) {
        String key = RedisConstant.DLQ_COUPON_KEY + userId + "_" + templateId;
        stringRedisTemplate.delete(key);
        log.info("DLQ记录已删除: userId={}, templateId={}", userId, templateId);
        return Result.success("记录已删除");
    }
}
