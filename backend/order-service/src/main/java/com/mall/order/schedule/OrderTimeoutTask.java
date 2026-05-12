package com.mall.order.schedule;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.mall.order.entity.Order;
import com.mall.order.entity.OrderItem;
import com.mall.order.feign.ProductServiceClient;
import com.mall.order.mapper.OrderItemMapper;
import com.mall.order.mapper.OrderMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Component
public class OrderTimeoutTask {

    @Autowired
    private OrderMapper orderMapper;

    @Autowired
    private OrderItemMapper orderItemMapper;

    @Autowired
    private ProductServiceClient productServiceClient;

    @Value("${order.timeout-minutes:15}")
    private int timeoutMinutes;

    @Value("${order.stock-retry-times:3}")
    private int stockRetryTimes;

    @Scheduled(fixedDelay = 60000)
    public void cancelTimeoutOrders() {
        LocalDateTime timeoutThreshold = LocalDateTime.now().minusMinutes(timeoutMinutes);

        LambdaQueryWrapper<Order> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(Order::getStatus, 0)
                   .lt(Order::getCreateTime, timeoutThreshold);

        List<Order> timeoutOrders = orderMapper.selectList(queryWrapper);

        if (timeoutOrders.isEmpty()) {
            return;
        }

        log.info("扫描到{}个超时未支付订单", timeoutOrders.size());

        for (Order order : timeoutOrders) {
            try {
                boolean cancelled = cancelOrder(order);
                if (cancelled) {
                    log.info("订单超时自动取消: {}", order.getOrderNo());
                }
            } catch (Exception e) {
                log.error("订单自动取消失败: {}", order.getOrderNo(), e);
            }
        }
    }

    private boolean cancelOrder(Order order) {
        LambdaUpdateWrapper<Order> updateWrapper = new LambdaUpdateWrapper<>();
        updateWrapper.eq(Order::getId, order.getId())
                    .eq(Order::getStatus, 0)
                    .set(Order::getStatus, 4);

        int rows = orderMapper.update(null, updateWrapper);
        if (rows > 0) {
            rollbackStock(order.getId());
            return true;
        }
        return false;
    }

    private void rollbackStock(Long orderId) {
        LambdaQueryWrapper<OrderItem> itemWrapper = new LambdaQueryWrapper<>();
        itemWrapper.eq(OrderItem::getOrderId, orderId);
        List<OrderItem> items = orderItemMapper.selectList(itemWrapper);

        for (OrderItem item : items) {
            boolean success = false;
            for (int i = 0; i < stockRetryTimes; i++) {
                try {
                    productServiceClient.addStock(item.getSkuId(), item.getQuantity());
                    success = true;
                    break;
                } catch (Exception e) {
                    log.warn("库存回滚第{}次失败, skuId={}, quantity={}", i + 1, item.getSkuId(), item.getQuantity(), e);
                }
            }
            if (!success) {
                log.error("库存回滚最终失败, skuId={}, quantity={}, 需人工处理", item.getSkuId(), item.getQuantity());
            }

            try {
                productServiceClient.decrementSales(item.getProductId(), item.getQuantity());
            } catch (Exception e) {
                log.warn("销量回滚失败, productId={}, quantity={}", item.getProductId(), item.getQuantity(), e);
            }
        }
    }
}
