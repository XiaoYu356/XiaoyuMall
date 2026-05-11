package com.mall.user.satoken;

import cn.dev33.satoken.stp.StpInterface;
import com.mall.user.mapper.PermissionMapper;
import com.mall.user.mapper.RoleMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class StpInterfaceImpl implements StpInterface {
    
    @Autowired
    private RoleMapper roleMapper;
    
    @Autowired
    private PermissionMapper permissionMapper;
    
    @Override
    public List<String> getPermissionList(Object loginId, String loginType) {
        Long userId = Long.parseLong(loginId.toString());
        return permissionMapper.selectPermissionCodesByUserId(userId);
    }
    
    @Override
    public List<String> getRoleList(Object loginId, String loginType) {
        Long userId = Long.parseLong(loginId.toString());
        return roleMapper.selectRoleCodesByUserId(userId);
    }
}
