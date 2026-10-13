-- ============================================
-- XiaoyuMall 商品数据扩容脚本
-- 在 init.sql 基础上补充更多分类、品牌、商品和 SKU
-- ============================================

USE mall_product;

-- ============================================
-- 1. 新增品牌 (现有 1-12，新增 13+)
-- ============================================
INSERT IGNORE INTO `brand` (`id`, `brand_name`, `logo`, `description`, `sort`, `status`) VALUES
(13, '兰蔻', 'https://picsum.photos/seed/lancome/100/100', 'Lancôme 兰蔻，法国高端护肤品牌', 13, 1),
(14, '雅诗兰黛', 'https://picsum.photos/seed/estee/100/100', 'Estée Lauder 雅诗兰黛，全球高端护肤领军品牌', 14, 1),
(15, '耐克', 'https://picsum.photos/seed/nike/100/100', 'Nike 耐克，全球运动品牌领导者', 15, 1),
(16, '阿迪达斯', 'https://picsum.photos/seed/adidas/100/100', 'Adidas 阿迪达斯，德国运动服饰品牌', 16, 1),
(17, '安踏', 'https://picsum.photos/seed/anta/100/100', '安踏体育，中国领先的运动品牌', 17, 1),
(18, '全棉时代', 'https://picsum.photos/seed/purcotton/100/100', 'Purcotton 全棉时代，全棉生活品牌', 18, 1),
(19, '罗技', 'https://picsum.photos/seed/logitech/100/100', 'Logitech 罗技，全球领先的电脑外设品牌', 19, 1),
(20, '索尼', 'https://picsum.photos/seed/sony/100/100', 'Sony 索尼，日本综合电子电器制造商', 20, 1),
(21, 'Anker', 'https://picsum.photos/seed/anker/100/100', 'Anker 安克创新，全球领先的充电配件品牌', 21, 1),
(22, '卫龙', 'https://picsum.photos/seed/weilong/100/100', '卫龙，中国辣条品类领导者', 22, 1),
(23, '良品铺子', 'https://picsum.photos/seed/lppz/100/100', '良品铺子，高端零食品牌', 23, 1),
(24, '农夫山泉', 'https://picsum.photos/seed/nongfu/100/100', '农夫山泉，天然水品牌', 24, 1);

-- ============================================
-- 2. 新增商品分类 (现有 1-18，新增 19+)
-- ============================================

-- 6 个新的一级分类
INSERT IGNORE INTO `product_category` (`id`, `parent_id`, `category_name`, `category_level`, `sort`, `status`) VALUES
(19, 0, '美妆护肤', 1, 6, 1),
(23, 0, '母婴用品', 1, 7, 1),
(27, 0, '家居家纺', 1, 8, 1),
(31, 0, '户外运动', 1, 9, 1),
(35, 0, '宠物用品', 1, 10, 1),
(38, 0, '数码配件', 1, 11, 1);

-- 美妆护肤二级分类
INSERT IGNORE INTO `product_category` (`id`, `parent_id`, `category_name`, `category_level`, `sort`, `status`) VALUES
(20, 19, '面部护肤', 2, 1, 1),
(21, 19, '彩妆', 2, 2, 1),
(22, 19, '身体护理', 2, 3, 1);

-- 母婴用品二级分类
INSERT IGNORE INTO `product_category` (`id`, `parent_id`, `category_name`, `category_level`, `sort`, `status`) VALUES
(24, 23, '婴儿喂养', 2, 1, 1),
(25, 23, '婴儿用品', 2, 2, 1),
(26, 23, '孕妇用品', 2, 3, 1);

-- 家居家纺二级分类
INSERT IGNORE INTO `product_category` (`id`, `parent_id`, `category_name`, `category_level`, `sort`, `status`) VALUES
(28, 27, '床上用品', 2, 1, 1),
(29, 27, '厨房用品', 2, 2, 1),
(30, 27, '收纳整理', 2, 3, 1);

-- 户外运动二级分类
INSERT IGNORE INTO `product_category` (`id`, `parent_id`, `category_name`, `category_level`, `sort`, `status`) VALUES
(32, 31, '户外装备', 2, 1, 1),
(33, 31, '运动鞋服', 2, 2, 1);

