package com.mall.product.controller;

import com.mall.common.result.Result;
import com.mall.product.service.MinioService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@Slf4j
@RestController
@RequestMapping("/api/v1/upload")
@Tag(name = "文件上传", description = "文件上传接口")
public class UploadController {

    @Autowired
    private MinioService minioService;

    @PostMapping
    @Operation(summary = "上传文件")
    public Result<String> upload(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return Result.failed("上传文件不能为空");
        }
        try {
            String url = minioService.uploadFile(
                    file.getOriginalFilename(),
                    file.getInputStream(),
                    file.getContentType()
            );
            return Result.success(url);
        } catch (Exception e) {
            log.error("文件上传失败: {}", e.getMessage(), e);
            return Result.failed("文件上传失败: " + e.getMessage());
        }
    }
}
