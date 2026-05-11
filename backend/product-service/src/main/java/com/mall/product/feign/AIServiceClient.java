package com.mall.product.feign;

import com.mall.common.dto.AIAnalysisRequest;
import com.mall.common.dto.AIAnalysisResponse;
import com.mall.common.result.Result;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

@FeignClient(name = "ai-service", url = "${ai.service.url:http://localhost:8000}")
public interface AIServiceClient {
    
    @PostMapping("/api/v1/ai/analyze")
    AIAnalysisResponse analyzeProduct(@RequestBody AIAnalysisRequest request);
    
    @PostMapping("/api/v1/ai/analyze/product")
    Result quickAnalysis(@RequestBody AIAnalysisRequest request);
    
    @PostMapping("/api/v1/ai/analyze/price")
    Result priceAnalysis(@RequestBody AIAnalysisRequest request);
    
    @PostMapping("/api/v1/ai/analyze/coupon")
    Result couponAnalysis(@RequestBody AIAnalysisRequest request);
}