-- 宠物用品二级分类
INSERT IGNORE INTO `product_category` (`id`, `parent_id`, `category_name`, `category_level`, `sort`, `status`) VALUES
(36, 35, '宠物食品', 2, 1, 1),
(37, 35, '宠物玩具', 2, 2, 1);

-- 数码配件二级分类
INSERT IGNORE INTO `product_category` (`id`, `parent_id`, `category_name`, `category_level`, `sort`, `status`) VALUES
(39, 38, '充电设备', 2, 1, 1),
(40, 38, '耳机音响', 2, 2, 1),
(41, 38, '键鼠外设', 2, 3, 1);

-- ============================================
-- 3. 新增商品 (现有 1-20，新增 21+)
-- ============================================

-- 手机类补充
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(21, '红米 K70 Pro', 2, 3, 'REDMIK70P001', 3299.00, 3699.00, '红米 K70 Pro 12+256GB，骁龙8Gen3，2K 120Hz屏，5000mAh大电池', 'https://picsum.photos/seed/redmik70/400/400', 1, 5, 892),
(22, 'vivo X100 Pro', 2, NULL, 'VIVOX100P001', 5999.00, 6499.00, 'vivo X100 Pro 12+256GB，天玑9300，蔡司影像，APO超级长焦', 'https://picsum.photos/seed/vivox100/400/400', 1, 6, 456);

-- 电脑类补充
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(23, '戴尔 XPS 15', 3, NULL, 'DELLEXPS15001', 13999.00, 15999.00, '戴尔 XPS 15 2024款，i9-13900H/32GB/1TB/RTX4060，3.5K OLED', 'https://picsum.photos/seed/dellxps15/400/400', 1, 4, 78),
(24, '华硕 ROG 魔霸新锐', 3, NULL, 'ROGMOBILE001', 9999.00, 11499.00, 'ROG 魔霸新锐 2024，i9-14900HX/16GB/1TB/RTX4060，240Hz电竞屏', 'https://picsum.photos/seed/rogmobile/400/400', 1, 5, 123);

-- 平板类补充
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(25, '小米平板 6S Pro', 4, 3, 'MIPAD6SP001', 3299.00, 3799.00, '小米平板 6S Pro 12.4英寸，3K 120Hz屏，骁龙8Gen2，双向卫星通信', 'https://picsum.photos/seed/mipad6s/400/400', 1, 3, 345);

-- 智能穿戴补充
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(26, '华为 Watch GT4', 5, 2, 'HWGT4001', 1588.00, 1788.00, '华为 WATCH GT4，跑步健康，科学运动减脂，14天超长续航', 'https://picsum.photos/seed/hwgt4/400/400', 1, 3, 567),
(27, 'OPPO Watch 4 Pro', 5, 4, 'OPWOW4P001', 1899.00, 2199.00, 'OPPO Watch 4 Pro，双芯长续航，健康监测，eSIM独立通话', 'https://picsum.photos/seed/opwow4p/400/400', 1, 4, 234);

-- 厨房电器补充
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(28, '苏泊尔电饭煲 SF40HC88', 7, NULL, 'SUPORFBSF40001', 699.00, 899.00, '苏泊尔球釜IH电饭煲 4L，IH电磁加热，球釜内胆，智能预约', 'https://picsum.photos/seed/supor/400/400', 1, 3, 1234),
(29, '小熊空气炸锅 QZG-E16A5', 7, NULL, 'BEARAF20001', 399.00, 599.00, '小熊空气炸锅 5L，无油健康，智能触控，可视窗口', 'https://picsum.photos/seed/bear/400/400', 1, 4, 2345);

-- 生活电器补充
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(30, '美的空调酷省电 KFR-35GW', 8, 6, 'MIDEAAC001', 2999.00, 3599.00, '美的酷省电 1.5匹新一级能效，酷省电动能，智能控温，静音运行', 'https://picsum.photos/seed/mideaac/400/400', 1, 3, 567),
(31, '飞利浦电动牙刷 HX9393', 8, NULL, 'PHILIPSTB001', 899.00, 1299.00, '飞利浦声波电动牙刷，智能感应刷头，多种清洁模式，APP互联', 'https://picsum.photos/seed/philipstb/400/400', 1, 4, 890);

