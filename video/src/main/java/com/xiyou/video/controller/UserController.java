package com.xiyou.video.controller;

import com.xiyou.video.common.ApiResponse;
import com.xiyou.video.dto.ProfileUpdateRequest;
import com.xiyou.video.security.AuthContext;
import com.xiyou.video.service.UserService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

/**
 * 普通用户个人中心接口。
 * 提供个人资料查询、资料修改和头像上传能力。
 */
@RestController
@RequestMapping("/api/user")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * 查询当前登录用户的个人资料。
     *
     * @return 用户基础信息、我的点赞列表、我的收藏列表
     */
    @GetMapping("/profile")
    public ApiResponse<Map<String, Object>> profile() {
        return ApiResponse.success(userService.getProfile(AuthContext.requireUserId()));
    }

    /**
     * 更新当前登录用户的个人资料。
     *
     * @param request 资料更新参数，包含姓名和头像访问地址
     * @return 更新后的用户资料
     */
    @PutMapping("/profile")
    public ApiResponse<Map<String, Object>> updateProfile(@Validated @RequestBody ProfileUpdateRequest request) {
        return ApiResponse.success("更新成功", userService.updateProfile(AuthContext.requireUserId(), request));
    }

    /**
     * 上传当前登录用户头像。
     * 文件会保存到本地 img 目录，并返回新的头像访问地址。
     *
     * @param file 前端上传的头像文件
     * @return 更新后的用户资料
     */
    @PostMapping("/avatar")
    public ApiResponse<Map<String, Object>> uploadAvatar(@RequestParam("file") MultipartFile file) throws Exception {
        return ApiResponse.success("头像上传成功",
                userService.uploadAvatar(AuthContext.requireUserId(), file == null ? null : file.getOriginalFilename(), file == null ? null : file.getBytes()));
    }
}
