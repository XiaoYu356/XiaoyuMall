package com.mall.user.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

@Data
@Schema(description = "用户查询请求")
public class UserQueryDTO {

    @Schema(description = "用户名")
    private String username;

    @Schema(description = "手机号")
    private String phone;

    @Schema(description = "状态 0-禁用 1-启用")
    private Integer status;

    @Min(1)
    @Schema(description = "页码", defaultValue = "1")
    private Integer pageNum = 1;

    @Min(1) @Max(100)
    @Schema(description = "每页数量", defaultValue = "10")
    private Integer pageSize = 10;
}
