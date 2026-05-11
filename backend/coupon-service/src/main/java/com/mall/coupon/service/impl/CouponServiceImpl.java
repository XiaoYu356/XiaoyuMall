package com.mall.coupon.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.common.exception.BusinessException;
import com.mall.coupon.entity.AvailableCouponVO;
import com.mall.coupon.entity.CouponTemplate;
import com.mall.coupon.entity.UserCoupon;
import com.mall.coupon.entity.UserCouponVO;
import com.mall.coupon.mapper.CouponTemplateMapper;
import com.mall.coupon.mapper.UserCouponMapper;
import com.mall.coupon.service.CouponService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

@Slf4j
@Service
public class CouponServiceImpl implements CouponService {

    @Autowired
    private CouponTemplateMapper couponTemplateMapper;

    @Autowired
    private UserCouponMapper userCouponMapper;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Override
    public Map<String, Object> getCouponStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("templateCount", couponTemplateMapper.selectCount(null));
        stats.put("receivedCount", userCouponMapper.selectCount(null));
        stats.put("usedCount", userCouponMapper.selectCount(
                new LambdaQueryWrapper<UserCoupon>().eq(UserCoupon::getStatus, 1)));
        stats.put("unusedCount", userCouponMapper.selectCount(
                new LambdaQueryWrapper<UserCoupon>().eq(UserCoupon::getStatus, 0)));
        return stats;
    }

    @Override
    public Page<CouponTemplate> getCouponTemplateList(Integer pageNum, Integer pageSize) {
        Page<CouponTemplate> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<CouponTemplate> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(CouponTemplate::getStatus, 1)
               .orderByDesc(CouponTemplate::getCreateTime);
        return couponTemplateMapper.selectPage(page, wrapper);
    }

    @Override
    public Page<AvailableCouponVO> getAvailableCouponList(Long userId, Integer pageNum, Integer pageSize) {
        Page<CouponTemplate> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<CouponTemplate> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(CouponTemplate::getStatus, 1)
               .orderByDesc(CouponTemplate::getCreateTime);
        Page<CouponTemplate> templatePage = couponTemplateMapper.selectPage(page, wrapper);

        Page<AvailableCouponVO> voPage = new Page<>(pageNum, pageSize, templatePage.getTotal());
        if (templatePage.getRecords().isEmpty()) {
            voPage.setRecords(new ArrayList<>());
            return voPage;
        }

        List<Long> templateIds = templatePage.getRecords().stream()
                .map(CouponTemplate::getId)
                .collect(Collectors.toList());

        Map<Long, Long> receivedCountMap = null;
        if (userId != null) {
            LambdaQueryWrapper<UserCoupon> ucWrapper = new LambdaQueryWrapper<>();
            ucWrapper.eq(UserCoupon::getUserId, userId)
                     .in(UserCoupon::getTemplateId, templateIds);
            List<UserCoupon> userCoupons = userCouponMapper.selectList(ucWrapper);
            receivedCountMap = userCoupons.stream()
                    .collect(Collectors.groupingBy(UserCoupon::getTemplateId, Collectors.counting()));
        }

        Map<Long, Long> finalReceivedCountMap = receivedCountMap;
        List<AvailableCouponVO> voList = templatePage.getRecords().stream().map(t -> {
            AvailableCouponVO vo = new AvailableCouponVO();
            vo.setId(t.getId());
            vo.setTemplateName(t.getTemplateName());
            vo.setCouponType(t.getCouponType());
            vo.setCouponValue(t.getCouponValue());
            vo.setMinAmount(t.getMinAmount());
            vo.setTotalCount(t.getTotalCount());
            vo.setUsedCount(t.getUsedCount());
            vo.setPerLimit(t.getPerLimit());
            vo.setStartTime(t.getStartTime());
            vo.setEndTime(t.getEndTime());
            vo.setStatus(t.getStatus());
            vo.setCreateTime(t.getCreateTime());
            vo.setUserReceivedCount(finalReceivedCountMap != null ? finalReceivedCountMap.getOrDefault(t.getId(), 0L).intValue() : 0);
            return vo;
        }).collect(Collectors.toList());

        voPage.setRecords(voList);
        return voPage;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CouponTemplate createCouponTemplate(CouponTemplate template) {
        template.setUsedCount(0);
        template.setStatus(1);
        couponTemplateMapper.insert(template);
        log.info("优惠券模板创建成功: {}", template.getTemplateName());
        return template;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public CouponTemplate updateCouponTemplate(CouponTemplate template) {
        couponTemplateMapper.updateById(template);
        log.info("优惠券模板更新成功: {}", template.getId());
        return template;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteCouponTemplate(Long templateId) {
        LambdaQueryWrapper<UserCoupon> ucWrapper = new LambdaQueryWrapper<>();
        ucWrapper.eq(UserCoupon::getTemplateId, templateId);
        Long receivedCount = userCouponMapper.selectCount(ucWrapper);
        if (receivedCount > 0) {
            throw new BusinessException("该优惠券已被用户领取，无法删除，请改为禁用");
        }
        couponTemplateMapper.deleteById(templateId);
        log.info("优惠券模板删除成功: {}", templateId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserCoupon receiveCoupon(Long userId, Long templateId) {
        CouponTemplate template = couponTemplateMapper.selectById(templateId);
        if (template == null) {
            throw new BusinessException("优惠券不存在");
        }

        if (template.getStatus() != 1) {
            throw new BusinessException("优惠券已禁用");
        }

        if (template.getUsedCount() >= template.getTotalCount()) {
            throw new BusinessException("优惠券已领完");
        }

        if (LocalDateTime.now().isBefore(template.getStartTime()) ||
            LocalDateTime.now().isAfter(template.getEndTime())) {
            throw new BusinessException("优惠券不在有效期内");
        }

        LambdaQueryWrapper<UserCoupon> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserCoupon::getUserId, userId)
               .eq(UserCoupon::getTemplateId, templateId);
        Long count = userCouponMapper.selectCount(wrapper);
        if (count >= template.getPerLimit()) {
            throw new BusinessException("已达到领取上限");
        }

        UserCoupon userCoupon = new UserCoupon();
        userCoupon.setUserId(userId);
        userCoupon.setTemplateId(templateId);
        userCoupon.setCouponCode("CPN" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        userCoupon.setStatus(0);
        userCoupon.setExpireTime(template.getEndTime());
        userCouponMapper.insert(userCoupon);

        template.setUsedCount(template.getUsedCount() + 1);
        couponTemplateMapper.updateById(template);

        log.info("用户领取优惠券成功: userId={}, couponId={}", userId, userCoupon.getId());
        return userCoupon;
    }

    @Override
    public BigDecimal calculateDiscount(Long couponId, BigDecimal orderAmount) {
        UserCoupon userCoupon = userCouponMapper.selectById(couponId);
        if (userCoupon == null || userCoupon.getStatus() != 0) {
            return BigDecimal.ZERO;
        }
        if (userCoupon.getExpireTime() != null && LocalDateTime.now().isAfter(userCoupon.getExpireTime())) {
            userCoupon.setStatus(2);
            userCouponMapper.updateById(userCoupon);
            return BigDecimal.ZERO;
        }

        CouponTemplate template = couponTemplateMapper.selectById(userCoupon.getTemplateId());
        if (template == null) {
            return BigDecimal.ZERO;
        }

        if (orderAmount.compareTo(template.getMinAmount()) < 0) {
            return BigDecimal.ZERO;
        }

        BigDecimal discount;
        switch (template.getCouponType()) {
            case 1:
                discount = template.getCouponValue();
                break;
            case 2:
                discount = orderAmount.multiply(
                    BigDecimal.ONE.subtract(template.getCouponValue().divide(BigDecimal.TEN, 2, RoundingMode.HALF_UP))
                );
                break;
            case 3:
                discount = template.getCouponValue();
                break;
            default:
                discount = BigDecimal.ZERO;
        }

        if (discount.compareTo(orderAmount) > 0) {
            discount = orderAmount;
        }

        return discount.setScale(2, RoundingMode.HALF_UP);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean useCoupon(Long couponId, Long orderId) {
        UserCoupon userCoupon = userCouponMapper.selectById(couponId);
        if (userCoupon == null) {
            throw new BusinessException("优惠券不存在");
        }

        if (userCoupon.getStatus() == 1) {
            throw new BusinessException("优惠券已使用");
        }
        if (userCoupon.getStatus() == 2) {
            throw new BusinessException("优惠券已过期");
        }
        if (userCoupon.getExpireTime() != null && LocalDateTime.now().isAfter(userCoupon.getExpireTime())) {
            userCoupon.setStatus(2);
            userCouponMapper.updateById(userCoupon);
            throw new BusinessException("优惠券已过期");
        }

        userCoupon.setStatus(1);
        userCoupon.setOrderId(orderId);
        userCoupon.setUseTime(LocalDateTime.now());
        userCouponMapper.updateById(userCoupon);

        log.info("优惠券使用成功: couponId={}, orderId={}", couponId, orderId);
        return true;
    }

    @Override
    public Page<UserCouponVO> getUserCouponList(Long userId, Integer status, Integer pageNum, Integer pageSize) {
        LambdaUpdateWrapper<UserCoupon> expireWrapper = new LambdaUpdateWrapper<>();
        expireWrapper.eq(UserCoupon::getUserId, userId)
                     .eq(UserCoupon::getStatus, 0)
                     .lt(UserCoupon::getExpireTime, LocalDateTime.now())
                     .set(UserCoupon::getStatus, 2);
        userCouponMapper.update(null, expireWrapper);

        Page<UserCoupon> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<UserCoupon> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserCoupon::getUserId, userId);
        if (status != null) {
            wrapper.eq(UserCoupon::getStatus, status);
        }
        wrapper.orderByDesc(UserCoupon::getCreateTime);
        Page<UserCoupon> userCouponPage = userCouponMapper.selectPage(page, wrapper);

        Page<UserCouponVO> voPage = new Page<>(pageNum, pageSize, userCouponPage.getTotal());
        if (userCouponPage.getRecords().isEmpty()) {
            voPage.setRecords(java.util.Collections.emptyList());
            return voPage;
        }

        java.util.List<Long> templateIds = userCouponPage.getRecords().stream()
                .map(UserCoupon::getTemplateId)
                .distinct()
                .collect(Collectors.toList());
        Map<Long, CouponTemplate> templateMap = couponTemplateMapper.selectBatchIds(templateIds)
                .stream()
                .collect(Collectors.toMap(CouponTemplate::getId, Function.identity()));

        java.util.List<UserCouponVO> voList = userCouponPage.getRecords().stream().map(uc -> {
            UserCouponVO vo = new UserCouponVO();
            vo.setId(uc.getId());
            vo.setUserId(uc.getUserId());
            vo.setTemplateId(uc.getTemplateId());
            vo.setCouponCode(uc.getCouponCode());
            vo.setStatus(uc.getStatus());
            vo.setOrderId(uc.getOrderId());
            vo.setUseTime(uc.getUseTime());
            vo.setExpireTime(uc.getExpireTime());
            vo.setCreateTime(uc.getCreateTime());

            CouponTemplate template = templateMap.get(uc.getTemplateId());
            if (template != null) {
                vo.setTemplateName(template.getTemplateName());
                vo.setCouponType(template.getCouponType());
                vo.setCouponValue(template.getCouponValue());
                vo.setMinAmount(template.getMinAmount());
            }
            return vo;
        }).collect(Collectors.toList());

        voPage.setRecords(voList);
        return voPage;
    }
}
