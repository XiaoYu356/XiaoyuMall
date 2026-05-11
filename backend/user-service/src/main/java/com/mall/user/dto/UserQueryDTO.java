package com.mall.user.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "用户查询请求")
public class UserQueryDTO {
    
    @Schema(description = "用户名")
    private String username;
    
    @Schema(description = "手机号")
    private String phone;
    
    @Schema(description = "页码", defaultValue = "1")
    private Integer pageNum = 1;
    
    @Schema(description = "每页数量", defaultValue = "10")
    private Integer pageSize = 10;
}
