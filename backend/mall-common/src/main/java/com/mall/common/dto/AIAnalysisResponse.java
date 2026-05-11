package com.mall.common.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Data
public class AIAnalysisResponse {
    private Boolean success;
    private Double executionTime;
    private List<String> agentsInvolved;
    private Map<String, Object> productAnalysis;
    private Map<String, Object> priceAnalysis;
    private Map<String, Object> couponAnalysis;
    private Map<String, Object> recommendation;
    private String timestamp;
}