-- 男装补充
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(32, '优衣库纯棉圆领T恤', 10, NULL, 'UNIQLOT001', 99.00, 149.00, '优衣库男士纯棉圆领T恤，100%纯棉，舒适透气，多色可选', 'https://picsum.photos/seed/uniqlot/400/400', 1, 2, 3456),
(33, '李宁加绒运动卫衣', 10, NULL, 'LININGHD001', 299.00, 399.00, '李宁男士加绒运动卫衣，摇粒绒内里，保暖舒适，潮流百搭', 'https://picsum.photos/seed/lininghd/400/400', 1, 3, 789);

-- 女装补充
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(34, 'ZARA 针织开衫外套', 11, NULL, 'ZARAKT001', 399.00, 599.00, 'ZARA 女士针织开衫，柔软针织面料，宽松版型，通勤百搭', 'https://picsum.photos/seed/zarakt/400/400', 1, 2, 567),
(35, '太平鸟过膝羽绒服', 11, NULL, 'PEACEBIRD001', 899.00, 1299.00, '太平鸟女士过膝羽绒服，90%白鸭绒，保暖时尚，修身显瘦', 'https://picsum.photos/seed/peacebird/400/400', 1, 3, 432);

-- 运动服饰 (category_id=12)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(36, '耐克 Air Max 270 运动鞋', 12, 15, 'NIKEAM270001', 899.00, 1099.00, 'Nike Air Max 270 全掌气垫运动鞋，270度可视气垫，缓震舒适', 'https://picsum.photos/seed/nikemax270/400/400', 1, 1, 1567),
(37, '阿迪达斯 Ultraboost 跑鞋', 12, 16, 'ADIDASUB001', 1199.00, 1399.00, 'Adidas Ultraboost 22 跑步鞋，Boost中底科技，极致缓震回弹', 'https://picsum.photos/seed/adidasub/400/400', 1, 2, 890),
(38, '安踏运动短裤', 12, 17, 'ANTASHORT001', 129.00, 179.00, '安踏男士运动短裤，速干透气面料，宽松版型，跑步健身必备', 'https://picsum.photos/seed/antashort/400/400', 1, 3, 2345);

-- 水果 (category_id=14)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(39, '智利车厘子 J级 2斤装', 14, NULL, 'CHILECHERRY01', 199.00, 299.00, '智利进口车厘子 J级 28-30mm，JJ级高品质，甜蜜多汁，顺丰冷链', 'https://picsum.photos/seed/cherry/400/400', 1, 1, 3456),
(40, '云南沃柑 5斤装', 14, NULL, 'YUNNANWG001', 49.00, 79.00, '云南高原沃柑，皮薄汁多，甜度15+，当季新鲜采摘', 'https://picsum.photos/seed/wogan/400/400', 1, 2, 5678),
(41, '新疆阿克苏苹果 5斤', 14, NULL, 'AKESUAP001', 89.00, 129.00, '新疆阿克苏冰糖心苹果，果心透亮，脆甜多汁，高山种植', 'https://picsum.photos/seed/akesu/400/400', 1, 3, 2345),
(42, '海南金煌芒果 3斤', 14, NULL, 'HAINANMG001', 69.00, 99.00, '海南金煌芒果，单果400-600g，果肉细腻无丝，香甜可口', 'https://picsum.photos/seed/mango/400/400', 1, 4, 1234);

-- 零食补充
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(43, '良品铺子每日坚果 750g', 15, 23, 'LPPZNUTS001', 129.00, 179.00, '良品铺子每日坚果礼盒 750g，30小包独立包装，8种坚果果干', 'https://picsum.photos/seed/lppznuts/400/400', 1, 2, 4567),
(44, '卫龙辣条大礼包', 15, 22, 'WEILONG001', 39.90, 59.90, '卫龙辣条大礼包 66包，经典辣条组合，儿时回忆，办公室零食', 'https://picsum.photos/seed/weilong/400/400', 1, 3, 8901),
(45, '乐事薯片大礼包 10包', 15, NULL, 'LAYS001', 49.90, 69.90, '乐事薯片混合口味大礼包 10包，原味/黄瓜/番茄/烧烤多口味', 'https://picsum.photos/seed/lays/400/400', 1, 4, 5678);

