package com.mall.order.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ApplyAftersaleDTO {

    /**
     * 由调用方（网关登录态 / ai-service 注入）设置，不由前端信任传入
     */
    private Long userId;

    @NotBlank(message = "订单号不能为空")
    private String orderNo;

    @NotNull(message = "售后类型不能为空")
    private Integer type;

    @NotBlank(message = "申请原因不能为空")
    private String reason;

    private String description;
}
