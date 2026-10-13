package com.mall.order.controller;

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

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/orders")
@Tag(name = "订单管理", description = "订单创建、支付、发货等接口")
public class OrderController {

    @Autowired
    private OrderService orderService;

    @GetMapping("/stats")
    @Operation(summary = "订单统计")
    public Result<Map<String, Object>> getOrderStats() {
        try {
            Map<String, Object> stats = orderService.getOrderStats();
            return Result.success(stats);
        } catch (Exception e) {
            log.error("订单统计异常 DEBUG", e);
            return Result.failed("DEBUG: " + e.getClass().getSimpleName() + " - " + e.getMessage());
        }
    }

    @GetMapping
    @Operation(summary = "订单列表")
    public Result<Page<Order>> getOrderList(
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) String orderNo,
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize) {
        // 归属防护：登录用户强制只看自己的订单，忽略伪造的 userId 参数；
        // 无登录态（内部服务间调用）需显式传 userId
        Long effectiveUserId = userId;
        if (StpUtil.isLogin()) {
            effectiveUserId = StpUtil.getLoginIdAsLong();
        }
        if (effectiveUserId == null) {
            return Result.failed("缺少用户标识");
        }
        Page<Order> page = orderService.getOrderList(effectiveUserId, status, orderNo, pageNum, pageSize);
        return Result.success(page);
    }

    @GetMapping("/{orderId}")
    @Operation(summary = "订单详情")
    public Result<Order> getOrderById(@PathVariable Long orderId) {
        Order order = orderService.getOrderById(orderId);
        if (order == null || !order.getUserId().equals(StpUtil.getLoginIdAsLong())) {
            return Result.failed("订单不存在");
        }
        return Result.success(order);
    }

    @GetMapping("/no/{orderNo}")
    @Operation(summary = "根据订单号查询")
    public Result<Order> getOrderByOrderNo(@PathVariable String orderNo,
                                           @RequestParam(required = false) Long userId) {
        // 登录态优先（C 端）；无登录态时按调用方声明的 userId 校验归属（AI 服务内部调用）
        Long checkUserId = userId;
        if (StpUtil.isLogin()) {
            checkUserId = StpUtil.getLoginIdAsLong();
        }
        if (checkUserId == null) {
            return Result.failed("缺少用户标识");
        }
        Order order = orderService.getOrderByOrderNo(orderNo);
        if (order == null || !order.getUserId().equals(checkUserId)) {
            return Result.failed("订单不存在");
        }
        return Result.success(order);
    }

    @GetMapping("/no/{orderNo}/logistics")
    @Operation(summary = "查询订单物流轨迹")
    public Result<List<Map<String, Object>>> getLogisticsTimeline(
            @PathVariable String orderNo,
            @RequestParam Long userId) {
        return Result.success(orderService.getLogisticsTimeline(orderNo, userId));
    }

    @PostMapping
    @Operation(summary = "创建订单")
    public Result<Map<String, Object>> createOrder(@Valid @RequestBody CreateOrderDTO dto) {
        dto.setUserId(StpUtil.getLoginIdAsLong());
        Map<String, Object> result = orderService.createOrder(dto);
        return Result.success(result);
    }

    @PostMapping("/{orderId}/pay")
    @Operation(summary = "支付订单")
    public Result<Boolean> payOrder(@PathVariable Long orderId) {
        boolean result = orderService.payOrder(orderId, StpUtil.getLoginIdAsLong());
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
        boolean result = orderService.cancelOrder(orderId, StpUtil.getLoginIdAsLong());
        return Result.success(result);
    }

    @PostMapping("/{orderId}/receive")
    @Operation(summary = "确认收货")
    public Result<Boolean> confirmReceive(@PathVariable Long orderId) {
        boolean result = orderService.confirmReceive(orderId, StpUtil.getLoginIdAsLong());
        return Result.success(result);
    }
}
