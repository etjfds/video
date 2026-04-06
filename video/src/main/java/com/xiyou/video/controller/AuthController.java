package com.xiyou.video.controller;

import com.xiyou.video.common.ApiResponse;
import com.xiyou.video.dto.LoginRequest;
import com.xiyou.video.dto.RegisterRequest;
import com.xiyou.video.service.AuthService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 认证相关接口。
 * 提供普通用户注册、普通用户登录以及管理员登录能力。
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    /**
     * 普通用户注册接口。
     *
     * @param request 注册请求参数，包含用户名、密码、姓名
     * @return 登录态信息，包含 token 和用户基础信息
     */
    @PostMapping("/register")
    public ApiResponse<Map<String, Object>> register(@Validated @RequestBody RegisterRequest request) {
        return ApiResponse.success("注册成功", authService.register(request));
    }

    /**
     * 普通用户登录接口。
     *
     * @param request 登录请求参数，包含用户名和密码
     * @return 登录态信息，包含 token 和用户基础信息
     */
    @PostMapping("/login")
    public ApiResponse<Map<String, Object>> login(@Validated @RequestBody LoginRequest request) {
        return ApiResponse.success("登录成功", authService.login(request, false));
    }

    /**
     * 管理员登录接口。
     * 仅允许 ADMIN 或 SUPER_ADMIN 角色账号登录。
     *
     * @param request 登录请求参数，包含用户名和密码
     * @return 登录态信息，包含 token 和用户基础信息
     */
    @PostMapping("/admin/login")
    public ApiResponse<Map<String, Object>> adminLogin(@Validated @RequestBody LoginRequest request) {
        return ApiResponse.success("登录成功", authService.login(request, true));
    }
}
