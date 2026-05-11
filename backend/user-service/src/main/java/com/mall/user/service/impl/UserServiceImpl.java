package com.mall.user.service.impl;

import cn.dev33.satoken.stp.StpUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.crypto.digest.BCrypt;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.mall.common.constant.RedisConstant;
import com.mall.common.exception.BusinessException;
import com.mall.user.dto.UserCreateDTO;
import com.mall.user.dto.UserLoginDTO;
import com.mall.user.dto.UserQueryDTO;
import com.mall.user.dto.UserRegisterDTO;
import com.mall.user.entity.User;
import com.mall.user.entity.UserRole;
import com.mall.user.mapper.UserMapper;
import com.mall.user.mapper.UserRoleMapper;
import com.mall.user.service.UserService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class UserServiceImpl implements UserService {

    @Autowired
    private UserMapper userMapper;

    @Override
    public Map<String, Object> getUserStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("userCount", userMapper.selectCount(null));
        stats.put("activeCount", userMapper.selectCount(
                new LambdaQueryWrapper<User>().eq(User::getStatus, 1)));
        stats.put("disabledCount", userMapper.selectCount(
                new LambdaQueryWrapper<User>().eq(User::getStatus, 0)));
        return stats;
    }

    private static final Long DEFAULT_ROLE_ID = 3L;
    private static final String DEFAULT_PASSWORD = "123456";

    
    @Autowired
    private UserRoleMapper userRoleMapper;
    
    @Autowired
    private RedisTemplate<String, Object> redisTemplate;
    
    @Override
    @Transactional(rollbackFor = Exception.class)
    public User register(UserRegisterDTO dto) {
        User existUser = userMapper.selectByUsername(dto.getUsername());
        if (existUser != null) {
            throw new BusinessException("用户名已存在");
        }

        User existPhone = userMapper.selectByPhone(dto.getPhone());
        if (existPhone != null) {
            throw new BusinessException("手机号已注册");
        }
        
        User user = new User();
        user.setUsername(dto.getUsername());
        user.setPassword(BCrypt.hashpw(dto.getPassword(), BCrypt.gensalt()));
        user.setNickname(dto.getNickname() != null ? dto.getNickname() : dto.getUsername());
        user.setPhone(dto.getPhone());
        user.setEmail(dto.getEmail());
        user.setStatus(1);
        user.setLevel(1);
        
        userMapper.insert(user);
        
        UserRole userRole = new UserRole();
        userRole.setUserId(user.getId());
        userRole.setRoleId(DEFAULT_ROLE_ID);
        userRole.setCreateTime(LocalDateTime.now());
        userRoleMapper.insert(userRole);
        
        log.info("用户注册成功: {}", user.getUsername());

        return user;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public User createUser(UserCreateDTO dto) {
        User existUser = userMapper.selectByUsername(dto.getUsername());
        if (existUser != null) {
            throw new BusinessException("用户名已存在");
        }

        User user = new User();
        user.setUsername(dto.getUsername());
        String password = dto.getPassword() != null && !dto.getPassword().isBlank()
                ? dto.getPassword() : DEFAULT_PASSWORD;
        user.setPassword(BCrypt.hashpw(password, BCrypt.gensalt()));
        user.setNickname(dto.getNickname() != null ? dto.getNickname() : dto.getUsername());
        user.setPhone(dto.getPhone());
        user.setEmail(dto.getEmail());
        user.setStatus(1);
        user.setLevel(dto.getLevel() != null ? dto.getLevel() : 1);

        userMapper.insert(user);

        UserRole userRole = new UserRole();
        userRole.setUserId(user.getId());
        userRole.setRoleId(DEFAULT_ROLE_ID);
        userRole.setCreateTime(LocalDateTime.now());
        userRoleMapper.insert(userRole);

        log.info("管理员创建用户成功: {}", user.getUsername());

        return user;
    }
    
    @Override
    public String login(UserLoginDTO dto) {
        User user = userMapper.selectByPhone(dto.getPhone());
        if (user == null) {
            throw new BusinessException("手机号或密码错误");
        }

        if (!BCrypt.checkpw(dto.getPassword(), user.getPassword())) {
            throw new BusinessException("手机号或密码错误");
        }

        if (user.getStatus() == 0) {
            throw new BusinessException("账号已被禁用");
        }

        StpUtil.login(user.getId());

        String token = StpUtil.getTokenValue();

        log.info("用户登录成功: {}", user.getUsername());
        
        return token;
    }
    
    @Override
    public User getUserById(Long userId) {
        String userKey = RedisConstant.USER_INFO_KEY + userId;
        User user = (User) redisTemplate.opsForValue().get(userKey);
        
        if (user == null) {
            user = userMapper.selectById(userId);
            if (user != null) {
                redisTemplate.opsForValue().set(userKey, user, RedisConstant.DEFAULT_EXPIRE_TIME, TimeUnit.SECONDS);
            }
        }
        
        return user;
    }
    
    @Override
    public User getUserByUsername(String username) {
        return userMapper.selectByUsername(username);
    }
    
    @Override
    @Transactional(rollbackFor = Exception.class)
    public User updateUserInfo(User user) {
        userMapper.updateById(user);
        
        String userKey = RedisConstant.USER_INFO_KEY + user.getId();
        redisTemplate.delete(userKey);
        
        if (user.getStatus() != null && user.getStatus() == 0) {
            StpUtil.kickout(user.getId());
        }
        
        log.info("用户信息更新成功: {}", user.getUsername());
        
        return user;
    }
    
    @Override
    public Page<User> getUserList(UserQueryDTO dto) {
        Page<User> page = new Page<>(dto.getPageNum(), dto.getPageSize());
        
        LambdaQueryWrapper<User> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.like(StrUtil.isNotBlank(dto.getUsername()), User::getUsername, dto.getUsername())
                .like(StrUtil.isNotBlank(dto.getPhone()), User::getPhone, dto.getPhone())
                .orderByDesc(User::getCreateTime);
        
        Page<User> userPage = userMapper.selectPage(page, queryWrapper);
        
        userPage.getRecords().forEach(user -> user.setPassword(null));
        
        return userPage;
    }
    
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteUser(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException("用户不存在");
        }
        
        userMapper.deleteById(userId);
        
        String userKey = RedisConstant.USER_INFO_KEY + userId;
        redisTemplate.delete(userKey);
        
        StpUtil.kickout(userId);
        
        log.info("用户删除成功: {}", user.getUsername());
    }
}
