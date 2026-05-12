-- ============================================
-- XiaoyuMall 数据库初始化脚本
-- 基于项目 Java Entity 模型生成
-- ============================================

-- ============================================
-- 1. 用户数据库 (mall_user)
-- ============================================
CREATE DATABASE IF NOT EXISTS mall_user DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mall_user;

-- 用户表 (对应 com.mall.user.entity.User)
CREATE TABLE IF NOT EXISTS `user` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `password` varchar(100) NOT NULL COMMENT '密码',
  `nickname` varchar(50) DEFAULT NULL COMMENT '昵称',
  `phone` varchar(20) DEFAULT NULL COMMENT '手机号',
  `email` varchar(100) DEFAULT NULL COMMENT '邮箱',
  `avatar` varchar(500) DEFAULT NULL COMMENT '头像',
  `gender` tinyint(4) DEFAULT NULL COMMENT '性别:0-未知,1-男,2-女',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态:0-禁用,1-启用',
  `level` tinyint(4) NOT NULL DEFAULT '1' COMMENT '会员等级',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 用户地址表 (对应 com.mall.user.entity.UserAddress)
CREATE TABLE IF NOT EXISTS `user_address` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `receiver_name` varchar(50) NOT NULL COMMENT '收货人姓名',
  `receiver_phone` varchar(20) NOT NULL COMMENT '收货人电话',
  `province` varchar(50) NOT NULL COMMENT '省份',
  `city` varchar(50) NOT NULL COMMENT '城市',
  `district` varchar(50) NOT NULL COMMENT '区县',
  `detail_address` varchar(200) NOT NULL COMMENT '详细地址',
  `is_default` tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否默认:0-否,1-是',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户地址表';

