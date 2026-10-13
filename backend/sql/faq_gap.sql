-- FAQ 知识库缺口信号表（数据飞轮：检索失败 query 持久化供运营补知识）
USE mall_order;

CREATE TABLE IF NOT EXISTS `faq_gap` (
  `id` bigint AUTO_INCREMENT PRIMARY KEY,
  `query` varchar(255) NOT NULL COMMENT '触发缺口的用户 query',
  `gap_type` tinyint NOT NULL COMMENT '1=all_killed(全剔除) 2=gray_killed(灰区剔除)',
  `detail` json DEFAULT NULL COMMENT '附加上下文(rrf_top1/score/top候选等)',
  `hit_count` int NOT NULL DEFAULT 1 COMMENT '同类 query 累计触发次数',
  `status` tinyint NOT NULL DEFAULT 0 COMMENT '0=待处理 1=已补知识 2=已忽略',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_query` (`query`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='FAQ知识库缺口信号表';
