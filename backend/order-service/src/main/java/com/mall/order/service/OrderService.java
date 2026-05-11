package com.mall.order.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.order.dto.CreateOrderDTO;
import com.mall.order.entity.Order;

import java.util.Map;

public interface OrderService {

    Map<String, Object> getOrderStats();

    Page<Order> getOrderList(Long userId, Integer status, String orderNo, Integer pageNum, Integer pageSize);

    Order getOrderById(Long orderId);

    Order createOrder(CreateOrderDTO dto);

    boolean payOrder(Long orderId);

    boolean shipOrder(Long orderId);

    boolean cancelOrder(Long orderId);

    boolean confirmReceive(Long orderId);
}
