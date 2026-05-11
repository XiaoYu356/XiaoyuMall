package com.mall.order.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
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
import com.mall.order.service.OrderService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

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
    @Transactional(rollbackFor = Exception.class)
    public Order createOrder(CreateOrderDTO dto) {
        Order order = new Order();
        order.setOrderNo(generateOrderNo());
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
            if (product == null) {
                throw new BusinessException("商品不存在, productId=" + itemDTO.getProductId());
            }

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
            item.setOrderNo(order.getOrderNo());

            totalAmount = totalAmount.add(item.getTotalAmount());
            orderItems.add(item);

            Result<Boolean> stockResult = productServiceClient.deductStock(itemDTO.getSkuId(), itemDTO.getQuantity());
            if (stockResult == null || !Boolean.TRUE.equals(stockResult.getData())) {
                throw new BusinessException("库存扣减失败, skuId=" + itemDTO.getSkuId());
            }
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

        log.info("订单创建成功: {}", order.getOrderNo());
        return order;
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
        order.setPaymentTime(LocalDateTime.now());
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
        order.setDeliveryTime(LocalDateTime.now());
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

        order.setStatus(4);
        orderMapper.updateById(order);

        List<OrderItem> items = getOrderItems(orderId);
        for (OrderItem item : items) {
            try {
                productServiceClient.addStock(item.getSkuId(), item.getQuantity());
            } catch (Exception e) {
                log.error("库存回滚失败, skuId={}, quantity={}", item.getSkuId(), item.getQuantity(), e);
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
        order.setReceiveTime(LocalDateTime.now());
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
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));
        String random = UUID.randomUUID().toString().substring(0, 6).toUpperCase();
        return "ORD" + timestamp + random;
    }
}
