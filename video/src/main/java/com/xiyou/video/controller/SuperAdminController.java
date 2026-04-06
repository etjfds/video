package com.xiyou.video.controller;

import com.xiyou.video.common.ApiResponse;
import com.xiyou.video.dto.AdminCreateRequest;
import com.xiyou.video.security.AuthContext;
import com.xiyou.video.service.AdminService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 超级管理员接口。
 * 当前版本主要提供管理员账号创建能力。
 */
@RestController
@RequestMapping("/api/super-admin")
public class SuperAdminController {

    private final AdminService adminService;

    public SuperAdminController(AdminService adminService) {
        this.adminService = adminService;
    }

    /**
     * 创建管理员账号。
     * 仅 SUPER_ADMIN 角色允许访问。
     *
     * @param request 管理员创建参数
     * @return 新建管理员信息
     */
    @PostMapping("/admins")
    public ApiResponse<Map<String, Object>> createAdmin(@Validated @RequestBody AdminCreateRequest request) {
        AuthContext.requireSuperAdmin();
        return ApiResponse.success("管理员创建成功", adminService.createAdmin(AuthContext.requireUserId(), request));
    }
}
