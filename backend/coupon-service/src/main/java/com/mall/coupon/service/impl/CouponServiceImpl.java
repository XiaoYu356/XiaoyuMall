package com.mall.coupon.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.common.constant.RedisConstant;
import com.mall.common.exception.BusinessException;
import com.mall.coupon.entity.AvailableCouponVO;
import com.mall.coupon.entity.CouponTemplate;
import com.mall.coupon.entity.UserCoupon;
import com.mall.coupon.entity.UserCouponVO;
import com.mall.coupon.mapper.CouponTemplateMapper;
import com.mall.coupon.mapper.UserCouponMapper;
import com.mall.coupon.service.CouponService;
import com.mall.coupon.mq.CouponMessageProducer;
import com.mall.coupon.mq.CouponReceiveMessage;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Arrays;
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
    private StringRedisTemplate stringRedisTemplate;

    @Autowired
    private TransactionTemplate transactionTemplate;

    @Autowired(required = false)
    private CouponMessageProducer couponMessageProducer;

    /**
     * 优惠券秒杀演进版本开关: v0/v1/v2/v3，见application.yaml中coupon.receive.version
     */
    @Value("${coupon.receive.version:v3}")
    private String receiveVersion;

    private static final String RECEIVE_SCRIPT =
            "local stockKey = KEYS[1] " +
            "local userKey = KEYS[2] " +
            "local userId = ARGV[1] " +
            "if redis.call('sismember', userKey, userId) == 1 then " +
            "  return 2 " +
            "end " +
            "local stock = tonumber(redis.call('get', stockKey)) " +
            "if stock == nil then " +
            "  return -1 " +
            "end " +
            "if stock <= 0 then " +
            "  return 0 " +
            "end " +
            "redis.call('decr', stockKey) " +
            "redis.call('sadd', userKey, userId) " +
            "return 1";

    private static final String ROLLBACK_SCRIPT =
            "local stockKey = KEYS[1] " +
            "local userKey = KEYS[2] " +
            "local userId = ARGV[1] " +
            "redis.call('incr', stockKey) " +
            "redis.call('srem', userKey, userId) " +
            "return 1";

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
    public CouponTemplate createCouponTemplate(CouponTemplate template) {
        template.setUsedCount(0);
        template.setStatus(1);
        template.setPerLimit(1);
        couponTemplateMapper.insert(template);

        long remainStock = template.getTotalCount() - template.getUsedCount();
        String stockKey = RedisConstant.COUPON_STOCK_KEY + template.getId();
        stringRedisTemplate.opsForValue().set(stockKey, String.valueOf(remainStock));

        log.info("优惠券模板创建成功: {}, 剩余库存已同步到Redis: {}", template.getTemplateName(), remainStock);
        return template;
    }

    @Override
    public CouponTemplate updateCouponTemplate(CouponTemplate template) {
        CouponTemplate existing = couponTemplateMapper.selectById(template.getId());
        if (existing == null) {
            throw new BusinessException("优惠券不存在");
        }

        if (LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isAfter(existing.getStartTime())) {
            throw new BusinessException("优惠券已开始发行，无法编辑");
        }

        template.setPerLimit(1);
        couponTemplateMapper.updateById(template);

        CouponTemplate updated = couponTemplateMapper.selectById(template.getId());
        if (updated != null) {
            long remainStock = updated.getTotalCount() - updated.getUsedCount();
            String stockKey = RedisConstant.COUPON_STOCK_KEY + updated.getId();
            stringRedisTemplate.opsForValue().set(stockKey, String.valueOf(remainStock));
        }

        log.info("优惠券模板更新成功: {}", template.getId());
        return updated;
    }

    @Override
    public void deleteCouponTemplate(Long templateId) {
        CouponTemplate existing = couponTemplateMapper.selectById(templateId);
        if (existing == null) {
            throw new BusinessException("优惠券不存在");
        }

        if (LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isAfter(existing.getStartTime())) {
            throw new BusinessException("优惠券已开始发行，无法删除，请改为禁用");
        }

        couponTemplateMapper.deleteById(templateId);

        String stockKey = RedisConstant.COUPON_STOCK_KEY + templateId;
        String userKey = RedisConstant.USER_COUPON_KEY + templateId;
        stringRedisTemplate.delete(stockKey);
        stringRedisTemplate.delete(userKey);

        log.info("优惠券模板删除成功: {}", templateId);
    }

    @Override
    public UserCoupon receiveCoupon(Long userId, Long templateId) {
        CouponTemplate template = couponTemplateMapper.selectById(templateId);
        if (template == null) {
            throw new BusinessException("优惠券不存在");
        }
        if (template.getStatus() != 1) {
            throw new BusinessException("优惠券已禁用");
        }
        if (LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isBefore(template.getStartTime()) ||
            LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isAfter(template.getEndTime())) {
            throw new BusinessException("优惠券不在有效期内");
        }

        String stockKey = RedisConstant.COUPON_STOCK_KEY + templateId;
        String userKey = RedisConstant.USER_COUPON_KEY + templateId;

        DefaultRedisScript<Long> receiveScript = new DefaultRedisScript<>(RECEIVE_SCRIPT, Long.class);
        Long result = stringRedisTemplate.execute(
                receiveScript,
                Arrays.asList(stockKey, userKey),
                userId.toString()
        );

        if (result == null || result == 0) {
            throw new BusinessException("优惠券已领完");
        }
        if (result == 2) {
            throw new BusinessException("已达到领取上限");
        }
        if (result == -1) {
            syncSingleTemplateToRedis(template);
            result = stringRedisTemplate.execute(
                    receiveScript,
                    Arrays.asList(stockKey, userKey),
                    userId.toString()
            );
            if (result == null || result == 0) {
                throw new BusinessException("优惠券已领完");
            }
            if (result == 2) {
                throw new BusinessException("已达到领取上限");
            }
        }

        try {
            UserCoupon coupon = transactionTemplate.execute(status -> {
                UserCoupon userCoupon = new UserCoupon();
                userCoupon.setUserId(userId);
                userCoupon.setTemplateId(templateId);
                userCoupon.setCouponCode("CPN" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
                userCoupon.setStatus(0);
                userCoupon.setExpireTime(template.getEndTime());
                userCouponMapper.insert(userCoupon);

                int updated = couponTemplateMapper.incrementUsedCount(templateId);
                if (updated == 0) {
                    status.setRollbackOnly();
                    throw new BusinessException("优惠券已领完");
                }

                log.info("用户领取优惠券成功: userId={}, couponId={}", userId, userCoupon.getId());
                return userCoupon;
            });
            return coupon;
        } catch (BusinessException e) {
            rollbackRedis(templateId, userId);
            throw e;
        } catch (Exception e) {
            rollbackRedis(templateId, userId);
            log.error("领取优惠券异常: userId={}, templateId={}", userId, templateId, e);
            throw new BusinessException("领取优惠券失败，请重试");
        }
    }

    @Override
    public void receiveCouponAsync(Long userId, Long templateId) {
        if (couponMessageProducer == null) {
            log.info("RocketMQ不可用，降级为同步领取优惠券: userId={}, templateId={}", userId, templateId);
            receiveCoupon(userId, templateId);
            return;
        }

        CouponTemplate template = couponTemplateMapper.selectById(templateId);
        if (template == null) {
            throw new BusinessException("优惠券不存在");
        }
        if (template.getStatus() != 1) {
            throw new BusinessException("优惠券已禁用");
        }
        if (LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isBefore(template.getStartTime()) ||
            LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isAfter(template.getEndTime())) {
            throw new BusinessException("优惠券不在有效期内");
        }

        String stockKey = RedisConstant.COUPON_STOCK_KEY + templateId;
        String userKey = RedisConstant.USER_COUPON_KEY + templateId;

        DefaultRedisScript<Long> receiveScript = new DefaultRedisScript<>(RECEIVE_SCRIPT, Long.class);
        Long result = stringRedisTemplate.execute(
                receiveScript,
                Arrays.asList(stockKey, userKey),
                userId.toString()
        );

        if (result == null || result == 0) {
            throw new BusinessException("优惠券已领完");
        }
        if (result == 2) {
            throw new BusinessException("已达到领取上限");
        }
        if (result == -1) {
            syncSingleTemplateToRedis(template);
            result = stringRedisTemplate.execute(
                    receiveScript,
                    Arrays.asList(stockKey, userKey),
                    userId.toString()
            );
            if (result == null || result == 0) {
                throw new BusinessException("优惠券已领完");
            }
            if (result == 2) {
                throw new BusinessException("已达到领取上限");
            }
        }

        CouponReceiveMessage message = new CouponReceiveMessage();
        message.setUserId(userId);
        message.setTemplateId(templateId);

        boolean sent = couponMessageProducer.sendReceiveMessage(message);
        if (!sent) {
            rollbackRedis(templateId, userId);
            log.warn("RocketMQ消息发送失败，降级为同步领取优惠券: userId={}, templateId={}", userId, templateId);
            receiveCoupon(userId, templateId);
            return;
        }

        log.info("优惠券异步领取消息已发送: userId={}, templateId={}", userId, templateId);
    }

    @Override
    public Map<String, Object> receiveCouponByStrategy(Long userId, Long templateId) {
        return switch (receiveVersion) {
            case "v0" -> buildSyncResult(receiveCouponV0(userId, templateId));
            case "v1" -> buildSyncResult(receiveCouponV1(userId, templateId));
            case "v2" -> buildSyncResult(receiveCoupon(userId, templateId));
            default -> {
                receiveCouponAsync(userId, templateId);
                Map<String, Object> result = new HashMap<>();
                result.put("status", "processing");
                result.put("message", "领取请求已提交，正在处理中");
                yield result;
            }
        };
    }

    /**
     * V0基线版本：先查询再减少（存在并发缺陷，仅用于压测对比，不建议生产使用）
     * 缺陷1-超卖: 查库存与写回非原子，库存剩1张时多个并发请求都能通过检查；
     *             used_count基于旧值+1后全量updateById写回，并发下互相覆盖导致少加 → 实发数量超过totalCount
     * 缺陷2-重复领取: 查重与插入非原子，同一用户并发请求可同时通过selectCount检查
     *             （当前被user_coupon表的uk_user_template唯一索引兜底，但会抛DuplicateKeyException表现为500，而非友好提示）
     */
    private UserCoupon receiveCouponV0(Long userId, Long templateId) {
        CouponTemplate template = couponTemplateMapper.selectById(templateId);
        if (template == null) {
            throw new BusinessException("优惠券不存在");
        }
        if (template.getStatus() != 1) {
            throw new BusinessException("优惠券已禁用");
        }
        if (LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isBefore(template.getStartTime()) ||
            LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isAfter(template.getEndTime())) {
            throw new BusinessException("优惠券不在有效期内");
        }

        // 缺陷1：并发下多个线程同时读到剩余库存>0，都能通过检查
        if (template.getTotalCount() - template.getUsedCount() <= 0) {
            throw new BusinessException("优惠券已领完");
        }

        // 缺陷2：并发下同一用户的多个请求同时查到receivedCount=0，都能通过检查
        Long receivedCount = userCouponMapper.selectCount(
                new LambdaQueryWrapper<UserCoupon>()
                        .eq(UserCoupon::getUserId, userId)
                        .eq(UserCoupon::getTemplateId, templateId));
        if (receivedCount >= template.getPerLimit()) {
            throw new BusinessException("已达到领取上限");
        }

        UserCoupon userCoupon = new UserCoupon();
        userCoupon.setUserId(userId);
        userCoupon.setTemplateId(templateId);
        userCoupon.setCouponCode("CPN" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        userCoupon.setStatus(0);
        userCoupon.setExpireTime(template.getEndTime());
        userCouponMapper.insert(userCoupon);

        // 缺陷1体现：基于查询到的旧值+1后全量写回，并发下丢失更新
        template.setUsedCount(template.getUsedCount() + 1);
        couponTemplateMapper.updateById(template);

        log.info("[V0先查再减] 领取优惠券成功: userId={}, templateId={}", userId, templateId);
        return userCoupon;
    }

    /**
     * V1数据库原子扣减：条件更新防超卖 + 唯一索引防重复领取
     * 解决V0的并发缺陷，但所有请求仍打到数据库，行锁热点限制QPS上限
     */
    private UserCoupon receiveCouponV1(Long userId, Long templateId) {
        CouponTemplate template = couponTemplateMapper.selectById(templateId);
        if (template == null) {
            throw new BusinessException("优惠券不存在");
        }
        if (template.getStatus() != 1) {
            throw new BusinessException("优惠券已禁用");
        }
        if (LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isBefore(template.getStartTime()) ||
            LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isAfter(template.getEndTime())) {
            throw new BusinessException("优惠券不在有效期内");
        }

        UserCoupon userCoupon = new UserCoupon();
        userCoupon.setUserId(userId);
        userCoupon.setTemplateId(templateId);
        userCoupon.setCouponCode("CPN" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        userCoupon.setStatus(0);
        userCoupon.setExpireTime(template.getEndTime());

        try {
            return transactionTemplate.execute(status -> {
                // 撞uk_user_template唯一索引说明该用户已领过
                userCouponMapper.insert(userCoupon);
                // 条件更新原子防超卖: UPDATE ... SET used_count=used_count+1 WHERE used_count<total_count
                int updated = couponTemplateMapper.incrementUsedCount(templateId);
                if (updated == 0) {
                    status.setRollbackOnly();
                    throw new BusinessException("优惠券已领完");
                }
                return userCoupon;
            });
        } catch (DuplicateKeyException e) {
            throw new BusinessException("已领取过该优惠券");
        }
    }

    private Map<String, Object> buildSyncResult(UserCoupon userCoupon) {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "success");
        result.put("couponId", userCoupon.getId());
        result.put("couponCode", userCoupon.getCouponCode());
        result.put("message", "领取成功");
        return result;
    }

    private void syncSingleTemplateToRedis(CouponTemplate template) {
        String stockKey = RedisConstant.COUPON_STOCK_KEY + template.getId();
        long remainStock = template.getTotalCount() - template.getUsedCount();
        stringRedisTemplate.opsForValue().set(stockKey, String.valueOf(remainStock));

        String userKey = RedisConstant.USER_COUPON_KEY + template.getId();
        LambdaQueryWrapper<UserCoupon> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserCoupon::getTemplateId, template.getId())
               .in(UserCoupon::getStatus, 0, 1);
        List<UserCoupon> userCoupons = userCouponMapper.selectList(wrapper);
        stringRedisTemplate.delete(userKey);
        if (!userCoupons.isEmpty()) {
            String[] userIds = userCoupons.stream()
                    .map(uc -> uc.getUserId().toString())
                    .distinct()
                    .toArray(String[]::new);
            stringRedisTemplate.opsForSet().add(userKey, userIds);
        }
        log.info("单模板Redis数据补偿完成: templateId={}, stock={}, userRecords={}", template.getId(), remainStock, userCoupons.size());
    }

    private void rollbackRedis(Long templateId, Long userId) {
        try {
            String stockKey = RedisConstant.COUPON_STOCK_KEY + templateId;
            String userKey = RedisConstant.USER_COUPON_KEY + templateId;
            DefaultRedisScript<Long> rollbackScript = new DefaultRedisScript<>(ROLLBACK_SCRIPT, Long.class);
            stringRedisTemplate.execute(rollbackScript, Arrays.asList(stockKey, userKey), userId.toString());
        } catch (Exception ex) {
            log.error("回滚Redis失败: templateId={}, userId={}", templateId, userId, ex);
        }
    }

    @Override
    public BigDecimal calculateDiscount(Long couponId, BigDecimal orderAmount) {
        UserCoupon userCoupon = userCouponMapper.selectById(couponId);
        if (userCoupon == null || userCoupon.getStatus() != 0) {
            return BigDecimal.ZERO;
        }
        if (userCoupon.getExpireTime() != null && LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isAfter(userCoupon.getExpireTime())) {
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
        if (userCoupon.getExpireTime() != null && LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isAfter(userCoupon.getExpireTime())) {
            userCoupon.setStatus(2);
            userCouponMapper.updateById(userCoupon);
            throw new BusinessException("优惠券已过期");
        }

        int rows = userCouponMapper.useCouponCas(couponId, orderId);
        if (rows == 0) {
            throw new BusinessException("优惠券使用失败，可能已被其他订单使用");
        }

        log.info("优惠券使用成功: couponId={}, orderId={}", couponId, orderId);
        return true;
    }

    @Override
    public boolean returnCoupon(Long couponId, Long orderId) {
        UserCoupon userCoupon = userCouponMapper.selectById(couponId);
        if (userCoupon == null) {
            log.warn("退券失败：优惠券不存在 couponId={}", couponId);
            return false;
        }
        if (userCoupon.getStatus() != 1) {
            log.warn("退券失败：优惠券未使用 status={}, couponId={}", userCoupon.getStatus(), couponId);
            return false;
        }
        if (userCoupon.getOrderId() == null || !userCoupon.getOrderId().equals(orderId)) {
            log.warn("退券失败：订单不匹配 couponOrderId={}, requestOrderId={}, couponId={}",
                    userCoupon.getOrderId(), orderId, couponId);
            return false;
        }

        int rows = userCouponMapper.returnCouponCas(couponId, orderId);
        if (rows == 0) {
            log.warn("退券 CAS 失败（可能已被退回）: couponId={}, orderId={}", couponId, orderId);
            return false;
        }

        // 如果券已过 expire_time，退回后自然过期，状态改为 2
        if (userCoupon.getExpireTime() != null
                && LocalDateTime.now(ZoneId.of("Asia/Shanghai")).isAfter(userCoupon.getExpireTime())) {
            UserCoupon expired = new UserCoupon();
            expired.setId(couponId);
            expired.setStatus(2);
            userCouponMapper.updateById(expired);
            log.info("优惠券退回后已过期: couponId={}, orderId={}", couponId, orderId);
        } else {
            log.info("优惠券退回成功: couponId={}, orderId={}", couponId, orderId);
        }
        return true;
    }

    @Override
    public Page<UserCouponVO> getUserCouponList(Long userId, Integer status, Integer pageNum, Integer pageSize) {
        LambdaUpdateWrapper<UserCoupon> expireWrapper = new LambdaUpdateWrapper<>();
        expireWrapper.eq(UserCoupon::getUserId, userId)
                     .eq(UserCoupon::getStatus, 0)
                     .lt(UserCoupon::getExpireTime, LocalDateTime.now(ZoneId.of("Asia/Shanghai")))
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

    @Override
    public void syncCouponStockToRedis() {
        List<CouponTemplate> templates = couponTemplateMapper.selectList(
                new LambdaQueryWrapper<CouponTemplate>().eq(CouponTemplate::getStatus, 1)
        );
        for (CouponTemplate template : templates) {
            String stockKey = RedisConstant.COUPON_STOCK_KEY + template.getId();
            long remainStock = template.getTotalCount() - template.getUsedCount();
            stringRedisTemplate.opsForValue().set(stockKey, String.valueOf(remainStock));

            String userKey = RedisConstant.USER_COUPON_KEY + template.getId();
            LambdaQueryWrapper<UserCoupon> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(UserCoupon::getTemplateId, template.getId())
                   .in(UserCoupon::getStatus, 0, 1);
            List<UserCoupon> userCoupons = userCouponMapper.selectList(wrapper);
            stringRedisTemplate.delete(userKey);
            if (!userCoupons.isEmpty()) {
                String[] userIds = userCoupons.stream()
                        .map(uc -> uc.getUserId().toString())
                        .distinct()
                        .toArray(String[]::new);
                stringRedisTemplate.opsForSet().add(userKey, userIds);
            }
        }
        log.info("优惠券库存+用户领取记录同步到Redis完成, 共同步{}个模板", templates.size());
    }
}
