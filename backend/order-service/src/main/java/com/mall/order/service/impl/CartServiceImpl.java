package com.mall.order.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.mall.common.exception.BusinessException;
import com.mall.order.dto.AddCartDTO;
import com.mall.order.dto.UpdateCartDTO;
import com.mall.order.entity.Cart;
import com.mall.order.mapper.CartMapper;
import com.mall.order.service.CartService;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class CartServiceImpl implements CartService {

    @Autowired
    private CartMapper cartMapper;

    @Override
    public List<Cart> getCartList(Long userId) {
        LambdaQueryWrapper<Cart> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Cart::getUserId, userId)
               .orderByDesc(Cart::getCreateTime);
        return cartMapper.selectList(wrapper);
    }

    @Override
    public Cart addCart(AddCartDTO addCartDTO) {
        LambdaQueryWrapper<Cart> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Cart::getUserId, addCartDTO.getUserId())
               .eq(Cart::getSkuId, addCartDTO.getSkuId());
        Cart existCart = cartMapper.selectOne(wrapper);

        if (existCart != null) {
            existCart.setQuantity(existCart.getQuantity() + addCartDTO.getQuantity());
            cartMapper.updateById(existCart);
            return existCart;
        }

        Cart cart = new Cart();
        BeanUtils.copyProperties(addCartDTO, cart);
        cart.setSelected(1);
        cartMapper.insert(cart);
        return cart;
    }

    @Override
    public Cart updateCart(UpdateCartDTO updateCartDTO) {
        Cart cart = cartMapper.selectById(updateCartDTO.getId());
        if (cart == null || !cart.getUserId().equals(updateCartDTO.getUserId())) {
            throw new BusinessException("购物车商品不存在");
        }

        if (updateCartDTO.getQuantity() != null) {
            if (updateCartDTO.getQuantity() < 1) {
                throw new BusinessException("商品数量不能小于1");
            }
            cart.setQuantity(updateCartDTO.getQuantity());
        }
        if (updateCartDTO.getSelected() != null) {
            cart.setSelected(updateCartDTO.getSelected());
        }
        cartMapper.updateById(cart);
        return cart;
    }

    @Override
    public void deleteCart(Long userId, Long cartId) {
        LambdaQueryWrapper<Cart> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Cart::getId, cartId)
               .eq(Cart::getUserId, userId);
        int rows = cartMapper.delete(wrapper);
        if (rows == 0) {
            throw new BusinessException("购物车商品不存在");
        }
    }

    @Override
    public void deleteCartBatch(Long userId, List<Long> cartIds) {
        if (cartIds == null || cartIds.isEmpty()) {
            return;
        }
        LambdaQueryWrapper<Cart> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Cart::getUserId, userId)
               .in(Cart::getId, cartIds);
        cartMapper.delete(wrapper);
    }

    @Override
    public void clearCart(Long userId) {
        LambdaQueryWrapper<Cart> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Cart::getUserId, userId);
        cartMapper.delete(wrapper);
    }

    @Override
    public void selectAll(Long userId, Integer selected) {
        LambdaUpdateWrapper<Cart> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(Cart::getUserId, userId)
               .set(Cart::getSelected, selected);
        cartMapper.update(null, wrapper);
    }
}
