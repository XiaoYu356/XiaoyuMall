-- 创建用户数据库
CREATE DATABASE IF NOT EXISTS mall_user DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mall_user;

-- 用户表
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

-- 用户地址表
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
  `deleted` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户地址表';

-- 创建商品数据库
CREATE DATABASE IF NOT EXISTS mall_product DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mall_product;

-- 商品表
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

-- 商品SKU表
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

-- 商品分类表
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

-- 创建优惠券数据库
CREATE DATABASE IF NOT EXISTS mall_coupon DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mall_coupon;

-- 优惠券模板表
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

-- 用户优惠券表
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

-- 创建订单数据库
CREATE DATABASE IF NOT EXISTS mall_order DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE mall_order;

-- 订单表
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

-- 订单明细表
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

-- 购物车表
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

-- 插入测试数据
USE mall_user;
-- 密码为 123456 的BCrypt加密值
INSERT IGNORE INTO `user` (`username`, `password`, `nickname`, `phone`, `status`, `level`) 
VALUES ('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EH', '管理员', '13800138000', 1, 5);

USE mall_product;
INSERT IGNORE INTO `product_category` (`parent_id`, `category_name`, `category_level`, `sort`, `status`) 
VALUES (0, '数码产品', 1, 1, 1);

INSERT IGNORE INTO `product` (`product_name`, `category_id`, `product_code`, `price`, `original_price`, `status`, `sort`) 
VALUES ('iPhone 15 Pro', 1, 'IPHONE15PRO001', 7999.00, 8999.00, 1, 1);

INSERT IGNORE INTO `product_sku` (`product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) 
VALUES (1, 'SKU-IPHONE15PRO-256-BLACK', 'iPhone 15 Pro 256GB 黑色', 7999.00, 100, '{"颜色":"黑色","存储":"256GB"}', 1);

INSERT IGNORE INTO `product_sku` (`product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) 
VALUES (1, 'SKU-IPHONE15PRO-256-WHITE', 'iPhone 15 Pro 256GB 白色', 7999.00, 100, '{"颜色":"白色","存储":"256GB"}', 1);

INSERT IGNORE INTO `product_sku` (`product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) 
VALUES (1, 'SKU-IPHONE15PRO-512-BLACK', 'iPhone 15 Pro 512GB 黑色', 9999.00, 50, '{"颜色":"黑色","存储":"512GB"}', 1);

-- 执行权限初始化SQL
SOURCE permission.sql;
