package com.mall.order.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.common.result.Result;
import com.mall.order.entity.Order;
import com.mall.order.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * 管理端订单接口：不做用户归属过滤，通过权限码控制访问。
 * C 端订单接口见 OrderController。
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/admin/orders")
@Tag(name = "管理端-订单管理", description = "管理端订单查询、取消等接口")
public class AdminOrderController {

    @Autowired
    private OrderService orderService;

    @GetMapping
    @Operation(summary = "订单列表（全部用户）")
    @SaCheckPermission("order:view")
    public Result<Page<Order>> getOrderList(
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) String orderNo,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        // userId 仅作为可选筛选条件；不传则查询全部用户的订单
        Page<Order> page = orderService.getOrderList(userId, status, orderNo, pageNum, pageSize);
        return Result.success(page);
    }

    @GetMapping("/{orderId}")
    @Operation(summary = "订单详情（不限归属）")
    @SaCheckPermission("order:view")
    public Result<Order> getOrderById(@PathVariable Long orderId) {
        Order order = orderService.getOrderById(orderId);
        if (order == null) {
            return Result.failed("订单不存在");
        }
        return Result.success(order);
    }

    @PostMapping("/{orderId}/cancel")
    @Operation(summary = "取消订单（管理员）")
    @SaCheckPermission("order:cancel")
    public Result<Boolean> cancelOrder(@PathVariable Long orderId) {
        // 复用 C 端取消逻辑：以订单真实归属人身份通过 service 层校验
        Order order = orderService.getOrderById(orderId);
        if (order == null) {
            return Result.failed("订单不存在");
        }
        boolean result = orderService.cancelOrder(orderId, order.getUserId());
        return Result.success(result);
    }
}
