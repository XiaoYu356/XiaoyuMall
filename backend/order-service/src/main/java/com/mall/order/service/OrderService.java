package com.mall.order.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.order.dto.CreateOrderDTO;
import com.mall.order.entity.Order;

import java.util.List;
import java.util.Map;

public interface OrderService {

    Map<String, Object> getOrderStats();

    Page<Order> getOrderList(Long userId, Integer status, String orderNo, Integer pageNum, Integer pageSize);

    Order getOrderById(Long orderId);

    Order getOrderByOrderNo(String orderNo);

    Map<String, Object> createOrder(CreateOrderDTO dto);

    boolean payOrder(Long orderId, Long userId);

    boolean shipOrder(Long orderId);

    boolean cancelOrder(Long orderId, Long userId);

    boolean confirmReceive(Long orderId, Long userId);

    /**
     * 物流轨迹：真实节点取自订单事件（支付/发货/签收），
     * 运输中节点按发货时间推导，数据源将来可替换为快递鸟/菜鸟接口。
     */
    List<Map<String, Object>> getLogisticsTimeline(String orderNo, Long userId);
}
