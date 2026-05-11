package com.mall.product.controller;

import cn.dev33.satoken.annotation.SaCheckPermission;
import com.mall.common.dto.AIAnalysisRequest;
import com.mall.common.dto.AIAnalysisResponse;
import com.mall.common.result.Result;
import com.mall.product.feign.AIServiceClient;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/v1/ai")
@Tag(name = "AI智能助手", description = "AI智能分析、推荐等接口")
public class AIController {
    
    @Autowired
    private AIServiceClient aiServiceClient;
    
    @PostMapping("/analyze")
    @Operation(summary = "AI完整分析")
    @SaCheckPermission("ai:analyze")
    public Result<AIAnalysisResponse> analyzeProduct(@RequestBody AIAnalysisRequest request) {
        AIAnalysisResponse response = aiServiceClient.analyzeProduct(request);
        return Result.success(response);
    }
    
    @PostMapping("/analyze/product")
    @Operation(summary = "AI商品分析")
    @SaCheckPermission("ai:analyze")
    public Result quickAnalysis(@RequestBody AIAnalysisRequest request) {
        return aiServiceClient.quickAnalysis(request);
    }
    
    @PostMapping("/analyze/price")
    @Operation(summary = "AI价格分析")
    @SaCheckPermission("ai:analyze")
    public Result priceAnalysis(@RequestBody AIAnalysisRequest request) {
        return aiServiceClient.priceAnalysis(request);
    }
    
    @PostMapping("/analyze/coupon")
    @Operation(summary = "AI优惠券分析")
    @SaCheckPermission("ai:analyze")
    public Result couponAnalysis(@RequestBody AIAnalysisRequest request) {
        return aiServiceClient.couponAnalysis(request);
    }
}