-- 美妆护肤 - 面部护肤 (category_id=20)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(46, '兰蔻小黑瓶精华 50ml', 20, 13, 'LANCOMEJS001', 1080.00, 1380.00, '兰蔻小黑瓶肌底修护精华液 50ml，修护肌肤屏障，改善肤质', 'https://picsum.photos/seed/lancomejs/400/400', 1, 1, 890),
(47, '雅诗兰黛小棕瓶精华 50ml', 20, 14, 'ESTEELAUDER01', 950.00, 1250.00, '雅诗兰黛第七代小棕瓶精华 50ml，修护抗老，弹润紧致', 'https://picsum.photos/seed/elady01/400/400', 1, 2, 678),
(48, '薇诺娜舒敏保湿特护霜', 20, NULL, 'WINONA001', 299.00, 399.00, '薇诺娜舒敏保湿特护霜 50g，敏感肌专用，舒缓泛红，补水保湿', 'https://picsum.photos/seed/winona/400/400', 1, 3, 2345);

-- 美妆护肤 - 彩妆 (category_id=21)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(49, 'MAC子弹头口红 Chili', 21, NULL, 'MACCHILI001', 220.00, 260.00, 'MAC经典子弹头口红 Chili 602号色，枫叶红棕色，百搭必入', 'https://picsum.photos/seed/macchili/400/400', 1, 1, 3456),
(50, 'YSL圣罗兰丝绒唇釉', 21, NULL, 'YSLVL001', 320.00, 380.00, 'YSL圣罗兰丝绒唇釉，轻薄丝绒质地，显色持久，不拔干', 'https://picsum.photos/seed/yslvl/400/400', 1, 2, 1234);

-- 母婴用品 - 婴儿喂养 (category_id=24)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(51, '惠氏启赋蓝钻奶粉 3段', 24, NULL, 'WYETHQX001', 368.00, 458.00, '惠氏启赋蓝钻 3段奶粉 900g，12-36个月婴幼儿，OPN活性蛋白', 'https://picsum.photos/seed/wyeth/400/400', 1, 1, 1234),
(52, '贝亲宽口径玻璃奶瓶', 24, NULL, 'PIGEON001', 189.00, 259.00, '贝亲宽口径玻璃奶瓶 240ml，自然实感奶嘴，防胀气设计', 'https://picsum.photos/seed/pigeon/400/400', 1, 2, 2345);

-- 母婴用品 - 婴儿用品 (category_id=25)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(53, '帮宝适黑金帮纸尿裤 M码', 25, NULL, 'PAMPERSBK01', 168.00, 228.00, '帮宝适黑金帮纸尿裤 M码 54片，蚕丝质感，超薄透气', 'https://picsum.photos/seed/pampers/400/400', 1, 1, 3456),
(54, '全棉时代婴儿湿巾', 25, 18, 'PURCOTTONWS01', 79.00, 119.00, '全棉时代婴儿纯棉湿巾 80抽×6包，纯水配方，温和不刺激', 'https://picsum.photos/seed/purcottonws/400/400', 1, 2, 5678);

-- 家居家纺 - 床上用品 (category_id=28)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(55, '罗莱家纺纯棉四件套', 28, NULL, 'LUOLAI001', 499.00, 799.00, '罗莱家纺 全棉斜纹四件套 1.8m床，亲肤舒适，活性印染', 'https://picsum.photos/seed/luolai/400/400', 1, 1, 890),
(56, '北极绒羽绒被冬被', 28, NULL, 'BEIJIRONGR001', 799.00, 1299.00, '北极绒 90%白鹅绒羽绒被 200×230cm，蓬松保暖，轻盈舒适', 'https://picsum.photos/seed/beijirong/400/400', 1, 2, 456);

-- 家居家纺 - 厨房用品 (category_id=29)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(57, '双立人不锈钢刀具套装', 29, NULL, 'ZWILLING001', 599.00, 899.00, '双立人不锈钢刀具套装 5件套，德国工艺，锋利耐用', 'https://picsum.photos/seed/zwilling/400/400', 1, 1, 567);

