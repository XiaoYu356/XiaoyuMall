package com.mall.order.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.common.exception.BusinessException;
import com.mall.common.result.Result;
import com.mall.order.dto.CreateOrderDTO;
import com.mall.order.entity.Order;
import com.mall.order.entity.OrderItem;
import com.mall.order.entity.Product;
import com.mall.order.entity.ProductSku;
import com.mall.order.feign.CouponServiceClient;
import com.mall.order.feign.ProductServiceClient;
import com.mall.order.mapper.OrderMapper;
import com.mall.order.mapper.OrderItemMapper;
import com.mall.order.mq.OrderCreateMessage;
import com.mall.order.mq.OrderMessageProducer;
import com.mall.order.service.OrderService;
import com.mall.order.service.StockRedisService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@Service
public class OrderServiceImpl implements OrderService {

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

    @Autowired(required = false)
    private OrderMessageProducer orderMessageProducer;

    @Override
    public Map<String, Object> getOrderStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("orderCount", orderMapper.selectCount(null));
        stats.put("pendingCount", orderMapper.selectCount(
                new LambdaQueryWrapper<Order>().eq(Order::getStatus, 0)));
        stats.put("paidCount", orderMapper.selectCount(
                new LambdaQueryWrapper<Order>().eq(Order::getStatus, 1)));
        stats.put("shippedCount", orderMapper.selectCount(
                new LambdaQueryWrapper<Order>().eq(Order::getStatus, 2)));
        stats.put("completedCount", orderMapper.selectCount(
                new LambdaQueryWrapper<Order>().eq(Order::getStatus, 3)));
        stats.put("cancelledCount", orderMapper.selectCount(
                new LambdaQueryWrapper<Order>().eq(Order::getStatus, 4)));

