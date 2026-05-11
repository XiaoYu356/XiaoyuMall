package com.mall.common.dto;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class AIAnalysisRequest {
    private String productId;
    private String userId;
    private String userQuery;
}
