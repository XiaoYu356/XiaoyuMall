package com.mall.order.service;

import com.mall.order.dto.ApplyAftersaleDTO;
import com.mall.order.entity.AftersaleOrder;

import java.util.List;

public interface AftersaleService {

    /**
     * 提交售后申请。平台自动审核（学生项目简化）：
     * - 仅退款：审核通过后自动退款，售后单直达已完成，订单状态变已退款
     * - 退货退款：审核通过后停在待寄回，等待 completeRefund 模拟签收退款
     */
    AftersaleOrder apply(ApplyAftersaleDTO dto);

    /**
     * 模拟退货退款的后续全流程：用户寄回 → 仓库签收 → 退款到账。
     */
    AftersaleOrder completeRefund(Long aftersaleId, Long userId);

    AftersaleOrder getById(Long aftersaleId, Long userId);

    List<AftersaleOrder> listByOrderNo(String orderNo, Long userId);

    List<AftersaleOrder> listMy(Long userId);
}