-- 家居家纺 - 收纳整理 (category_id=30)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(58, '太力真空压缩袋 6件套', 30, NULL, 'TAILI001', 129.00, 199.00, '太力真空压缩袋 6件套，免抽气设计，收纳被子衣物节省空间', 'https://picsum.photos/seed/taili/400/400', 1, 1, 2345);

-- 户外运动 - 户外装备 (category_id=32)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(59, '探路者登山鞋徒步鞋', 32, NULL, 'TOREAD001', 599.00, 899.00, '探路者户外登山鞋，防水透气，Vibram大底，专业徒步装备', 'https://picsum.photos/seed/toread/400/400', 1, 1, 456),
(60, '迪卡侬露营帐篷 2人', 32, NULL, 'DECATHLON01', 499.00, 699.00, '迪卡侬户外露营帐篷 2人双层，快速搭建，防水防风', 'https://picsum.photos/seed/decathlon/400/400', 1, 2, 789);

-- 户外运动 - 运动鞋服 (category_id=33)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(61, '哥伦比亚三合一冲锋衣', 33, NULL, 'COLUMBIA01', 1199.00, 1699.00, '哥伦比亚三合一冲锋衣，Omni-Shield防泼水，抓绒内胆可拆卸', 'https://picsum.photos/seed/columbia/400/400', 1, 1, 234);

-- 宠物用品 - 宠物食品 (category_id=36)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(62, '皇家成猫专用粮 2kg', 36, NULL, 'ROYALCANIN01', 168.00, 228.00, '皇家Royal Canin成猫专用粮 2kg，营养均衡，口腔健康配方', 'https://picsum.photos/seed/royalcanin/400/400', 1, 1, 1234),
(63, '麦富迪幼犬狗粮 10kg', 36, NULL, 'MYFOODIE001', 299.00, 399.00, '麦富迪牛肉双拼幼犬狗粮 10kg，高蛋白营养，健壮骨骼', 'https://picsum.photos/seed/myfoodie/400/400', 1, 2, 2345);

-- 宠物用品 - 宠物玩具 (category_id=37)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(64, '耐咬狗咬胶玩具', 37, NULL, 'DOGTOY001', 49.00, 79.00, '狗狗耐咬磨牙棒玩具，橡胶材质，清洁牙齿，消磨精力', 'https://picsum.photos/seed/dogtoy/400/400', 1, 1, 5678),
(65, '猫薄荷逗猫棒套装', 37, NULL, 'CATTOY001', 29.00, 49.00, '逗猫棒套装 3支装，含猫薄荷，羽毛铃铛，逗猫神器', 'https://picsum.photos/seed/cattoy/400/400', 1, 2, 8901);

-- 数码配件 - 充电设备 (category_id=39)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(66, 'Anker 737 充电宝 24000mAh', 39, 21, 'ANKER737001', 499.00, 649.00, 'Anker 737 移动电源 24000mAh，140W快充，三设备同时充', 'https://picsum.photos/seed/anker737/400/400', 1, 1, 1234),
(67, '小米 GaN 氮化镓充电器 65W', 39, 3, 'MIGAN65001', 129.00, 169.00, '小米 GaN 氮化镓充电器 65W，小巧便携，笔记本手机通用', 'https://picsum.photos/seed/migan65/400/400', 1, 2, 3456);

-- 数码配件 - 耳机音响 (category_id=40)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(68, 'AirPods Pro 第二代', 40, 1, 'AIRPODSPRO201', 1899.00, 1999.00, 'Apple AirPods Pro 第二代，主动降噪，自适应通透模式，USB-C', 'https://picsum.photos/seed/airpodspro2/400/400', 1, 1, 2345),
(69, '索尼 WH-1000XM5 头戴式耳机', 40, 20, 'SONYWH1000XM5', 2499.00, 2899.00, '索尼 WH-1000XM5 无线降噪头戴式耳机，行业领先降噪，30小时续航', 'https://picsum.photos/seed/sonywh1000xm5/400/400', 1, 2, 567),
(70, 'JBL Flip 6 蓝牙音箱', 40, NULL, 'JBLFLIP6001', 899.00, 1199.00, 'JBL Flip 6 蓝牙便携音箱，IP67防水防尘，12小时续航', 'https://picsum.photos/seed/jblflip6/400/400', 1, 3, 1234);

