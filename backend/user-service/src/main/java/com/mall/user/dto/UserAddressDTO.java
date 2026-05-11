package com.mall.user.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "用户地址请求")
public class UserAddressDTO {
    
    @Schema(description = "地址ID(更新时需要)")
    private Long id;
    
    @Schema(description = "收货人姓名", required = true)
    @NotBlank(message = "收货人姓名不能为空")
    private String receiverName;
    
    @Schema(description = "收货人电话", required = true)
    @NotBlank(message = "收货人电话不能为空")
    private String receiverPhone;
    
    @Schema(description = "省份", required = true)
    @NotBlank(message = "省份不能为空")
    private String province;
    
    @Schema(description = "城市", required = true)
    @NotBlank(message = "城市不能为空")
    private String city;
    
    @Schema(description = "区县", required = true)
    @NotBlank(message = "区县不能为空")
    private String district;
    
    @Schema(description = "详细地址", required = true)
    @NotBlank(message = "详细地址不能为空")
    private String detailAddress;
    
    @Schema(description = "是否默认地址")
    private Integer isDefault;
}
