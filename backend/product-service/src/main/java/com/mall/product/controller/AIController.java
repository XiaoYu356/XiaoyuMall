package com.mall.product.controller;

import cn.dev33.satoken.stp.StpUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

@Slf4j
@RestController
@RequestMapping("/api/v1/ai")
@Tag(name = "AI智能助手", description = "AI智能对话代理（v3，透传 ai-service）")
public class AIController {

    @Value("${ai.service.url:http://localhost:8000}")
    private String aiServiceUrl;

    private final ObjectMapper objectMapper = new ObjectMapper();
    // 有界线程池：核心10/最大50，队列满时由调用线程执行，避免SSE并发把线程打爆
    private final ExecutorService sseExecutor = new ThreadPoolExecutor(
            10, 50, 60L, TimeUnit.SECONDS,
            new LinkedBlockingQueue<>(100),
            new ThreadPoolExecutor.CallerRunsPolicy());

    @GetMapping(value = "/stream/v3/chat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @Operation(summary = "AI流式对话(v3：SSE事件流 meta/llm_chunk/tool/product_card/citation/interrupt/complete/error，前端addEventListener监听)")
    public SseEmitter streamV3Chat(
            @RequestParam("q") String q,
            @RequestParam(value = "session_id", required = false) String sessionId,
            @RequestParam(value = "product_id", required = false) Long productId,
            @RequestParam(value = "user_id", required = false) String userId) {
        // user_id 优先登录态（不信任前端传值），未登录回退显式参数（游客链路）
        String effectiveUserId = resolveUserId(userId);
        StringBuilder url = new StringBuilder(aiServiceUrl + "/api/v3/chat/stream?q=")
                .append(URLEncoder.encode(q, StandardCharsets.UTF_8));
        if (productId != null) url.append("&product_id=").append(productId);
        if (sessionId != null && !sessionId.isBlank()) {
            url.append("&session_id=").append(URLEncoder.encode(sessionId, StandardCharsets.UTF_8));
        }
        if (effectiveUserId != null && !effectiveUserId.isBlank()) {
            url.append("&user_id=").append(URLEncoder.encode(effectiveUserId, StandardCharsets.UTF_8));
        }
        return proxySseV3(url.toString());
    }

    @PostMapping("/v3/resume")
    @Operation(summary = "AI写操作确认(v3：HITL硬中断恢复，透传 ai-service)")
    public ResponseEntity<String> resumeV3(@RequestBody Map<String, Object> body) {
        // user_id 以登录态为准注入，不信任前端传值；未登录回退 body.user_id，都没有返回401
        String userId = resolveUserId(strOrNull(body.get("user_id")));
        if (userId == null || userId.isBlank()) {
            return unauthorized();
        }
        Map<String, Object> pyBody = new HashMap<>();
        pyBody.put("session_id", body.get("session_id") != null ? body.get("session_id") : body.get("sessionId"));
        pyBody.put("approved", Boolean.TRUE.equals(body.get("approved")));
        try {
            return proxyJson("POST", "/api/v3/resume",
                    objectMapper.writeValueAsString(pyBody), Map.of("X-User-Id", userId));
        } catch (Exception e) {
            log.error("AI写操作确认失败: {}", e.getMessage(), e);
            return aiUnavailable();
        }
    }

    @PostMapping("/v3/feedback")
    @Operation(summary = "AI回答反馈(v3，透传 ai-service)")
    public ResponseEntity<String> feedbackV3(@RequestBody Map<String, Object> body) {
        // user_id 注入规则同 /v3/resume：登录态优先，回退 body.user_id，都没有返回401
        String userId = resolveUserId(strOrNull(body.get("user_id")));
        if (userId == null || userId.isBlank()) {
            return unauthorized();
        }
        Map<String, Object> pyBody = new HashMap<>();
        pyBody.put("request_id", body.get("request_id"));
        pyBody.put("session_id", body.get("session_id"));
        pyBody.put("rating", body.get("rating"));
        pyBody.put("comment", body.get("comment"));
        try {
            return proxyJson("POST", "/api/v3/feedback",
                    objectMapper.writeValueAsString(pyBody), Map.of("X-User-Id", userId));
        } catch (Exception e) {
            log.error("AI反馈提交失败: {}", e.getMessage(), e);
            return aiUnavailable();
        }
    }

    @GetMapping("/memory/conversation/{userId}")
    @Operation(summary = "获取会话历史（透传 ai-service，供前端重开页面回显）")
    public ResponseEntity<String> getConversationHistory(
            @PathVariable Long userId,
            @RequestParam("session_id") String sessionId,
            @RequestParam(value = "limit", defaultValue = "20") int limit) {
        String target = "/api/v1/ai/memory/conversation/" + userId
                + "?session_id=" + URLEncoder.encode(sessionId, StandardCharsets.UTF_8)
                + "&limit=" + limit;
        return proxyJson("GET", target);
    }

    @DeleteMapping("/memory/session/{userId}/{sessionId}")
    @Operation(summary = "清除指定会话（透传 ai-service）")
    public ResponseEntity<String> clearConversationSession(
            @PathVariable Long userId,
            @PathVariable String sessionId) {
        String target = "/api/v1/ai/memory/session/" + userId + "/"
                + URLEncoder.encode(sessionId, StandardCharsets.UTF_8);
        return proxyJson("DELETE", target);
    }

    // ==================== 知识库管理（数据飞轮闭环） ====================

    @GetMapping("/knowledge/gaps")
    @Operation(summary = "知识库缺口列表（透传 ai-service）")
    public ResponseEntity<String> listGaps(
            @RequestParam(value = "status", required = false) Integer status,
            @RequestParam(value = "limit", defaultValue = "50") int limit,
            @RequestParam(value = "offset", defaultValue = "0") int offset) {
        StringBuilder target = new StringBuilder("/api/v1/ai/knowledge/gaps?limit=" + limit + "&offset=" + offset);
        if (status != null) target.append("&status=").append(status);
        return proxyJson("GET", target.toString());
    }

    @PutMapping("/knowledge/gaps/{gapId}/status")
    @Operation(summary = "更新缺口处理状态（透传 ai-service）")
    public ResponseEntity<String> updateGapStatus(
            @PathVariable Long gapId,
            @RequestBody String body) {
        return proxyJson("PUT", "/api/v1/ai/knowledge/gaps/" + gapId + "/status", body, Map.of());
    }

    @GetMapping("/knowledge/faqs")
    @Operation(summary = "FAQ条目列表（透传 ai-service）")
    public ResponseEntity<String> listFaqs(
            @RequestParam(value = "q", defaultValue = "") String q,
            @RequestParam(value = "category", defaultValue = "") String category,
            @RequestParam(value = "limit", defaultValue = "50") int limit,
            @RequestParam(value = "offset", defaultValue = "0") int offset) {
        StringBuilder target = new StringBuilder("/api/v1/ai/knowledge/faqs?limit=" + limit + "&offset=" + offset);
        if (!q.isEmpty()) target.append("&q=").append(URLEncoder.encode(q, StandardCharsets.UTF_8));
        if (!category.isEmpty()) target.append("&category=").append(URLEncoder.encode(category, StandardCharsets.UTF_8));
        return proxyJson("GET", target.toString());
    }

    @PostMapping("/knowledge/faqs")
    @Operation(summary = "新增FAQ条目（透传 ai-service，自动embed）")
    public ResponseEntity<String> createFaq(@RequestBody String body) {
        return proxyJson("POST", "/api/v1/ai/knowledge/faqs", body, Map.of());
    }

    @PutMapping("/knowledge/faqs/{faqId}")
    @Operation(summary = "更新FAQ条目（透传 ai-service，自动embed）")
    public ResponseEntity<String> updateFaq(
            @PathVariable String faqId,
            @RequestBody String body) {
        return proxyJson("PUT", "/api/v1/ai/knowledge/faqs/" + faqId, body, Map.of());
    }

    @DeleteMapping("/knowledge/faqs/{faqId}")
    @Operation(summary = "删除FAQ条目（透传 ai-service）")
    public ResponseEntity<String> deleteFaq(@PathVariable String faqId) {
        return proxyJson("DELETE", "/api/v1/ai/knowledge/faqs/" + faqId);
    }

    @GetMapping("/knowledge/categories")
    @Operation(summary = "FAQ分类列表（透传 ai-service）")
    public ResponseEntity<String> listCategories() {
        return proxyJson("GET", "/api/v1/ai/knowledge/categories");
    }

    @PostMapping("/knowledge/rebuild")
    @Operation(summary = "重建ES索引（从种子全量导入，alias原子切换）")
    public ResponseEntity<String> rebuildIndex() {
        return proxyJson("POST", "/api/v1/ai/knowledge/rebuild", null, Map.of());
    }

    /**
     * 登录态优先解析 user_id：已登录取 sa-token 登录ID（不信任前端传值），
     * 未登录回退调用方显式提供的值（游客链路）。
     */
    private String resolveUserId(String fallback) {
        Object loginId = StpUtil.getLoginIdDefaultNull();
        return loginId != null ? String.valueOf(loginId) : fallback;
    }

    private String strOrNull(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private ResponseEntity<String> unauthorized() {
        return ResponseEntity.status(401)
                .contentType(MediaType.APPLICATION_JSON)
                .body("{\"success\":false,\"message\":\"未登录\"}");
    }

    private ResponseEntity<String> aiUnavailable() {
        return ResponseEntity.status(502)
                .contentType(MediaType.APPLICATION_JSON)
                .body("{\"success\":false,\"message\":\"AI服务暂时不可用\"}");
    }

    /**
     * 普通 JSON 透传：原样转发 ai-service 的状态码与响应体，
     * 不做 Result 包装，保持前端读取契约 {success,data} 一致。
     */
    private ResponseEntity<String> proxyJson(String method, String targetPathAndQuery) {
        return proxyJson(method, targetPathAndQuery, null, Map.of());
    }

    private ResponseEntity<String> proxyJson(String method, String targetPathAndQuery,
                                             String jsonBody, Map<String, String> headers) {
        HttpURLConnection conn = null;
        try {
            conn = (HttpURLConnection) URI.create(aiServiceUrl + targetPathAndQuery)
                    .toURL().openConnection();
            conn.setRequestMethod(method);
            conn.setConnectTimeout(10000);
            // /resume 恢复后需等待 Agent 生成最终答复（含 LLM 调用），读超时放宽
            conn.setReadTimeout(jsonBody != null ? 120000 : 30000);
            headers.forEach(conn::setRequestProperty);
            if (jsonBody != null) {
                conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type", "application/json");
                try (var os = conn.getOutputStream()) {
                    os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
                }
            }

            int status = conn.getResponseCode();
            java.io.InputStream stream = status >= 400
                    ? conn.getErrorStream()
                    : conn.getInputStream();
            String body = stream != null
                    ? new String(stream.readAllBytes(), StandardCharsets.UTF_8)
                    : "";
            return ResponseEntity.status(status)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body);
        } catch (Exception e) {
            log.error("AI服务JSON代理失败 {} {}: {}", method, targetPathAndQuery, e.getMessage());
            return aiUnavailable();
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    /**
     * SSE 透传(v3)：把 Python 服务的 text/event-stream 完整转发给前端，
     * 保留 event 名（meta/llm_chunk/tool/product_card/citation/interrupt/complete/error），
     * 前端通过 addEventListener(type) 监听对应事件。
     */
    private SseEmitter proxySseV3(String targetUrl) {
        SseEmitter emitter = new SseEmitter(180000L);

        sseExecutor.execute(() -> {
            HttpURLConnection conn = null;
            try {
                conn = (HttpURLConnection) URI.create(targetUrl).toURL().openConnection();
                conn.setRequestMethod("GET");
                conn.setRequestProperty("Accept", "text/event-stream");
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(180000);

                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
                    String eventName = null;
                    StringBuilder data = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        if (line.isEmpty()) {
                            // 空行 = 一帧结束，把累积的 event/data 转发给前端
                            if (data.length() > 0) {
                                var event = SseEmitter.event();
                                if (eventName != null) event = event.name(eventName);
                                emitter.send(event.data(data.toString()));
                            }
                            eventName = null;
                            data.setLength(0);
                        } else if (line.startsWith("event:")) {
                            eventName = line.substring(6).trim();
                        } else if (line.startsWith("data:")) {
                            if (data.length() > 0) data.append('\n');
                            data.append(line.substring(5).trim());
                        }
                        // id:/retry:/注释行不参与转发
                    }
                    // 流结束时最后一帧可能没有空行结尾
                    if (data.length() > 0) {
                        var event = SseEmitter.event();
                        if (eventName != null) event = event.name(eventName);
                        emitter.send(event.data(data.toString()));
                    }
                }

                emitter.complete();
            } catch (Exception e) {
                log.error("SSE流式代理出错 url={}: {}", targetUrl, e.getMessage(), e);
                try {
                    // 不回显内部异常细节，避免信息泄露；统一以 error 事件通知前端
                    emitter.send(SseEmitter.event().name("error")
                            .data("{\"message\":\"AI服务暂时不可用\"}"));
                } catch (Exception ignored) {
                }
                emitter.completeWithError(e);
            } finally {
                if (conn != null) {
                    conn.disconnect();
                }
            }
        });

        emitter.onTimeout(() -> log.warn("SSE连接超时"));
        emitter.onError(e -> log.warn("SSE连接错误: {}", e.getMessage()));

        return emitter;
    }
}
