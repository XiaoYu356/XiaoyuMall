package com.mall.order.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.mall.common.exception.BusinessException;
import com.mall.common.result.Result;
import com.mall.order.dto.ApplyAftersaleDTO;
import com.mall.order.entity.AftersaleOrder;
import com.mall.order.entity.Order;
import com.mall.order.feign.CouponServiceClient;
import com.mall.order.mapper.AftersaleMapper;
import com.mall.order.mapper.OrderMapper;
import com.mall.order.service.AftersaleService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
public class AftersaleServiceImpl implements AftersaleService {

    private static final ZoneId ZONE = ZoneId.of("Asia/Shanghai");

    // 售后单状态
    private static final int ST_PENDING_AUDIT = 0;
    private static final int ST_APPROVED = 1;
    private static final int ST_RETURNING = 2;
    private static final int ST_WAREHOUSE_RECEIVED = 3;
    private static final int ST_REFUNDING = 4;
    private static final int ST_COMPLETED = 5;
    private static final int ST_REJECTED = 6;

    // 售后类型
    private static final int TYPE_REFUND_ONLY = 1;
    private static final int TYPE_RETURN_REFUND = 2;

    // 订单状态
    private static final int ORDER_REFUNDED = 5;

    /** 进行中的售后状态（不允许重复申请） */
    private static final List<Integer> ACTIVE_STATUS =
            List.of(0, 1, 2, 3, 4);

    /** 允许申请售后的订单状态：已支付/已发货/已完成 */
    private static final List<Integer> APPLIABLE_ORDER_STATUS = List.of(1, 2, 3);

    @Autowired
    private AftersaleMapper aftersaleMapper;

    @Autowired
    private OrderMapper orderMapper;

