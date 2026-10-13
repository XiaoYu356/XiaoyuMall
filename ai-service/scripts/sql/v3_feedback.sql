-- v3 新增：用户反馈表（评估闭环的数据源，见设计文档 §9）
-- request_id = 该次对话的 trace_id，可跳转 Langfuse 回放
CREATE TABLE ai_chat_feedback (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  request_id VARCHAR(64) NOT NULL,        -- = trace_id，可跳 Langfuse
  user_id BIGINT NOT NULL,
  session_id VARCHAR(64) NOT NULL,
  rating TINYINT NOT NULL,                -- 1=赞 0=贬
  comment VARCHAR(500),
  shortcut_hit TINYINT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_user (user_id), KEY idx_request (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
