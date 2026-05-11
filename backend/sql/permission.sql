USE mall_user;

-- 角色表
CREATE TABLE IF NOT EXISTS `role` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  `role_name` varchar(50) NOT NULL COMMENT '角色名称',
  `role_code` varchar(50) NOT NULL COMMENT '角色编码',
  `description` varchar(200) DEFAULT NULL COMMENT '角色描述',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态:0-禁用,1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- 权限表
CREATE TABLE IF NOT EXISTS `permission` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '权限ID',
  `permission_name` varchar(50) NOT NULL COMMENT '权限名称',
  `permission_code` varchar(50) NOT NULL COMMENT '权限编码',
  `resource_type` tinyint(4) NOT NULL COMMENT '资源类型:1-菜单,2-按钮,3-接口',
  `parent_id` bigint(20) DEFAULT '0' COMMENT '父权限ID',
  `menu_url` varchar(200) DEFAULT NULL COMMENT '菜单路径',
  `api_url` varchar(200) DEFAULT NULL COMMENT '接口路径',
  `icon` varchar(100) DEFAULT NULL COMMENT '图标',
  `sort` int(11) DEFAULT '0' COMMENT '排序',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_permission_code` (`permission_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限表';

-- 用户角色关联表
CREATE TABLE IF NOT EXISTS `user_role` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `role_id` bigint(20) NOT NULL COMMENT '角色ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role` (`user_id`,`role_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_role_id` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';

-- 角色权限关联表
CREATE TABLE IF NOT EXISTS `role_permission` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `role_id` bigint(20) NOT NULL COMMENT '角色ID',
  `permission_id` bigint(20) NOT NULL COMMENT '权限ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_permission` (`role_id`,`permission_id`),
  KEY `idx_role_id` (`role_id`),
  KEY `idx_permission_id` (`permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色权限关联表';

-- 插入默认角色
INSERT IGNORE INTO `role` (`role_name`, `role_code`, `description`) VALUES
('超级管理员', 'super_admin', '拥有所有权限'),
('管理员', 'admin', '拥有管理权限'),
('普通用户', 'user', '普通用户权限');

-- 插入权限数据
INSERT IGNORE INTO `permission` (`permission_name`, `permission_code`, `resource_type`, `parent_id`, `menu_url`, `sort`) VALUES
('用户管理', 'user', 1, 0, '/users', 1),
('用户查看', 'user:view', 2, 1, NULL, 1),
('用户新增', 'user:add', 2, 1, NULL, 2),
('用户编辑', 'user:edit', 2, 1, NULL, 3),
('用户删除', 'user:delete', 2, 1, NULL, 4),
('商品管理', 'product', 1, 0, '/products', 2),
('商品查看', 'product:view', 2, 6, NULL, 1),
('商品新增', 'product:add', 2, 6, NULL, 2),
('商品编辑', 'product:edit', 2, 6, NULL, 3),
('商品删除', 'product:delete', 2, 6, NULL, 4),
('优惠券管理', 'coupon', 1, 0, '/coupons', 3),
('优惠券查看', 'coupon:view', 2, 11, NULL, 1),
('优惠券新增', 'coupon:add', 2, 11, NULL, 2),
('优惠券编辑', 'coupon:edit', 2, 11, NULL, 3),
('优惠券删除', 'coupon:delete', 2, 11, NULL, 4),
('订单管理', 'order', 1, 0, '/orders', 4),
('订单查看', 'order:view', 2, 16, NULL, 1),
('订单发货', 'order:ship', 2, 16, NULL, 2),
('订单取消', 'order:cancel', 2, 16, NULL, 3),
('AI智能助手', 'ai', 1, 0, '/ai-assistant', 5),
('AI分析', 'ai:analyze', 2, 19, NULL, 1);

-- 为超级管理员分配所有权限
INSERT IGNORE INTO `role_permission` (`role_id`, `permission_id`)
SELECT 1, id FROM `permission`;

-- 为管理员分配部分权限
INSERT IGNORE INTO `role_permission` (`role_id`, `permission_id`) VALUES
(2, 1), (2, 2), (2, 3), (2, 4),
(2, 6), (2, 7), (2, 8), (2, 9),
(2, 11), (2, 12), (2, 13), (2, 14),
(2, 16), (2, 17), (2, 18);

-- 为普通用户分配查看权限
INSERT IGNORE INTO `role_permission` (`role_id`, `permission_id`) VALUES
(3, 1), (3, 2),
(3, 6), (3, 7),
(3, 11), (3, 12),
(3, 16), (3, 17);

-- 为admin用户分配超级管理员角色
INSERT IGNORE INTO `user_role` (`user_id`, `role_id`) VALUES (1, 1);