-- 角色表 (对应 com.mall.user.entity.Role)
CREATE TABLE IF NOT EXISTS `role` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '角色ID',
  `role_name` varchar(50) NOT NULL COMMENT '角色名称',
  `role_code` varchar(50) NOT NULL COMMENT '角色编码',
  `description` varchar(200) DEFAULT NULL COMMENT '角色描述',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态:0-禁用,1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- 权限表 (对应 com.mall.user.entity.Permission)
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
  `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_permission_code` (`permission_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限表';

-- 用户角色关联表 (对应 com.mall.user.entity.UserRole)
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

-- ============================================
-- 2. 商品数据库 (mall_product)
-- ============================================
CREATE DATABASE IF NOT EXISTS mall_product DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mall_product;

-- 品牌表 (对应 com.mall.product.entity.Brand)
CREATE TABLE IF NOT EXISTS `brand` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '品牌ID',
  `brand_name` varchar(100) NOT NULL COMMENT '品牌名称',
  `logo` varchar(500) DEFAULT NULL COMMENT '品牌Logo URL',
  `description` varchar(500) DEFAULT NULL COMMENT '品牌描述',
  `sort` int(11) DEFAULT '0' COMMENT '排序',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态:0-禁用,1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_brand_name` (`brand_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='品牌表';

-- 商品表 (对应 com.mall.product.entity.Product)
CREATE TABLE IF NOT EXISTS `product` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '商品ID',
  `product_name` varchar(200) NOT NULL COMMENT '商品名称',
  `category_id` bigint(20) NOT NULL COMMENT '分类ID',
  `brand_id` bigint(20) DEFAULT NULL COMMENT '品牌ID',
  `product_code` varchar(50) NOT NULL COMMENT '商品编码',
  `price` decimal(10,2) NOT NULL COMMENT '销售价格',
  `original_price` decimal(10,2) DEFAULT NULL COMMENT '原价',
  `description` text COMMENT '商品描述',
  `main_image` varchar(500) DEFAULT NULL COMMENT '主图URL',
  `sub_images` text COMMENT '副图URLs(JSON)',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态:0-下架,1-上架',
  `sort` int(11) DEFAULT '0' COMMENT '排序',
  `sales` int(11) DEFAULT '0' COMMENT '销量',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  KEY `idx_category_id` (`category_id`),
  KEY `idx_product_code` (`product_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- 商品SKU表 (对应 com.mall.product.entity.ProductSku)
CREATE TABLE IF NOT EXISTS `product_sku` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `product_id` bigint(20) NOT NULL COMMENT '商品ID',
  `sku_code` varchar(50) NOT NULL COMMENT 'SKU编码',
  `sku_name` varchar(200) NOT NULL COMMENT 'SKU名称',
  `price` decimal(10,2) NOT NULL COMMENT 'SKU价格',
  `stock` int(11) NOT NULL DEFAULT '0' COMMENT '库存',
  `specs` json COMMENT '规格属性(JSON)',
  `image` varchar(500) DEFAULT NULL COMMENT 'SKU图片',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sku_code` (`sku_code`),
  KEY `idx_product_id` (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品SKU表';

-- 商品分类表 (对应 com.mall.product.entity.ProductCategory)
CREATE TABLE IF NOT EXISTS `product_category` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `parent_id` bigint(20) NOT NULL DEFAULT '0' COMMENT '父分类ID',
  `category_name` varchar(50) NOT NULL COMMENT '分类名称',
  `category_level` tinyint(4) NOT NULL COMMENT '分类层级',
  `icon` varchar(200) DEFAULT NULL COMMENT '分类图标',
  `sort` int(11) DEFAULT '0' COMMENT '排序',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表';

-- ============================================
-- 3. 优惠券数据库 (mall_coupon)
-- ============================================
CREATE DATABASE IF NOT EXISTS mall_coupon DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mall_coupon;

-- 优惠券模板表 (对应 com.mall.coupon.entity.CouponTemplate)
CREATE TABLE IF NOT EXISTS `coupon_template` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `template_name` varchar(100) NOT NULL COMMENT '优惠券模板名称',
  `coupon_type` tinyint(4) NOT NULL COMMENT '类型:1-满减券,2-折扣券,3-现金券',
  `coupon_value` decimal(10,2) NOT NULL COMMENT '优惠值',
  `min_amount` decimal(10,2) DEFAULT '0.00' COMMENT '最低消费金额',
  `total_count` int(11) NOT NULL COMMENT '发行总量',
  `used_count` int(11) NOT NULL DEFAULT '0' COMMENT '已使用数量',
  `per_limit` int(11) NOT NULL DEFAULT '1' COMMENT '每人限领数量',
  `start_time` datetime NOT NULL COMMENT '生效开始时间',
  `end_time` datetime NOT NULL COMMENT '生效结束时间',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态:0-禁用,1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券模板表';

-- 用户优惠券表 (对应 com.mall.coupon.entity.UserCoupon)
CREATE TABLE IF NOT EXISTS `user_coupon` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `template_id` bigint(20) NOT NULL COMMENT '优惠券模板ID',
  `coupon_code` varchar(50) NOT NULL COMMENT '优惠券码',
  `status` tinyint(4) NOT NULL DEFAULT '0' COMMENT '状态:0-未使用,1-已使用,2-已过期',
  `order_id` bigint(20) DEFAULT NULL COMMENT '使用的订单ID',
  `use_time` datetime DEFAULT NULL COMMENT '使用时间',
  `expire_time` datetime NOT NULL COMMENT '过期时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_coupon_code` (`coupon_code`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户优惠券表';

-- ============================================
-- 4. 订单数据库 (mall_order)
-- ============================================
CREATE DATABASE IF NOT EXISTS mall_order DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mall_order;

-- 订单表 (对应 com.mall.order.entity.Order)
CREATE TABLE IF NOT EXISTS `order` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `order_no` varchar(50) NOT NULL COMMENT '订单号',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `total_amount` decimal(10,2) NOT NULL COMMENT '订单总金额',
  `pay_amount` decimal(10,2) NOT NULL COMMENT '实付金额',
  `discount_amount` decimal(10,2) DEFAULT '0.00' COMMENT '优惠金额',
  `coupon_id` bigint(20) DEFAULT NULL COMMENT '使用的优惠券ID',
  `status` tinyint(4) NOT NULL DEFAULT '0' COMMENT '状态:0-待支付,1-已支付,2-已发货,3-已完成,4-已取消,5-已退款',
  `receiver_name` varchar(50) NOT NULL COMMENT '收货人姓名',
  `receiver_phone` varchar(20) NOT NULL COMMENT '收货人电话',
  `receiver_address` varchar(200) NOT NULL COMMENT '收货地址',
  `payment_time` datetime DEFAULT NULL COMMENT '支付时间',
  `delivery_time` datetime DEFAULT NULL COMMENT '发货时间',
  `receive_time` datetime DEFAULT NULL COMMENT '收货时间',
  `remark` varchar(500) DEFAULT NULL COMMENT '订单备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- 订单明细表 (对应 com.mall.order.entity.OrderItem)
CREATE TABLE IF NOT EXISTS `order_item` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `order_id` bigint(20) NOT NULL COMMENT '订单ID',
  `order_no` varchar(50) NOT NULL COMMENT '订单号',
  `product_id` bigint(20) NOT NULL COMMENT '商品ID',
  `sku_id` bigint(20) NOT NULL COMMENT 'SKU ID',
  `product_name` varchar(200) NOT NULL COMMENT '商品名称',
  `sku_name` varchar(200) NOT NULL COMMENT 'SKU名称',
  `sku_code` varchar(50) NOT NULL COMMENT 'SKU编码',
  `price` decimal(10,2) NOT NULL COMMENT '商品单价',
  `quantity` int(11) NOT NULL COMMENT '购买数量',
  `total_amount` decimal(10,2) NOT NULL COMMENT '小计金额',
  `product_image` varchar(500) DEFAULT NULL COMMENT '商品图片',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order_id` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单明细表';

-- 购物车表 (对应 com.mall.order.entity.Cart)
CREATE TABLE IF NOT EXISTS `cart` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `product_id` bigint(20) NOT NULL COMMENT '商品ID',
  `sku_id` bigint(20) NOT NULL COMMENT 'SKU ID',
  `product_name` varchar(200) NOT NULL COMMENT '商品名称',
  `sku_name` varchar(200) DEFAULT NULL COMMENT 'SKU名称',
  `price` decimal(10,2) NOT NULL COMMENT '商品单价',
  `quantity` int(11) NOT NULL DEFAULT '1' COMMENT '商品数量',
  `product_image` varchar(500) DEFAULT NULL COMMENT '商品图片',
  `selected` tinyint(4) NOT NULL DEFAULT '1' COMMENT '是否选中:0-否,1-是',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_sku` (`user_id`, `sku_id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购物车表';

-- ============================================
-- 5. 测试数据
-- ============================================

-- 5.1 用户数据
USE mall_user;

-- 密码均为 123456 的 BCrypt 加密值
INSERT IGNORE INTO `user` (`id`, `username`, `password`, `nickname`, `phone`, `email`, `gender`, `status`, `level`) VALUES
(1, 'admin', '$2a$10$nUOkzR2hPe9l40vBfHwn.ehMWvN1i1oyWFX8KDSD2q2fb5dVhuruW', '管理员', '13800138000', 'admin@xiaoyumall.com', 1, 1, 5),
(2, 'testuser', '$2a$10$nUOkzR2hPe9l40vBfHwn.ehMWvN1i1oyWFX8KDSD2q2fb5dVhuruW', '测试用户', '13900139000', 'test@xiaoyumall.com', 1, 1, 1),
(3, 'zhangsan', '$2a$10$nUOkzR2hPe9l40vBfHwn.ehMWvN1i1oyWFX8KDSD2q2fb5dVhuruW', '张三', '13700137000', 'zhangsan@xiaoyumall.com', 1, 1, 2);

-- 用户地址
INSERT IGNORE INTO `user_address` (`id`, `user_id`, `receiver_name`, `receiver_phone`, `province`, `city`, `district`, `detail_address`, `is_default`) VALUES
(1, 1, '管理员', '13800138000', '广东省', '深圳市', '南山区', '科技园路100号', 1),
(2, 2, '测试用户', '13900139000', '北京市', '北京市', '朝阳区', '望京街道200号', 1),
(3, 3, '张三', '13700137000', '上海市', '上海市', '浦东新区', '陆家嘴金融中心大厦3001室', 1);

-- 5.2 角色与权限数据
INSERT IGNORE INTO `role` (`id`, `role_name`, `role_code`, `description`) VALUES
(1, '超级管理员', 'super_admin', '拥有所有权限'),
(2, '管理员', 'admin', '拥有管理权限'),
(3, '普通用户', 'user', '普通用户权限');

INSERT IGNORE INTO `permission` (`id`, `permission_name`, `permission_code`, `resource_type`, `parent_id`, `menu_url`, `sort`) VALUES
(1, '用户管理', 'user', 1, 0, '/users', 1),
(2, '用户查看', 'user:view', 2, 1, NULL, 1),
(3, '用户新增', 'user:add', 2, 1, NULL, 2),
(4, '用户编辑', 'user:edit', 2, 1, NULL, 3),
(5, '用户删除', 'user:delete', 2, 1, NULL, 4),
(6, '商品管理', 'product', 1, 0, '/products', 2),
(7, '商品查看', 'product:view', 2, 6, NULL, 1),
(8, '商品新增', 'product:add', 2, 6, NULL, 2),
(9, '商品编辑', 'product:edit', 2, 6, NULL, 3),
(10, '商品删除', 'product:delete', 2, 6, NULL, 4),
(11, '优惠券管理', 'coupon', 1, 0, '/coupons', 3),
(12, '优惠券查看', 'coupon:view', 2, 11, NULL, 1),
(13, '优惠券新增', 'coupon:add', 2, 11, NULL, 2),
(14, '优惠券编辑', 'coupon:edit', 2, 11, NULL, 3),
(15, '优惠券删除', 'coupon:delete', 2, 11, NULL, 4),
(16, '订单管理', 'order', 1, 0, '/orders', 4),
(17, '订单查看', 'order:view', 2, 16, NULL, 1),
(18, '订单发货', 'order:ship', 2, 16, NULL, 2),
(19, '订单取消', 'order:cancel', 2, 16, NULL, 3),
(20, 'AI智能助手', 'ai', 1, 0, '/ai-assistant', 5),
(21, 'AI分析', 'ai:analyze', 2, 20, NULL, 1);

-- 为超级管理员(role_id=1)分配所有权限
INSERT IGNORE INTO `role_permission` (`role_id`, `permission_id`)
SELECT 1, id FROM `permission`;

-- 为管理员(role_id=2)分配管理权限
INSERT IGNORE INTO `role_permission` (`role_id`, `permission_id`) VALUES
(2, 1), (2, 2), (2, 3), (2, 4),
(2, 6), (2, 7), (2, 8), (2, 9),
(2, 11), (2, 12), (2, 13), (2, 14),
(2, 16), (2, 17), (2, 18);

-- 为普通用户(role_id=3)分配查看权限
INSERT IGNORE INTO `role_permission` (`role_id`, `permission_id`) VALUES
(3, 1), (3, 2),
(3, 6), (3, 7),
(3, 11), (3, 12),
(3, 16), (3, 17);

-- 分配用户角色
INSERT IGNORE INTO `user_role` (`user_id`, `role_id`) VALUES
(1, 1),
(2, 2),
(3, 3);

-- 5.3 商品分类数据
USE mall_product;

-- 品牌数据
INSERT IGNORE INTO `brand` (`id`, `brand_name`, `logo`, `description`, `sort`, `status`) VALUES
(1, 'Apple', 'https://picsum.photos/seed/apple/100/100', '苹果公司，全球领先的科技企业', 1, 1),
(2, '华为', 'https://picsum.photos/seed/huawei/100/100', '华为技术有限公司，全球领先的ICT基础设施和智能终端提供商', 2, 1),
(3, '小米', 'https://picsum.photos/seed/xiaomi/100/100', '小米科技有限责任公司，让每个人都能享受科技的乐趣', 3, 1),
(4, 'OPPO', 'https://picsum.photos/seed/oppo/100/100', 'OPPO广东移动通信有限公司，致美科技', 4, 1),
(5, '联想', 'https://picsum.photos/seed/lenovo/100/100', '联想集团，全球PC领导厂商', 5, 1),
(6, '美的', 'https://picsum.photos/seed/midea/100/100', '美的集团，智慧生活可以更美', 6, 1),
(7, '九阳', 'https://picsum.photos/seed/joyoung/100/100', '九阳股份，健康生活电器品牌', 7, 1),
(8, '戴森', 'https://picsum.photos/seed/dyson/100/100', 'Dyson戴森，英国科技创新品牌', 8, 1),
(9, '科沃斯', 'https://picsum.photos/seed/ecovacs/100/100', '科沃斯机器人，让机器人服务全球家庭', 9, 1),
(10, '海澜之家', 'https://picsum.photos/seed/hla/100/100', '海澜之家，男人的衣柜', 10, 1),
(11, '伊芙丽', 'https://picsum.photos/seed/eifini/100/100', '伊芙丽，优雅法式女装品牌', 11, 1),
(12, '三只松鼠', 'https://picsum.photos/seed/3songshu/100/100', '三只松鼠，互联网坚果零食品牌', 12, 1);

INSERT IGNORE INTO `product_category` (`id`, `parent_id`, `category_name`, `category_level`, `sort`, `status`) VALUES
(1, 0, '数码产品', 1, 1, 1),
(2, 1, '手机', 2, 1, 1),
(3, 1, '电脑', 2, 2, 1),
(4, 1, '平板', 2, 3, 1),
(5, 1, '智能穿戴', 2, 4, 1),
(6, 0, '家用电器', 1, 2, 1),
(7, 6, '厨房电器', 2, 1, 1),
(8, 6, '生活电器', 2, 2, 1),
(9, 0, '服装鞋帽', 1, 3, 1),
(10, 9, '男装', 2, 1, 1),
(11, 9, '女装', 2, 2, 1),
(12, 9, '运动服饰', 2, 3, 1),
(13, 0, '食品生鲜', 1, 4, 1),
(14, 13, '水果', 2, 1, 1),
(15, 13, '零食', 2, 2, 1),
(16, 0, '图书教育', 1, 5, 1),
(17, 16, '小说', 2, 1, 1),
(18, 16, '教材', 2, 2, 1);

-- 5.4 商品数据
-- 手机类
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(1, 'iPhone 15 Pro', 2, 1, 'IPHONE15PRO001', 7999.00, 8999.00, 'Apple iPhone 15 Pro 256GB，A17 Pro芯片，钛金属设计，4800万像素主摄', 'https://picsum.photos/seed/iphone15/400/400', 1, 1, 328),
(2, '华为 Mate 60 Pro', 2, 2, 'MATE60PRO001', 6999.00, 7999.00, '华为 Mate 60 Pro 512GB，麒麟9000S芯片，卫星通话，超强影像', 'https://picsum.photos/seed/mate60/400/400', 1, 2, 512),
(3, '小米 14 Pro', 2, 3, 'MI14PRO001', 4999.00, 5499.00, '小米 14 Pro 256GB，骁龙8Gen3，徕卡光学镜头，120W快充', 'https://picsum.photos/seed/mi14/400/400', 1, 3, 756),
(4, 'OPPO Find X7', 2, 4, 'FINDX7001', 4599.00, 4999.00, 'OPPO Find X7 256GB，天玑9300，哈苏影像，100W超级闪充', 'https://picsum.photos/seed/findx7/400/400', 1, 4, 215);

-- 电脑类
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(5, 'MacBook Pro 14英寸', 3, 1, 'MACBOOKPRO14M3', 14999.00, 16499.00, 'Apple MacBook Pro 14英寸 M3 Pro芯片 18GB/512GB，Liquid Retina XDR显示屏', 'https://picsum.photos/seed/macbook14/400/400', 1, 1, 189),
(6, 'ThinkPad X1 Carbon', 3, 5, 'THINKPADX1C01', 9999.00, 10999.00, '联想 ThinkPad X1 Carbon Gen 11，i7-1365U/16GB/512GB，2.8K OLED屏', 'https://picsum.photos/seed/thinkpad/400/400', 1, 2, 95),
(7, '华为 MateBook X Pro', 3, 2, 'MATEBOOKXPRO01', 8999.00, 9999.00, '华为 MateBook X Pro 2024款，Ultra 7/16GB/1TB，3.1K OLED触控屏', 'https://picsum.photos/seed/matebook/400/400', 1, 3, 143);

-- 平板类
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(8, 'iPad Air M2', 4, 1, 'IPADAIRM2001', 4799.00, 5299.00, 'Apple iPad Air M2芯片 11英寸，Liquid Retina显示屏，支持Apple Pencil Pro', 'https://picsum.photos/seed/ipadair/400/400', 1, 1, 267),
(9, '华为 MatePad Pro', 4, 2, 'MATEPADPRO001', 3699.00, 4299.00, '华为 MatePad Pro 13.2英寸，OLED柔性屏，天生会画，鸿蒙生态', 'https://picsum.photos/seed/matepad/400/400', 1, 2, 178);

-- 智能穿戴
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(10, 'Apple Watch Ultra 2', 5, 1, 'APPLEWATCHULTRA2001', 6499.00, 6999.00, 'Apple Watch Ultra 2 49mm，钛金属表壳，精准双频GPS，2000尼特亮度', 'https://picsum.photos/seed/awultra2/400/400', 1, 1, 87),
(11, '小米手环 8 Pro', 5, 3, 'MIBAND8PRO001', 399.00, 449.00, '小米手环 8 Pro，1.74英寸AMOLED屏，独立GNSS定位，14天长续航', 'https://picsum.photos/seed/miband8/400/400', 1, 2, 1523);

-- 厨房电器
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(12, '美的微波炉 M3-L239C', 7, 6, 'MIDEAM3239C001', 599.00, 799.00, '美的微波炉 23L，变频微蒸烤一体，智能菜单，平板加热', 'https://picsum.photos/seed/midea/400/400', 1, 1, 456),
(13, '九阳破壁机 L18-P510', 7, 7, 'JOYOUNGL18P51001', 899.00, 1299.00, '九阳破壁机，1.75L大容量，低音破壁，一键自清洗，12小时预约', 'https://picsum.photos/seed/joyoung/400/400', 1, 2, 678);

-- 生活电器
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(14, '戴森 V15 Detect', 8, 8, 'DYSONV15DETECT001', 4990.00, 5490.00, '戴森 V15 Detect无绳吸尘器，激光探测微尘，压电式传感器，60分钟续航', 'https://picsum.photos/seed/dyson/400/400', 1, 1, 234),
(15, '科沃斯 T30 PRO', 8, 9, 'ECOVACST30PRO001', 3999.00, 4599.00, '科沃斯 T30 PRO扫拖机器人，全能基站，热水洗拖布，11000Pa大吸力', 'https://picsum.photos/seed/ecovacs/400/400', 1, 2, 189);

-- 男装
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(16, '海澜之家商务POLO衫', 10, 10, 'HLAPOLO001', 299.00, 399.00, '海澜之家男士商务休闲POLO衫，纯棉面料，经典版型，多色可选', 'https://picsum.photos/seed/polo/400/400', 1, 1, 1023);

-- 女装
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(17, '伊芙丽碎花连衣裙', 11, 11, 'EVELILYD001', 459.00, 599.00, '伊芙丽夏季法式碎花连衣裙，雪纺面料，收腰显瘦，优雅气质', 'https://picsum.photos/seed/dress/400/400', 1, 1, 654);

-- 零食
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(18, '三只松鼠坚果大礼包', 15, 12, 'SZS9001', 99.00, 139.00, '三只松鼠每日坚果礼盒 750g，6种坚果+3种果干混合装，新鲜健康', 'https://picsum.photos/seed/squirrel/400/400', 1, 1, 8932);

-- 图书
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(19, '三体（全三册）', 17, NULL, 'THREEBODY001', 68.00, 93.00, '刘慈欣科幻小说《三体》全三册套装，雨果奖获奖作品，中国科幻巅峰之作', 'https://picsum.photos/seed/threebody/400/400', 1, 1, 4567),
(20, 'Java编程思想（第4版）', 18, NULL, 'THINKINJAVA001', 89.00, 108.00, '《Thinking in Java》中文版第4版，Java开发者必读经典，从入门到精通', 'https://picsum.photos/seed/thinkjava/400/400', 1, 2, 1234);

-- 5.5 商品SKU数据
-- iPhone 15 Pro SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(1, 1, 'IP15P-256-BLACK', 'iPhone 15 Pro 256GB 黑色', 7999.00, 80, '{"颜色":"黑色","存储":"256GB"}', 1),
(2, 1, 'IP15P-256-WHITE', 'iPhone 15 Pro 256GB 白色', 7999.00, 60, '{"颜色":"白色","存储":"256GB"}', 1),
(3, 1, 'IP15P-512-BLACK', 'iPhone 15 Pro 512GB 黑色', 9999.00, 30, '{"颜色":"黑色","存储":"512GB"}', 1),
(4, 1, 'IP15P-1TB-BLACK', 'iPhone 15 Pro 1TB 黑色', 12999.00, 15, '{"颜色":"黑色","存储":"1TB"}', 1);

-- 华为 Mate 60 Pro SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(5, 2, 'M60P-512-BLACK', '华为 Mate 60 Pro 512GB 雅丹黑', 6999.00, 45, '{"颜色":"雅丹黑","存储":"512GB"}', 1),
(6, 2, 'M60P-512-WHITE', '华为 Mate 60 Pro 512GB 白沙银', 6999.00, 35, '{"颜色":"白沙银","存储":"512GB"}', 1),
(7, 2, 'M60P-1TB-BLACK', '华为 Mate 60 Pro 1TB 雅丹黑', 7999.00, 20, '{"颜色":"雅丹黑","存储":"1TB"}', 1);

-- 小米 14 Pro SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(8, 3, 'MI14P-256-BLACK', '小米 14 Pro 256GB 黑色', 4999.00, 100, '{"颜色":"黑色","存储":"256GB"}', 1),
(9, 3, 'MI14P-256-WHITE', '小米 14 Pro 256GB 白色', 4999.00, 80, '{"颜色":"白色","存储":"256GB"}', 1),
(10, 3, 'MI14P-512-BLACK', '小米 14 Pro 512GB 黑色', 5499.00, 50, '{"颜色":"黑色","存储":"512GB"}', 1);

-- OPPO Find X7 SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(11, 4, 'FINDX7-256', 'OPPO Find X7 256GB 海阔天空', 4599.00, 65, '{"颜色":"海阔天空","存储":"256GB"}', 1),
(12, 4, 'FINDX7-512', 'OPPO Find X7 512GB 海阔天空', 4999.00, 40, '{"颜色":"海阔天空","存储":"512GB"}', 1);

-- MacBook Pro SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(13, 5, 'MBP14-M3-18G-512G', 'MacBook Pro 14 M3 Pro 18GB/512GB 深空黑', 14999.00, 25, '{"颜色":"深空黑","内存":"18GB","硬盘":"512GB"}', 1),
(14, 5, 'MBP14-M3-36G-1TB', 'MacBook Pro 14 M3 Pro 36GB/1TB 深空黑', 19999.00, 10, '{"颜色":"深空黑","内存":"36GB","硬盘":"1TB"}', 1);

-- ThinkPad SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(15, 6, 'TPX1C-I7-16G-512G', 'ThinkPad X1 Carbon i7/16GB/512GB', 9999.00, 20, '{"颜色":"黑色","内存":"16GB","硬盘":"512GB"}', 1),
(16, 6, 'TPX1C-I7-32G-1TB', 'ThinkPad X1 Carbon i7/32GB/1TB', 11999.00, 12, '{"颜色":"黑色","内存":"32GB","硬盘":"1TB"}', 1);

-- iPad Air M2 SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(17, 8, 'IPADAIRM2-128G-WIFI', 'iPad Air M2 128GB WiFi版 蓝色', 4799.00, 40, '{"颜色":"蓝色","存储":"128GB","网络":"WiFi"}', 1),
(18, 8, 'IPADAIRM2-256G-WIFI', 'iPad Air M2 256GB WiFi版 蓝色', 5599.00, 30, '{"颜色":"蓝色","存储":"256GB","网络":"WiFi"}', 1),
(19, 8, 'IPADAIRM2-256G-CELL', 'iPad Air M2 256GB 5G版 星光色', 6999.00, 15, '{"颜色":"星光色","存储":"256GB","网络":"5G"}', 1);

-- Apple Watch Ultra 2 SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(20, 10, 'AWU2-49-ALPINE', 'Apple Watch Ultra 2 高山回环式表带 S/M', 6499.00, 10, '{"表带":"高山回环式","尺寸":"S/M"}', 1);

-- 小米手环 SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(21, 11, 'MIBAND8PRO-BLACK', '小米手环 8 Pro 黑色', 399.00, 500, '{"颜色":"黑色"}', 1),
(22, 11, 'MIBAND8PRO-GREY', '小米手环 8 Pro 灰色', 399.00, 350, '{"颜色":"灰色"}', 1);

-- 戴森吸尘器 SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(23, 14, 'DYSON-V15-STD', '戴森 V15 Detect 标准版', 4990.00, 18, '{"型号":"标准版"}', 1),
(24, 14, 'DYSON-V15-PRO', '戴森 V15 Detect 旗舰版+', 5490.00, 8, '{"型号":"旗舰版"}', 1);

-- 男装POLO SKUs (尺码)
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(25, 16, 'HLAPOLO-M-WHITE', '海澜之家商务POLO衫 M码 白色', 299.00, 200, '{"颜色":"白色","尺码":"M"}', 1),
(26, 16, 'HLAPOLO-L-BLUE', '海澜之家商务POLO衫 L码 蓝色', 299.00, 180, '{"颜色":"蓝色","尺码":"L"}', 1),
(27, 16, 'HLAPOLO-XL-BLACK', '海澜之家商务POLO衫 XL码 黑色', 299.00, 150, '{"颜色":"黑色","尺码":"XL"}', 1);

-- 连衣裙 SKUs (尺码)
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(28, 17, 'EVE-D-S', '伊芙丽碎花连衣裙 S码', 459.00, 100, '{"尺码":"S"}', 1),
(29, 17, 'EVE-D-M', '伊芙丽碎花连衣裙 M码', 459.00, 120, '{"尺码":"M"}', 1),
(30, 17, 'EVE-D-L', '伊芙丽碎花连衣裙 L码', 459.00, 80, '{"尺码":"L"}', 1);

-- 默认规格商品 (单SKU)
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(31, 7, 'MATEBOOKXPRO-DEFAULT', '华为 MateBook X Pro 默认规格', 8999.00, 15, NULL, 1),
(32, 9, 'MATEPADPRO-DEFAULT', '华为 MatePad Pro 默认规格', 3699.00, 28, NULL, 1),
(33, 12, 'MIDEAMW-DEFAULT', '美的微波炉 M3-L239C 默认规格', 599.00, 120, NULL, 1),
(34, 13, 'JOYOUNGPB-DEFAULT', '九阳破壁机 L18-P510 默认规格', 899.00, 85, NULL, 1),
(35, 15, 'ECOVACST30PRO-DEFAULT', '科沃斯 T30 PRO 默认规格', 3999.00, 32, NULL, 1),
(36, 18, 'SZS-DEFAULT', '三只松鼠坚果大礼包 默认规格', 99.00, 2000, NULL, 1),
(37, 19, 'THREEBODY-DEFAULT', '三体（全三册）默认规格', 68.00, 500, NULL, 1),
(38, 20, 'THINKINJAVA-DEFAULT', 'Java编程思想（第4版）默认规格', 89.00, 300, NULL, 1);

-- 5.6 优惠券数据
USE mall_coupon;

INSERT IGNORE INTO `coupon_template` (`id`, `template_name`, `coupon_type`, `coupon_value`, `min_amount`, `total_count`, `used_count`, `per_limit`, `start_time`, `end_time`, `status`) VALUES
(1, '新人满200减50', 1, 50.00, 200.00, 10000, 156, 1, '2025-01-01 00:00:00', '2026-12-31 23:59:59', 1),
(2, '数码满5000减300', 1, 300.00, 5000.00, 5000, 89, 1, '2025-01-01 00:00:00', '2026-12-31 23:59:59', 1),
(3, '全场9折券', 2, 9.00, 0.00, 5000, 234, 2, '2025-01-01 00:00:00', '2026-12-31 23:59:59', 1),
(4, '满1000减100', 1, 100.00, 1000.00, 2000, 412, 1, '2025-06-01 00:00:00', '2026-06-30 23:59:59', 1),
(5, '新人现金券10元', 3, 10.00, 0.00, 20000, 1024, 1, '2025-01-01 00:00:00', '2026-12-31 23:59:59', 1);

-- 给测试用户发优惠券
INSERT IGNORE INTO `user_coupon` (`id`, `user_id`, `template_id`, `coupon_code`, `status`, `order_id`, `expire_time`) VALUES
(1, 1, 1, 'UC20250101000001', 0, NULL, '2026-06-30 23:59:59'),
(2, 1, 2, 'UC20250101000002', 0, NULL, '2026-06-30 23:59:59'),
(3, 2, 1, 'UC20250101000003', 0, NULL, '2026-06-30 23:59:59'),
(4, 2, 5, 'UC20250101000004', 1, 1, '2026-06-30 23:59:59'),
(5, 3, 3, 'UC20250101000005', 0, NULL, '2026-06-30 23:59:59'),
(6, 3, 4, 'UC20250101000006', 0, NULL, '2026-06-30 23:59:59');