package com.mall.order.controller;

import cn.dev33.satoken.annotation.SaCheckLogin;
import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.common.result.Result;
import com.mall.order.dto.CreateOrderDTO;
import com.mall.order.entity.Order;
import com.mall.order.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/orders")
@SaCheckLogin
@Tag(name = "订单管理", description = "订单创建、支付、发货等接口")
public class OrderController {

    @Autowired
    private OrderService orderService;

    @GetMapping("/stats")
    @Operation(summary = "订单统计")
    public Result<Map<String, Object>> getOrderStats() {
        Map<String, Object> stats = orderService.getOrderStats();
        return Result.success(stats);
    }

    @GetMapping
    @Operation(summary = "订单列表")
    public Result<Page<Order>> getOrderList(
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) String orderNo,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        Page<Order> page = orderService.getOrderList(userId, status, orderNo, pageNum, pageSize);
        return Result.success(page);
    }

    @GetMapping("/{orderId}")
    @Operation(summary = "订单详情")
    public Result<Order> getOrderById(@PathVariable Long orderId) {
        Order order = orderService.getOrderById(orderId);
        return Result.success(order);
    }

    @PostMapping
    @Operation(summary = "创建订单")
    public Result<Order> createOrder(@Valid @RequestBody CreateOrderDTO dto) {
        dto.setUserId(StpUtil.getLoginIdAsLong());
        Order order = orderService.createOrder(dto);
        return Result.success(order);
    }

    @PostMapping("/{orderId}/pay")
    @Operation(summary = "支付订单")
    public Result<Boolean> payOrder(@PathVariable Long orderId) {
        boolean result = orderService.payOrder(orderId);
        return Result.success(result);
    }

    @PostMapping("/{orderId}/ship")
    @Operation(summary = "订单发货")
    @SaCheckPermission("order:ship")
    public Result<Boolean> shipOrder(@PathVariable Long orderId) {
        boolean result = orderService.shipOrder(orderId);
        return Result.success(result);
    }

    @PostMapping("/{orderId}/cancel")
    @Operation(summary = "取消订单")
    public Result<Boolean> cancelOrder(@PathVariable Long orderId) {
        boolean result = orderService.cancelOrder(orderId);
        return Result.success(result);
    }

    @PostMapping("/{orderId}/receive")
    @Operation(summary = "确认收货")
    public Result<Boolean> confirmReceive(@PathVariable Long orderId) {
        boolean result = orderService.confirmReceive(orderId);
        return Result.success(result);
    }
}
