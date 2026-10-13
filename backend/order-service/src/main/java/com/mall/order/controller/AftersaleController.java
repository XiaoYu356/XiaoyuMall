package com.mall.order.controller;

import com.mall.common.result.Result;
import com.mall.order.dto.ApplyAftersaleDTO;
import com.mall.order.entity.AftersaleOrder;
import com.mall.order.service.AftersaleService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 售后接口。
 * 鉴权模式与订单列表一致：调用方显式传入 userId（网关场景由登录态转换，
 * ai-service 场景由运行时注入），Service 层以订单/售后单归属做越权校验。
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/aftersale")
@Tag(name = "售后服务", description = "退款/退货申请与进度查询")
public class AftersaleController {

    @Autowired
    private AftersaleService aftersaleService;

    @PostMapping("/apply")
    @Operation(summary = "提交售后申请")
    public Result<AftersaleOrder> apply(
            @RequestParam Long userId,
            @Valid @RequestBody ApplyAftersaleDTO dto) {
        dto.setUserId(userId);
        return Result.success(aftersaleService.apply(dto));
    }

    @PostMapping("/{aftersaleId}/refund")
    @Operation(summary = "模拟退货寄回后的签收退款")
    public Result<AftersaleOrder> completeRefund(
            @RequestParam Long userId,
            @PathVariable Long aftersaleId) {
        return Result.success(aftersaleService.completeRefund(aftersaleId, userId));
    }

    @GetMapping("/{aftersaleId}")
    @Operation(summary = "查询售后单详情")
    public Result<AftersaleOrder> getById(
            @RequestParam Long userId,
            @PathVariable Long aftersaleId) {
        return Result.success(aftersaleService.getById(aftersaleId, userId));
    }

    @GetMapping("/order/{orderNo}")
    @Operation(summary = "查询某订单的售后记录")
    public Result<List<AftersaleOrder>> listByOrder(
            @RequestParam Long userId,
            @PathVariable String orderNo) {
        return Result.success(aftersaleService.listByOrderNo(orderNo, userId));
    }

    @GetMapping("/my")
    @Operation(summary = "查询我的售后单")
    public Result<List<AftersaleOrder>> listMy(@RequestParam Long userId) {
        return Result.success(aftersaleService.listMy(userId));
    }
}
