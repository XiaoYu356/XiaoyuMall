package com.mall.coupon.entity;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
public class AvailableCouponVO {
    private Long id;
    private String templateName;
    private Integer couponType;
    private BigDecimal couponValue;
    private BigDecimal minAmount;
    private Integer totalCount;
    private Integer usedCount;
    private Integer perLimit;
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "Asia/Shanghai")
    private LocalDateTime startTime;
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "Asia/Shanghai")
    private LocalDateTime endTime;
    private Integer status;
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "Asia/Shanghai")
    private LocalDateTime createTime;

    private Integer userReceivedCount;
}