-- 数码配件 - 键鼠外设 (category_id=41)
INSERT IGNORE INTO `product` (`id`, `product_name`, `category_id`, `brand_id`, `product_code`, `price`, `original_price`, `description`, `main_image`, `status`, `sort`, `sales`) VALUES
(71, '罗技 MX Master 3S 无线鼠标', 41, 19, 'LOGIMXM3S001', 699.00, 799.00, '罗技 MX Master 3S 无线办公鼠标，8K DPI静音点击，多设备切换', 'https://picsum.photos/seed/logimx3s/400/400', 1, 1, 1567),
(72, 'HHKB Professional Hybrid 静电容键盘', 41, NULL, 'HHKBHYBRID01', 2180.00, 2480.00, 'HHKB Professional Hybrid 蓝牙静电容键盘，45g按键，程序员神器', 'https://picsum.photos/seed/hhkb/400/400', 1, 2, 234);

-- ============================================
-- 4. 新增 SKU (现有 1-38，新增 39+)
-- ============================================

-- 红米 K70 Pro SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(39, 21, 'REDMIK70P-12-256', '红米 K70 Pro 12+256GB 墨羽黑', 3299.00, 80, '{"颜色":"墨羽黑","存储":"12+256GB"}', 1),
(40, 21, 'REDMIK70P-12-512', '红米 K70 Pro 12+512GB 墨羽黑', 3599.00, 50, '{"颜色":"墨羽黑","存储":"12+512GB"}', 1),
(41, 21, 'REDMIK70P-16-512', '红米 K70 Pro 16+512GB 雪影白', 3899.00, 30, '{"颜色":"雪影白","存储":"16+512GB"}', 1);

-- vivo X100 Pro SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(42, 22, 'VIVOX100P-12-256', 'vivo X100 Pro 12+256GB 星迹蓝', 5999.00, 45, '{"颜色":"星迹蓝","存储":"12+256GB"}', 1),
(43, 22, 'VIVOX100P-16-512', 'vivo X100 Pro 16+512GB 落日橙', 6999.00, 25, '{"颜色":"落日橙","存储":"16+512GB"}', 1);

-- 小米平板 6S Pro SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(44, 25, 'MIPAD6SP-8-256', '小米平板 6S Pro 8+256GB 黑色', 3299.00, 35, '{"颜色":"黑色","存储":"8+256GB"}', 1),
(45, 25, 'MIPAD6SP-12-512', '小米平板 6S Pro 12+512GB 银色', 3999.00, 20, '{"颜色":"银色","存储":"12+512GB"}', 1);

-- 华为 Watch GT4 SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(46, 26, 'HWGT4-46MM-BLACK', '华为 Watch GT4 46mm 曜石黑', 1588.00, 50, '{"颜色":"曜石黑","尺寸":"46mm"}', 1),
(47, 26, 'HWGT4-42MM-GOLD', '华为 Watch GT4 42mm 皓月金', 1588.00, 40, '{"颜色":"皓月金","尺寸":"42mm"}', 1);

-- 男装 SKUs (尺码)
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(48, 32, 'UNIQLOT-M-WHITE', '优衣库纯棉T恤 M码 白色', 99.00, 500, '{"颜色":"白色","尺码":"M"}', 1),
(49, 32, 'UNIQLOT-L-GRAY', '优衣库纯棉T恤 L码 灰色', 99.00, 450, '{"颜色":"灰色","尺码":"L"}', 1),
(50, 32, 'UNIQLOT-XL-BLACK', '优衣库纯棉T恤 XL码 黑色', 99.00, 400, '{"颜色":"黑色","尺码":"XL"}', 1),
(51, 33, 'LININGHD-L-NAVY', '李宁加绒卫衣 L码 藏青色', 299.00, 200, '{"颜色":"藏青色","尺码":"L"}', 1),
(52, 33, 'LININGHD-XL-GRAY', '李宁加绒卫衣 XL码 花灰色', 299.00, 180, '{"颜色":"花灰色","尺码":"XL"}', 1);