        List<Order> paidOrders = orderMapper.selectList(
                new LambdaQueryWrapper<Order>().in(Order::getStatus, 1, 2, 3));
        BigDecimal totalAmount = paidOrders.stream()
                .map(Order::getTotalAmount)
                .filter(a -> a != null)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        stats.put("totalAmount", totalAmount);
        return stats;
    }

    @Override
    public Page<Order> getOrderList(Long userId, Integer status, String orderNo, Integer pageNum, Integer pageSize) {
        Page<Order> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<Order> wrapper = new LambdaQueryWrapper<>();
        if (userId != null) {
            wrapper.eq(Order::getUserId, userId);
        }
        if (status != null) {
            wrapper.eq(Order::getStatus, status);
        }
        if (orderNo != null && !orderNo.isEmpty()) {
            wrapper.like(Order::getOrderNo, orderNo);
        }
        wrapper.orderByDesc(Order::getCreateTime);
        Page<Order> result = orderMapper.selectPage(page, wrapper);

        for (Order order : result.getRecords()) {
            List<OrderItem> items = getOrderItems(order.getId());
            order.setItems(items);
        }

        return result;
    }

    @Override
    public Order getOrderById(Long orderId) {
        Order order = orderMapper.selectById(orderId);
        if (order != null) {
            List<OrderItem> items = getOrderItems(order.getId());
            order.setItems(items);
        }
        return order;
    }

    @Override
    public Order getOrderByOrderNo(String orderNo) {
        LambdaQueryWrapper<Order> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Order::getOrderNo, orderNo);
        Order order = orderMapper.selectOne(wrapper);
        if (order != null) {
            List<OrderItem> items = getOrderItems(order.getId());
            order.setItems(items);
        }
        return order;
    }

    @Override
    public Map<String, Object> createOrder(CreateOrderDTO dto) {
        String orderNo = generateOrderNo();

        Map<Long, Integer> skuQuantityMap = new LinkedHashMap<>();
        for (CreateOrderDTO.OrderItemDTO itemDTO : dto.getItems()) {
            if (itemDTO.getSkuId() != null) {
                skuQuantityMap.merge(itemDTO.getSkuId(), itemDTO.getQuantity(), Integer::sum);
            }
        }

        List<Long> skuIds = new ArrayList<>(skuQuantityMap.keySet());
        List<Integer> quantities = new ArrayList<>(skuQuantityMap.values());

        if (orderMessageProducer == null) {
            return createOrderSync(dto, orderNo, skuIds, quantities);
        }

        boolean deducted = stockRedisService.deductStock(skuIds, quantities);
        if (!deducted) {
            throw new BusinessException("库存不足，请稍后重试");
        }

        OrderCreateMessage message = new OrderCreateMessage();
        message.setOrderNo(orderNo);
        message.setUserId(dto.getUserId());
        message.setReceiverName(dto.getReceiverName());
        message.setReceiverPhone(dto.getReceiverPhone());
        message.setReceiverAddress(dto.getReceiverAddress());
        message.setRemark(dto.getRemark());
        message.setCouponId(dto.getCouponId());
        message.setItems(new ArrayList<>());
        for (CreateOrderDTO.OrderItemDTO itemDTO : dto.getItems()) {
            OrderCreateMessage.OrderItemMessage itemMsg = new OrderCreateMessage.OrderItemMessage();
            itemMsg.setProductId(itemDTO.getProductId());
            itemMsg.setSkuId(itemDTO.getSkuId());
            itemMsg.setQuantity(itemDTO.getQuantity());
            message.getItems().add(itemMsg);
        }

        boolean sent = orderMessageProducer.sendOrderCreateMessage(message);
        if (!sent) {
            stockRedisService.addStock(skuIds, quantities);
            throw new BusinessException("系统繁忙，请稍后重试");
        }

        Map<String, Object> result = new HashMap<>();
        result.put("orderNo", orderNo);
        result.put("status", "processing");
        result.put("message", "订单正在处理中");

        log.info("订单提交成功，等待后台处理: orderNo={}", orderNo);
        return result;
    }

    private Map<String, Object> createOrderSync(CreateOrderDTO dto, String orderNo, List<Long> skuIds, List<Integer> quantities) {
        log.info("RocketMQ不可用，降级为同步创建订单: orderNo={}", orderNo);
        for (int i = 0; i < skuIds.size(); i++) {
            Result<Boolean> stockResult = productServiceClient.deductStock(skuIds.get(i), quantities.get(i));
            if (stockResult == null || !Boolean.TRUE.equals(stockResult.getData())) {
                for (int j = 0; j < i; j++) {
                    try { productServiceClient.addStock(skuIds.get(j), quantities.get(j)); } catch (Exception ignored) {}
                }
                throw new BusinessException("库存不足");
            }
        }

        Order order = new Order();
        order.setOrderNo(orderNo);
        order.setUserId(dto.getUserId());
        order.setStatus(0);
        order.setRemark(dto.getRemark());
        order.setReceiverName(dto.getReceiverName());
        order.setReceiverPhone(dto.getReceiverPhone());
        order.setReceiverAddress(dto.getReceiverAddress());

        BigDecimal totalAmount = BigDecimal.ZERO;
        List<OrderItem> orderItems = new ArrayList<>();
        for (CreateOrderDTO.OrderItemDTO itemDTO : dto.getItems()) {
            Result<Product> productResult = productServiceClient.getProductById(itemDTO.getProductId());
            Product product = productResult != null ? productResult.getData() : null;
            ProductSku sku = null;
            if (itemDTO.getSkuId() != null) {
                Result<ProductSku> skuResult = productServiceClient.getSkuById(itemDTO.getSkuId());
                sku = skuResult != null ? skuResult.getData() : null;
            }
            OrderItem item = new OrderItem();
            item.setProductId(itemDTO.getProductId());
            item.setSkuId(itemDTO.getSkuId());
            item.setQuantity(itemDTO.getQuantity());
            item.setPrice(sku != null && sku.getPrice() != null ? sku.getPrice() : product.getPrice());
            item.setTotalAmount(item.getPrice().multiply(BigDecimal.valueOf(itemDTO.getQuantity())));
            item.setProductName(product.getProductName());
            item.setSkuName(sku != null && sku.getSkuName() != null ? sku.getSkuName() : product.getProductName());
            item.setSkuCode(sku != null && sku.getSkuCode() != null ? sku.getSkuCode() : "SKU" + itemDTO.getSkuId());
            item.setProductImage(product.getMainImage());
            item.setOrderNo(orderNo);
            totalAmount = totalAmount.add(item.getTotalAmount());
            orderItems.add(item);

            productServiceClient.incrementSales(itemDTO.getProductId(), itemDTO.getQuantity());
        }

        order.setTotalAmount(totalAmount);
        if (dto.getCouponId() != null) {
            Result<BigDecimal> discountResult = couponServiceClient.calculateDiscount(dto.getCouponId(), totalAmount);
            BigDecimal discount = discountResult != null ? discountResult.getData() : BigDecimal.ZERO;
            order.setCouponId(dto.getCouponId());
            order.setDiscountAmount(discount != null ? discount : BigDecimal.ZERO);
            order.setPayAmount(totalAmount.subtract(order.getDiscountAmount()));
        } else {
            order.setPayAmount(totalAmount);
            order.setDiscountAmount(BigDecimal.ZERO);
        }
        if (order.getPayAmount().compareTo(BigDecimal.ZERO) < 0) {
            order.setPayAmount(BigDecimal.ZERO);
        }

        orderMapper.insert(order);
        for (OrderItem item : orderItems) {
            item.setOrderId(order.getId());
            orderItemMapper.insert(item);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("orderNo", orderNo);
        result.put("status", "created");
        result.put("orderId", order.getId());
        result.put("message", "订单创建成功");
        return result;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean payOrder(Long orderId) {
        Order order = orderMapper.selectById(orderId);
        if (order == null) {
            throw new BusinessException("订单不存在");
        }

        if (order.getStatus() != 0) {
            throw new BusinessException("订单状态不正确");
        }

        order.setStatus(1);
        order.setPaymentTime(LocalDateTime.now(ZoneId.of("Asia/Shanghai")));
        orderMapper.updateById(order);

        if (order.getCouponId() != null) {
            Result<Boolean> useResult = couponServiceClient.useCoupon(order.getCouponId(), orderId);
            if (useResult == null || !Boolean.TRUE.equals(useResult.getData())) {
                log.warn("优惠券使用失败, couponId={}, orderId={}", order.getCouponId(), orderId);
            }
        }

        log.info("订单支付成功: {}", order.getOrderNo());
        return true;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean shipOrder(Long orderId) {
        Order order = orderMapper.selectById(orderId);
        if (order == null) {
            throw new BusinessException("订单不存在");
        }

        if (order.getStatus() != 1) {
            throw new BusinessException("订单状态不正确，只能发货已支付的订单");
        }

        order.setStatus(2);
        order.setDeliveryTime(LocalDateTime.now(ZoneId.of("Asia/Shanghai")));
        orderMapper.updateById(order);

        log.info("订单发货成功: {}", order.getOrderNo());
        return true;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean cancelOrder(Long orderId) {
        Order order = orderMapper.selectById(orderId);
        if (order == null) {
            throw new BusinessException("订单不存在");
        }

        if (order.getStatus() != 0) {
            throw new BusinessException("只能取消待支付的订单");
        }

        LambdaUpdateWrapper<Order> updateWrapper = new LambdaUpdateWrapper<>();
        updateWrapper.eq(Order::getId, orderId)
                    .eq(Order::getStatus, 0)
                    .set(Order::getStatus, 4);

        int rows = orderMapper.update(null, updateWrapper);
        if (rows == 0) {
            throw new BusinessException("订单状态已变更，取消失败");
        }

        List<OrderItem> items = getOrderItems(orderId);
        for (OrderItem item : items) {
            boolean success = false;
            for (int i = 0; i < 3; i++) {
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

        log.info("订单取消成功: {}", order.getOrderNo());
        return true;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean confirmReceive(Long orderId) {
        Order order = orderMapper.selectById(orderId);
        if (order == null) {
            throw new BusinessException("订单不存在");
        }

        if (order.getStatus() != 2) {
            throw new BusinessException("订单状态不正确，只能确认收货已发货的订单");
        }

        order.setStatus(3);
        order.setReceiveTime(LocalDateTime.now(ZoneId.of("Asia/Shanghai")));
        orderMapper.updateById(order);

        log.info("订单确认收货成功: {}", order.getOrderNo());
        return true;
    }

    private List<OrderItem> getOrderItems(Long orderId) {
        LambdaQueryWrapper<OrderItem> itemWrapper = new LambdaQueryWrapper<>();
        itemWrapper.eq(OrderItem::getOrderId, orderId);
        return orderItemMapper.selectList(itemWrapper);
    }

    private String generateOrderNo() {
        String timestamp = LocalDateTime.now(ZoneId.of("Asia/Shanghai")).format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));
        String random = UUID.randomUUID().toString().substring(0, 6).toUpperCase();
        return "ORD" + timestamp + random;
    }
}
