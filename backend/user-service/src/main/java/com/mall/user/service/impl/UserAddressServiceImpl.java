package com.mall.user.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.mall.common.exception.BusinessException;
import com.mall.user.entity.UserAddress;
import com.mall.user.mapper.UserAddressMapper;
import com.mall.user.service.UserAddressService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
public class UserAddressServiceImpl implements UserAddressService {

    @Autowired
    private UserAddressMapper userAddressMapper;

    @Override
    public List<UserAddress> getAddressList(Long userId) {
        LambdaQueryWrapper<UserAddress> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserAddress::getUserId, userId)
               .orderByDesc(UserAddress::getIsDefault)
               .orderByDesc(UserAddress::getCreateTime);
        return userAddressMapper.selectList(wrapper);
    }

    @Override
    public UserAddress getAddressById(Long addressId) {
        return userAddressMapper.selectById(addressId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserAddress addAddress(UserAddress address) {
        if (address.getIsDefault() == null) {
            address.setIsDefault(0);
        }

        if (Integer.valueOf(1).equals(address.getIsDefault())) {
            clearDefaultAddress(address.getUserId());
        }

        userAddressMapper.insert(address);
        log.info("用户地址添加成功: userId={}", address.getUserId());
        return address;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserAddress updateAddress(UserAddress address) {
        UserAddress existing = userAddressMapper.selectById(address.getId());
        if (existing == null || !existing.getUserId().equals(address.getUserId())) {
            throw new BusinessException("地址不存在");
        }

        if (Integer.valueOf(1).equals(address.getIsDefault())) {
            clearDefaultAddress(address.getUserId());
        }

        userAddressMapper.updateById(address);
        log.info("用户地址更新成功: addressId={}", address.getId());
        return address;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteAddress(Long userId, Long addressId) {
        LambdaQueryWrapper<UserAddress> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserAddress::getId, addressId)
               .eq(UserAddress::getUserId, userId);
        int rows = userAddressMapper.delete(wrapper);
        if (rows == 0) {
            throw new BusinessException("地址不存在");
        }
        log.info("用户地址删除成功: addressId={}", addressId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void setDefaultAddress(Long userId, Long addressId) {
        UserAddress address = userAddressMapper.selectById(addressId);
        if (address == null || !address.getUserId().equals(userId)) {
            throw new BusinessException("地址不存在");
        }

        clearDefaultAddress(userId);

        address.setIsDefault(1);
        userAddressMapper.updateById(address);
        log.info("设置默认地址成功: addressId={}", addressId);
    }

    private void clearDefaultAddress(Long userId) {
        LambdaUpdateWrapper<UserAddress> updateWrapper = new LambdaUpdateWrapper<>();
        updateWrapper.eq(UserAddress::getUserId, userId)
                     .eq(UserAddress::getIsDefault, 1)
                     .set(UserAddress::getIsDefault, 0);
        userAddressMapper.update(null, updateWrapper);
    }
}
