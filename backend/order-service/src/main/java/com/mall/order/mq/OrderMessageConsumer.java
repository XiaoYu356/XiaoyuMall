package com.mall.order.mq;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.mall.common.constant.RedisConstant;
import com.mall.common.result.Result;
import com.mall.order.entity.Order;
import com.mall.order.entity.OrderItem;
import com.mall.order.entity.Product;
import com.mall.order.entity.ProductSku;
import com.mall.order.feign.CouponServiceClient;
import com.mall.order.feign.ProductServiceClient;
import com.mall.order.mapper.OrderItemMapper;
import com.mall.order.mapper.OrderMapper;
import com.mall.order.service.StockRedisService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
@RocketMQMessageListener(
        topic = OrderMessageProducer.TOPIC,
        consumerGroup = "order-consumer-group"
)
public class OrderMessageConsumer implements RocketMQListener<String> {

    @Autowired
    private OrderMapper orderMapper;

    @Autowired
    private OrderItemMapper orderItemMapper;

    @Autowired
    private ProductServiceClient productServiceClient;

    @Autowired
    private CouponServiceClient couponServiceClient;

    @Autowired
    private StockRedisService stockRedisService;

    @Autowired
    private TransactionTemplate transactionTemplate;

    @Override
    public void onMessage(String message) {
        OrderCreateMessage orderMsg = JSON.parseObject(message, OrderCreateMessage.class);
        log.info("收到订单创建消息: orderNo={}", orderMsg.getOrderNo());

        if (isAlreadyProcessed(orderMsg.getOrderNo())) {
            log.info("订单已处理过，跳过: orderNo={}", orderMsg.getOrderNo());
            return;
        }

        try {
            processOrder(orderMsg);
            log.info("订单创建完成: orderNo={}", orderMsg.getOrderNo());
        } catch (Exception e) {
            log.error("订单创建失败: orderNo={}", orderMsg.getOrderNo(), e);
            if (isBusinessError(e)) {
                log.warn("业务异常，回滚Redis库存: orderNo={}", orderMsg.getOrderNo());
                rollbackRedisStock(orderMsg);
                return;
            }
            log.error("系统异常，等待RocketMQ重试: orderNo={}", orderMsg.getOrderNo());
            throw e;
        }
    }

