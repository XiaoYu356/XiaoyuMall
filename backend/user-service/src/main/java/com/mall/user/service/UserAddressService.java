package com.mall.user.service;

import com.mall.user.entity.UserAddress;

import java.util.List;

public interface UserAddressService {

    List<UserAddress> getAddressList(Long userId);

    UserAddress getAddressById(Long addressId);

    UserAddress addAddress(UserAddress address);

    UserAddress updateAddress(UserAddress address);

    void deleteAddress(Long userId, Long addressId);

    void setDefaultAddress(Long userId, Long addressId);
}
