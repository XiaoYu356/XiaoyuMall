package com.mall.user.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.user.dto.UserCreateDTO;
import com.mall.user.dto.UserLoginDTO;
import com.mall.user.dto.UserQueryDTO;
import com.mall.user.dto.UserRegisterDTO;
import com.mall.user.entity.User;

import java.util.Map;

public interface UserService {

    Map<String, Object> getUserStats();

    User register(UserRegisterDTO dto);

    User createUser(UserCreateDTO dto);
    
    String login(UserLoginDTO dto);
    
    User getUserById(Long userId);
    
    User getUserByUsername(String username);
    
    User updateUserInfo(User user);
    
    Page<User> getUserList(UserQueryDTO dto);
    
    void deleteUser(Long userId);
}
