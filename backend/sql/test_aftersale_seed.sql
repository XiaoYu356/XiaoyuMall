-- 售后/物流功能的测试种子（用户 1710）
-- 用法：docker exec -i mysql mysql -uroot -proot mall_order < sql/test_aftersale_seed.sql
-- 幂等：每次先清理本种子产生的订单与售后单，再重新插入
USE mall_order;

DELETE FROM `order_item` WHERE order_no IN ('ORDTEST1710A1', 'ORDTEST1710B1');
DELETE FROM `aftersale_order` WHERE order_no IN ('ORDTEST1710A1', 'ORDTEST1710B1');
DELETE FROM `order` WHERE order_no IN ('ORDTEST1710A1', 'ORDTEST1710B1');

-- 已发货订单：用于物流轨迹 + 退货退款演示
INSERT INTO `order` (order_no, user_id, total_amount, pay_amount, discount_amount,
                     status, receiver_name, receiver_phone, receiver_address,
                     payment_time, delivery_time)
VALUES ('ORDTEST1710A1', 1710, 4999.00, 4999.00, 0.00,
        2, '测试用户', '13800101710', '上海市浦东新区测试路1号',
        DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY));

INSERT INTO `order_item` (order_id, order_no, product_id, sku_id, product_name,
                          sku_name, sku_code, price, quantity, total_amount, product_image)
SELECT id, order_no, 1, 1, '小米 14 Pro', '小米14 Pro 256GB 黑色',
       'XM14PRO-256', 4999.00, 1, 4999.00, NULL
FROM `order` WHERE order_no = 'ORDTEST1710A1';

-- 已支付待发货订单：用于仅退款演示
INSERT INTO `order` (order_no, user_id, total_amount, pay_amount, discount_amount,
                     status, receiver_name, receiver_phone, receiver_address,
                     payment_time, delivery_time)
VALUES ('ORDTEST1710B1', 1710, 99.00, 99.00, 0.00,
        1, '测试用户', '13800101710', '上海市浦东新区测试路1号',
        DATE_SUB(NOW(), INTERVAL 1 HOUR), NULL);