    @Autowired
    private CouponServiceClient couponServiceClient;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public AftersaleOrder apply(ApplyAftersaleDTO dto) {
        if (dto.getUserId() == null) {
            throw new BusinessException("无法确定当前用户");
        }
        if (dto.getType() != TYPE_REFUND_ONLY && dto.getType() != TYPE_RETURN_REFUND) {
            throw new BusinessException("暂仅支持仅退款与退货退款");
        }

        LambdaQueryWrapper<Order> orderWrapper = new LambdaQueryWrapper<>();
        orderWrapper.eq(Order::getOrderNo, dto.getOrderNo());
        Order order = orderMapper.selectOne(orderWrapper);
        if (order == null) {
            throw new BusinessException("订单不存在");
        }

        // 越权保护：order-service 直连场景下网关登录态不可用，
        // 以调用方传入的 userId 与订单归属做一致性校验
        if (!order.getUserId().equals(dto.getUserId())) {
            log.info("拦截越权售后申请 user={} orderNo={}", dto.getUserId(), dto.getOrderNo());
            throw new BusinessException("订单不存在");
        }

        if (!APPLIABLE_ORDER_STATUS.contains(order.getStatus())) {
            throw new BusinessException("当前订单状态不支持申请售后");
        }

        Long activeCount = aftersaleMapper.selectCount(
                new LambdaQueryWrapper<AftersaleOrder>()
                        .eq(AftersaleOrder::getOrderId, order.getId())
                        .in(AftersaleOrder::getStatus, ACTIVE_STATUS));
        if (activeCount > 0) {
            throw new BusinessException("该订单已有进行中的售后申请，请勿重复提交");
        }

        LocalDateTime now = LocalDateTime.now(ZONE);
        AftersaleOrder aftersale = new AftersaleOrder();
        aftersale.setAftersaleNo(generateAftersaleNo());
        aftersale.setOrderId(order.getId());
        aftersale.setOrderNo(order.getOrderNo());
        aftersale.setUserId(order.getUserId());
        aftersale.setType(dto.getType());
        aftersale.setReason(dto.getReason());
        aftersale.setDescription(dto.getDescription());
        // 退款金额按原订单实付金额计算
        aftersale.setRefundAmount(order.getPayAmount());
        aftersale.setStatus(ST_PENDING_AUDIT);
        aftersaleMapper.insert(aftersale);

        // 自动审核（学生项目：模拟平台规则自动通过；真实场景为人工/风控审核）
        aftersale.setStatus(ST_APPROVED);
        aftersale.setAuditTime(now);
        aftersale.setAuditRemark("系统自动审核通过");
        aftersaleMapper.updateById(aftersale);

        if (dto.getType() == TYPE_REFUND_ONLY) {
            // 仅退款：审核通过即模拟退款到账，订单联动置为已退款
            doRefund(aftersale, now);
            log.info("仅退款售后单完成: {}", aftersale.getAftersaleNo());
        } else {
            log.info("退货退款售后单已审核通过，等待用户寄回: {}", aftersale.getAftersaleNo());
        }
        return aftersale;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public AftersaleOrder completeRefund(Long aftersaleId, Long userId) {
        AftersaleOrder aftersale = requireOwned(aftersaleId, userId);

        if (aftersale.getStatus() == ST_COMPLETED) {
            return aftersale; // 幂等：重复通知不重复退款
        }
        if (aftersale.getStatus() != ST_APPROVED
                || aftersale.getType() != TYPE_RETURN_REFUND) {
            throw new BusinessException("当前售后单状态不支持该操作");
        }

        // 模拟物流与仓库作业的各状态节点（真实系统由快递轨迹/仓库系统驱动）
        LocalDateTime now = LocalDateTime.now(ZONE);
        aftersale.setStatus(ST_RETURNING);
        aftersaleMapper.updateById(aftersale);
        aftersale.setStatus(ST_WAREHOUSE_RECEIVED);
        aftersaleMapper.updateById(aftersale);
        aftersale.setStatus(ST_REFUNDING);
        aftersaleMapper.updateById(aftersale);

        doRefund(aftersale, now);
        log.info("退货退款售后单完成: {}", aftersale.getAftersaleNo());
        return aftersale;
    }

    /**
     * 执行退款落账：售后单置已完成、记录退款时间，原订单置已退款。
     * 退款通道与"模拟支付"同为可替换适配器，将来可替换为支付网关退款 API。
     * 同时退回已使用的优惠券（尽力而为：Feign 异常不阻塞退款主流程）。
     */
    private void doRefund(AftersaleOrder aftersale, LocalDateTime at) {
        aftersale.setStatus(ST_COMPLETED);
        aftersale.setRefundTime(at);
        aftersaleMapper.updateById(aftersale);

        // 先查出完整订单（包含 couponId），再更新状态 + 退券
        Order order = orderMapper.selectById(aftersale.getOrderId());
        Order update = new Order();
        update.setId(aftersale.getOrderId());
        update.setStatus(ORDER_REFUNDED);
        orderMapper.updateById(update);

        if (order != null && order.getCouponId() != null) {
            try {
                Result<Boolean> ret = couponServiceClient.returnCoupon(
                        order.getCouponId(), order.getId());
                if (ret != null && ret.getData() != null && ret.getData()) {
                    log.info("售后退款优惠券退回成功: aftersaleNo={}, couponId={}",
                            aftersale.getAftersaleNo(), order.getCouponId());
                } else {
                    log.warn("售后退款优惠券退回返回 false: aftersaleNo={}, couponId={}",
                            aftersale.getAftersaleNo(), order.getCouponId());
                }
            } catch (Exception e) {
                // 退券失败不阻塞退款主流程——优惠券服务异常时先保证退款到账，
                // 退券可通过定时补偿或人工处理
                log.error("售后退款优惠券退回异常（已忽略，需人工补偿）: aftersaleNo={}, couponId={}",
                        aftersale.getAftersaleNo(), order.getCouponId(), e);
            }
        }
    }

    @Override
    public AftersaleOrder getById(Long aftersaleId, Long userId) {
        return requireOwned(aftersaleId, userId);
    }

    @Override
    public List<AftersaleOrder> listByOrderNo(String orderNo, Long userId) {
        LambdaQueryWrapper<Order> orderWrapper = new LambdaQueryWrapper<>();
        orderWrapper.eq(Order::getOrderNo, orderNo);
        Order order = orderMapper.selectOne(orderWrapper);
        if (order == null || !order.getUserId().equals(userId)) {
            throw new BusinessException("订单不存在");
        }
        return aftersaleMapper.selectList(
                new LambdaQueryWrapper<AftersaleOrder>()
                        .eq(AftersaleOrder::getOrderId, order.getId())
                        .orderByDesc(AftersaleOrder::getCreateTime));
    }

    @Override
    public List<AftersaleOrder> listMy(Long userId) {
        return aftersaleMapper.selectList(
                new LambdaQueryWrapper<AftersaleOrder>()
                        .eq(AftersaleOrder::getUserId, userId)
                        .orderByDesc(AftersaleOrder::getCreateTime));
    }

    private AftersaleOrder requireOwned(Long aftersaleId, Long userId) {
        AftersaleOrder aftersale = aftersaleMapper.selectById(aftersaleId);
        if (aftersale == null || !aftersale.getUserId().equals(userId)) {
            throw new BusinessException("售后单不存在");
        }
        return aftersale;
    }

    private String generateAftersaleNo() {
        String timestamp = LocalDateTime.now(ZONE)
                .format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));
        String random = UUID.randomUUID().toString().substring(0, 6).toUpperCase();
        return "RMA" + timestamp + random;
    }
}
