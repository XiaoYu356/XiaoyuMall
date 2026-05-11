package com.mall.order.service;

import com.mall.order.dto.AddCartDTO;
import com.mall.order.dto.UpdateCartDTO;
import com.mall.order.entity.Cart;

import java.util.List;

public interface CartService {
    
    List<Cart> getCartList(Long userId);
    
    Cart addCart(AddCartDTO addCartDTO);
    
    Cart updateCart(UpdateCartDTO updateCartDTO);
    
    void deleteCart(Long userId, Long cartId);
    
    void deleteCartBatch(Long userId, List<Long> cartIds);
    
    void clearCart(Long userId);
    
    void selectAll(Long userId, Integer selected);
}
