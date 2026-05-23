package com.mall.order.service;

import com.mall.common.constant.RedisConstant;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Slf4j
@Service
public class StockRedisService {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    private static final String DEDUCT_STOCK_LUA =
            "for i = 1, #KEYS do\n" +
            "    local stock = tonumber(redis.call('GET', KEYS[i]))\n" +
            "    if stock == nil or stock < tonumber(ARGV[i]) then\n" +
            "        return i - 1\n" +
            "    end\n" +
            "end\n" +
            "for i = 1, #KEYS do\n" +
            "    redis.call('DECRBY', KEYS[i], tonumber(ARGV[i]))\n" +
            "end\n" +
            "return #KEYS";

    private static final String ADD_STOCK_LUA =
            "for i = 1, #KEYS do\n" +
            "    redis.call('INCRBY', KEYS[i], tonumber(ARGV[i]))\n" +
            "end\n" +
            "return #KEYS";

    public boolean deductStock(List<Long> skuIds, List<Integer> quantities) {
        if (skuIds.size() != quantities.size() || skuIds.isEmpty()) {
            return false;
        }

        List<String> keys = new ArrayList<>();
        List<String> args = new ArrayList<>();
        for (int i = 0; i < skuIds.size(); i++) {
            keys.add(RedisConstant.PRODUCT_STOCK_KEY + skuIds.get(i));
            args.add(String.valueOf(quantities.get(i)));
        }

        DefaultRedisScript<Long> script = new DefaultRedisScript<>(DEDUCT_STOCK_LUA, Long.class);
        Long result = stringRedisTemplate.execute(script, keys, args.toArray(new String[0]));

        if (result != null && result == skuIds.size()) {
            log.info("Redis库存扣减成功: skuIds={}, quantities={}", skuIds, quantities);
            return true;
        }

        log.warn("Redis库存扣减失败(库存不足): skuIds={}, quantities={}, result={}", skuIds, quantities, result);
        if (result != null && result > 0) {
            rollbackPartialDeduct(skuIds, quantities, result);
        }
        return false;
    }

    public void addStock(List<Long> skuIds, List<Integer> quantities) {
        if (skuIds.size() != quantities.size() || skuIds.isEmpty()) {
            return;
        }

        List<String> keys = new ArrayList<>();
        List<String> args = new ArrayList<>();
        for (int i = 0; i < skuIds.size(); i++) {
            keys.add(RedisConstant.PRODUCT_STOCK_KEY + skuIds.get(i));
            args.add(String.valueOf(quantities.get(i)));
        }

        DefaultRedisScript<Long> script = new DefaultRedisScript<>(ADD_STOCK_LUA, Long.class);
        stringRedisTemplate.execute(script, keys, args.toArray(new String[0]));
        log.info("Redis库存回滚成功: skuIds={}, quantities={}", skuIds, quantities);
    }

    public void addStock(Long skuId, Integer quantity) {
        addStock(Collections.singletonList(skuId), Collections.singletonList(quantity));
    }

    private void rollbackPartialDeduct(List<Long> skuIds, List<Integer> quantities, long deductedCount) {
        if (deductedCount <= 0) return;
        List<Long> rollbackSkuIds = skuIds.subList(0, (int) deductedCount);
        List<Integer> rollbackQuantities = quantities.subList(0, (int) deductedCount);
        try {
            addStock(rollbackSkuIds, rollbackQuantities);
            log.info("部分扣减回滚成功: 回滚了前{}个SKU", deductedCount);
        } catch (Exception e) {
            log.error("部分扣减回滚失败，需人工处理: skuIds={}, quantities={}", rollbackSkuIds, rollbackQuantities, e);
        }
    }
}