-- 女装 SKUs (尺码)
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(53, 34, 'ZARAKT-S-BEIGE', 'ZARA针织开衫 S码 米色', 399.00, 120, '{"颜色":"米色","尺码":"S"}', 1),
(54, 34, 'ZARAKT-M-BLACK', 'ZARA针织开衫 M码 黑色', 399.00, 150, '{"颜色":"黑色","尺码":"M"}', 1),
(55, 35, 'PEACEBIRD-M-WHITE', '太平鸟羽绒服 M码 奶白色', 899.00, 80, '{"颜色":"奶白色","尺码":"M"}', 1),
(56, 35, 'PEACEBIRD-L-BLACK', '太平鸟羽绒服 L码 黑色', 899.00, 100, '{"颜色":"黑色","尺码":"L"}', 1);

-- 运动服饰 SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(57, 36, 'NIKEAM270-42-WHITE', 'Nike Air Max 270 42码 白色', 899.00, 80, '{"颜色":"白色","尺码":"42"}', 1),
(58, 36, 'NIKEAM270-43-BLACK', 'Nike Air Max 270 43码 黑色', 899.00, 60, '{"颜色":"黑色","尺码":"43"}', 1),
(59, 37, 'ADIDASUB-42-WHITE', 'Adidas Ultraboost 42码 白色', 1199.00, 50, '{"颜色":"白色","尺码":"42"}', 1),
(60, 37, 'ADIDASUB-43-BLACK', 'Adidas Ultraboost 43码 黑色', 1199.00, 40, '{"颜色":"黑色","尺码":"43"}', 1),
(61, 38, 'ANTASHORT-M-NAVY', '安踏运动短裤 M码 藏青色', 129.00, 300, '{"颜色":"藏青色","尺码":"M"}', 1),
(62, 38, 'ANTASHORT-L-BLACK', '安踏运动短裤 L码 黑色', 129.00, 280, '{"颜色":"黑色","尺码":"L"}', 1);

-- 水果默认规格
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(63, 39, 'CHERRY-J-2J', '智利车厘子 J级 2斤装 默认规格', 199.00, 500, NULL, 1),
(64, 40, 'WG-YUNNAN-5J', '云南沃柑 5斤装 默认规格', 49.00, 2000, NULL, 1),
(65, 41, 'AKESU-5J', '新疆阿克苏苹果 5斤 默认规格', 89.00, 800, NULL, 1),
(66, 42, 'MG-HN-3J', '海南金煌芒果 3斤 默认规格', 69.00, 600, NULL, 1);

-- 美妆护肤 SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(67, 46, 'LANCOMEJS-50ML', '兰蔻小黑瓶 50ml 默认规格', 1080.00, 80, NULL, 1),
(68, 46, 'LANCOMEJS-100ML', '兰蔻小黑瓶 100ml 默认规格', 1680.00, 30, NULL, 1),
(69, 47, 'ESTEE-50ML', '雅诗兰黛小棕瓶 50ml 默认规格', 950.00, 60, NULL, 1),
(70, 48, 'WINONA-50G', '薇诺娜特护霜 50g 默认规格', 299.00, 300, NULL, 1),
(71, 49, 'MAC-CHILI-602', 'MAC子弹头 Chili 602 默认规格', 220.00, 500, NULL, 1),
(72, 50, 'YSLVL-211', 'YSL丝绒唇釉 211号 默认规格', 320.00, 200, NULL, 1);

-- 母婴用品默认规格
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(73, 51, 'WYETHQ-3-900G', '惠氏启赋蓝钻 3段 900g 默认规格', 368.00, 500, NULL, 1),
(74, 52, 'PIGEON-240ML', '贝亲宽口径奶瓶 240ml 默认规格', 189.00, 400, NULL, 1),
(75, 53, 'PAMPERS-M-54P', '帮宝适黑金帮 M码 54片 默认规格', 168.00, 800, NULL, 1),
(76, 54, 'PURCOTTON-6P', '全棉时代湿巾 80抽×6包 默认规格', 79.00, 1500, NULL, 1);

