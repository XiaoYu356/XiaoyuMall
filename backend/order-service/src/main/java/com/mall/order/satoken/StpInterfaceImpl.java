package com.mall.order.satoken;

import cn.dev33.satoken.stp.StpInterface;
import com.mall.common.result.Result;
import com.mall.order.feign.UserServiceClient;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@Component
public class StpInterfaceImpl implements StpInterface {

    @Autowired
    private UserServiceClient userServiceClient;

    @Override
    public List<String> getPermissionList(Object loginId, String loginType) {
        try {
            Long userId = Long.parseLong(loginId.toString());
            Result<List<String>> result = userServiceClient.getPermissionList(userId);
            if (result != null && result.getCode() == 200) {
                return result.getData();
            }
        } catch (Exception e) {
            log.error("获取用户权限列表失败, userId={}", loginId, e);
        }
        return new ArrayList<>();
    }

    @Override
    public List<String> getRoleList(Object loginId, String loginType) {
        try {
            Long userId = Long.parseLong(loginId.toString());
            Result<List<String>> result = userServiceClient.getRoleList(userId);
            if (result != null && result.getCode() == 200) {
                return result.getData();
            }
        } catch (Exception e) {
            log.error("获取用户角色列表失败, userId={}", loginId, e);
        }
        return new ArrayList<>();
    }
}
