package com.xiyou.video.dto;

import javax.validation.constraints.NotBlank;

public class ProfileUpdateRequest {

    @NotBlank(message = "姓名不能为空")
    private String realName;

    private String avatarUrl;

    public String getRealName() {
        return realName;
    }

    public void setRealName(String realName) {
        this.realName = realName;
    }

    public String getAvatarUrl() {
        return avatarUrl;
    }

    public void setAvatarUrl(String avatarUrl) {
        this.avatarUrl = avatarUrl;
    }
}