-- 家居家纺默认规格
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(77, 55, 'LUOLAI-1.8M', '罗莱四件套 1.8m床 默认规格', 499.00, 200, NULL, 1),
(78, 56, 'BR-200230', '北极绒羽绒被 200×230cm 默认规格', 799.00, 100, NULL, 1),
(79, 57, 'ZWILLING-5SET', '双立人刀具 5件套 默认规格', 599.00, 150, NULL, 1),
(80, 58, 'TAILI-6SET', '太力真空压缩袋 6件套 默认规格', 129.00, 600, NULL, 1);

-- 户外运动默认规格
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(81, 59, 'TOREAD-HK-42', '探路者登山鞋 42码 默认规格', 599.00, 120, NULL, 1),
(82, 60, 'DECATHLON-2P', '迪卡侬帐篷 2人 默认规格', 499.00, 80, NULL, 1),
(83, 61, 'COLUMBIA-M', '哥伦比亚冲锋衣 M码 默认规格', 1199.00, 60, NULL, 1);

-- 宠物用品默认规格
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(84, 62, 'RC-CAT-2KG', '皇家成猫粮 2kg 默认规格', 168.00, 400, NULL, 1),
(85, 63, 'MYFOODIE-10KG', '麦富迪幼犬粮 10kg 默认规格', 299.00, 200, NULL, 1),
(86, 64, 'DOGTOY-DEFAULT', '耐咬狗咬胶 默认规格', 49.00, 1000, NULL, 1),
(87, 65, 'CATTOY-3SET', '逗猫棒 3支装 默认规格', 29.00, 1500, NULL, 1);

-- 数码配件 SKUs
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(88, 66, 'ANKER737-24K', 'Anker 737 24000mAh 默认规格', 499.00, 200, NULL, 1),
(89, 67, 'MIGAN-65W', '小米GaN 65W 默认规格', 129.00, 800, NULL, 1),
(90, 68, 'AIRPODSP2-USB', 'AirPods Pro 2 USB-C 默认规格', 1899.00, 300, NULL, 1),
(91, 69, 'SONY-WH1000XM5', '索尼WH-1000XM5 默认规格', 2499.00, 100, NULL, 1),
(92, 70, 'JBLFLIP6-BLUE', 'JBL Flip 6 蓝色 默认规格', 899.00, 250, NULL, 1),
(93, 71, 'LOGI-MX3S-BLACK', '罗技 MX Master 3S 黑色 默认规格', 699.00, 180, NULL, 1),
(94, 72, 'HHKB-HYBRID-ING', 'HHKB Hybrid 英文版 默认规格', 2180.00, 40, NULL, 1);

-- 剩余新增商品的默认 SKU (无多规格需求)
INSERT IGNORE INTO `product_sku` (`id`, `product_id`, `sku_code`, `sku_name`, `price`, `stock`, `specs`, `status`) VALUES
(95, 23, 'DELLXPS15-DEFAULT', '戴尔 XPS 15 默认规格', 13999.00, 15, NULL, 1),
(96, 24, 'ROGMOBILE-DEFAULT', 'ROG 魔霸新锐 默认规格', 9999.00, 25, NULL, 1),
(97, 27, 'OPWOW4P-DEFAULT', 'OPPO Watch 4 Pro 默认规格', 1899.00, 30, NULL, 1),
(98, 28, 'SUPOR-FB-DEFAULT', '苏泊尔电饭煲 默认规格', 699.00, 200, NULL, 1),
(99, 29, 'BEAR-AF-DEFAULT', '小熊空气炸锅 默认规格', 399.00, 350, NULL, 1),
(100, 30, 'MIDEA-AC-DEFAULT', '美的空调酷省电 默认规格', 2999.00, 80, NULL, 1),
(101, 31, 'PHILIPS-TB-DEFAULT', '飞利浦电动牙刷 默认规格', 899.00, 150, NULL, 1),
(102, 43, 'LPPZ-NUTS-DEFAULT', '良品铺子每日坚果 默认规格', 129.00, 800, NULL, 1),
(103, 44, 'WEILONG-BIG-DEFAULT', '卫龙辣条大礼包 默认规格', 39.90, 2000, NULL, 1),
(104, 45, 'LAYS-10P-DEFAULT', '乐事薯片10包 默认规格', 49.90, 1500, NULL, 1);
