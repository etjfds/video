package com.xiyou.video.dto;

import javax.validation.constraints.NotBlank;

public class VideoReportRequest {

    @NotBlank(message = "反馈原因不能为空")
    private String reason;

    public String getReason() {
        return reason;
    }

    public void setReason(String reason) {
        this.reason = reason;
    }
}
