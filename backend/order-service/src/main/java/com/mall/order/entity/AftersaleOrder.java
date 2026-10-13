package com.mall.order.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("aftersale_order")
public class AftersaleOrder {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String aftersaleNo;

    private Long orderId;

    private String orderNo;

    private Long userId;

    /**
     * 类型:1-仅退款,2-退货退款,3-换货
     */
    private Integer type;

    private String reason;

    private String description;

    /**
     * 状态:0-待审核,1-审核通过(待寄回),2-退货中,3-仓库已签收,4-退款中,5-已完成,6-已驳回
     */
    private Integer status;

    private BigDecimal refundAmount;

    private String auditRemark;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "Asia/Shanghai")
    private LocalDateTime auditTime;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "Asia/Shanghai")
    private LocalDateTime refundTime;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "Asia/Shanghai")
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "Asia/Shanghai")
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