    private boolean isAlreadyProcessed(String orderNo) {
        LambdaQueryWrapper<Order> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Order::getOrderNo, orderNo);
        return orderMapper.selectCount(wrapper) > 0;
    }

    private void processOrder(OrderCreateMessage orderMsg) {
        Order order = new Order();
        order.setOrderNo(orderMsg.getOrderNo());
        order.setUserId(orderMsg.getUserId());
        order.setStatus(0);
        order.setRemark(orderMsg.getRemark());
        order.setReceiverName(orderMsg.getReceiverName());
        order.setReceiverPhone(orderMsg.getReceiverPhone());
        order.setReceiverAddress(orderMsg.getReceiverAddress());

        BigDecimal totalAmount = BigDecimal.ZERO;
        List<OrderItem> orderItems = new ArrayList<>();

        for (OrderCreateMessage.OrderItemMessage itemMsg : orderMsg.getItems()) {
            Result<Product> productResult = productServiceClient.getProductById(itemMsg.getProductId());
            Product product = productResult != null ? productResult.getData() : null;
            if (product == null) {
                throw new RuntimeException("商品不存在, productId=" + itemMsg.getProductId());
            }

            ProductSku sku = null;
            if (itemMsg.getSkuId() != null) {
                Result<ProductSku> skuResult = productServiceClient.getSkuById(itemMsg.getSkuId());
                sku = skuResult != null ? skuResult.getData() : null;
            }

            OrderItem item = new OrderItem();
            item.setProductId(itemMsg.getProductId());
            item.setSkuId(itemMsg.getSkuId());
            item.setQuantity(itemMsg.getQuantity());
            item.setPrice(sku != null && sku.getPrice() != null ? sku.getPrice() : product.getPrice());
            item.setTotalAmount(item.getPrice().multiply(BigDecimal.valueOf(itemMsg.getQuantity())));
            item.setProductName(product.getProductName());
            item.setSkuName(sku != null && sku.getSkuName() != null ? sku.getSkuName() : product.getProductName());
            item.setSkuCode(sku != null && sku.getSkuCode() != null ? sku.getSkuCode() : "SKU" + itemMsg.getSkuId());
            item.setProductImage(product.getMainImage());
            item.setOrderNo(order.getOrderNo());

            totalAmount = totalAmount.add(item.getTotalAmount());
            orderItems.add(item);
        }

        order.setTotalAmount(totalAmount);

        if (orderMsg.getCouponId() != null) {
            Result<BigDecimal> discountResult = couponServiceClient.calculateDiscount(orderMsg.getCouponId(), totalAmount);
            BigDecimal discount = discountResult != null ? discountResult.getData() : BigDecimal.ZERO;
            order.setCouponId(orderMsg.getCouponId());
            order.setDiscountAmount(discount != null ? discount : BigDecimal.ZERO);
            order.setPayAmount(totalAmount.subtract(order.getDiscountAmount()));
        } else {
            order.setPayAmount(totalAmount);
            order.setDiscountAmount(BigDecimal.ZERO);
        }

        if (order.getPayAmount().compareTo(BigDecimal.ZERO) < 0) {
            order.setPayAmount(BigDecimal.ZERO);
        }

        transactionTemplate.executeWithoutResult(status -> {
            orderMapper.insert(order);
            for (OrderItem item : orderItems) {
                item.setOrderId(order.getId());
                orderItemMapper.insert(item);
            }
        });

        log.info("订单写入MySQL成功: orderNo={}, orderId={}", order.getOrderNo(), order.getId());

        Map<Long, Integer> skuDeductMap = new LinkedHashMap<>();
        Map<Long, Integer> salesMap = new LinkedHashMap<>();
        for (OrderCreateMessage.OrderItemMessage itemMsg : orderMsg.getItems()) {
            if (itemMsg.getSkuId() != null) {
                skuDeductMap.merge(itemMsg.getSkuId(), itemMsg.getQuantity(), Integer::sum);
            }
            salesMap.merge(itemMsg.getProductId(), itemMsg.getQuantity(), Integer::sum);
        }

        List<Long> deductedSkuIds = new ArrayList<>();
        List<Integer> deductedQuantities = new ArrayList<>();
        try {
            for (Map.Entry<Long, Integer> entry : skuDeductMap.entrySet()) {
                Result<Boolean> stockResult = productServiceClient.deductStock(entry.getKey(), entry.getValue());
                if (stockResult == null || !Boolean.TRUE.equals(stockResult.getData())) {
                    throw new RuntimeException("MySQL库存扣减失败, skuId=" + entry.getKey());
                }
                deductedSkuIds.add(entry.getKey());
                deductedQuantities.add(entry.getValue());
            }

            for (Map.Entry<Long, Integer> entry : salesMap.entrySet()) {
                Result<Boolean> salesResult = productServiceClient.incrementSales(entry.getKey(), entry.getValue());
                if (salesResult == null || !Boolean.TRUE.equals(salesResult.getData())) {
                    log.warn("商品销量更新失败, productId={}, quantity={}", entry.getKey(), entry.getValue());
                }
            }
        } catch (Exception e) {
            if (!deductedSkuIds.isEmpty()) {
                try {
                    productServiceClient.addStock(deductedSkuIds.get(0), deductedQuantities.get(0));
                } catch (Exception ex) {
                    log.error("MySQL库存回滚失败，需人工处理: skuId={}", deductedSkuIds.get(0), ex);
                }
            }
            deleteOrder(order.getId());
            throw e;
        }
    }

    private void deleteOrder(Long orderId) {
        try {
            orderItemMapper.delete(new LambdaQueryWrapper<OrderItem>().eq(OrderItem::getOrderId, orderId));
            orderMapper.deleteById(orderId);
            log.info("清理失败订单: orderId={}", orderId);
        } catch (Exception e) {
            log.error("清理失败订单异常，需人工处理: orderId={}", orderId, e);
        }
    }

    private boolean isBusinessError(Exception e) {
        String msg = e.getMessage();
        if (msg == null) return false;
        return msg.contains("不存在") || msg.contains("库存扣减失败") || msg.contains("库存不足");
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
                log.info("Redis库存回滚成功: orderNo={}", orderMsg.getOrderNo());
            }
        } catch (Exception e) {
            log.error("Redis库存回滚失败，需人工处理: orderNo={}", orderMsg.getOrderNo(), e);
        }
    }
}
