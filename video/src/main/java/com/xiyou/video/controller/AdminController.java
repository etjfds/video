package com.xiyou.video.controller;

import com.xiyou.video.common.ApiResponse;
import com.xiyou.video.common.PageResult;
import com.xiyou.video.dto.VideoPublishRequest;
import com.xiyou.video.security.AuthContext;
import com.xiyou.video.service.AdminService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

/**
 * 管理员后台接口。
 * 提供用户管理、视频管理以及失效反馈处理能力。
 */
@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private final AdminService adminService;

    public AdminController(AdminService adminService) {
        this.adminService = adminService;
    }

    /**
     * 查询用户列表。
     *
     * @param keyword 可选关键字，匹配用户名或姓名
     * @param role    可选角色过滤
     * @return 用户列表
     */
    @GetMapping("/users")
    public ApiResponse<PageResult<Map<String, Object>>> users(@RequestParam(value = "keyword", required = false) String keyword,
                                                              @RequestParam(value = "role", required = false) String role,
                                                              @RequestParam(value = "page", defaultValue = "1") Long page,
                                                              @RequestParam(value = "pageSize", defaultValue = "10") Long pageSize) {
        AuthContext.requireAdmin();
        return ApiResponse.success(adminService.listUsers(keyword, role, page, pageSize));
    }

    /**
     * 更新普通用户启用状态。
     *
     * @param id     用户ID
     * @param status 目标状态，1启用，0禁用
     * @return 处理结果
     */
    @PutMapping("/users/{id}/status")
    public ApiResponse<Void> updateUserStatus(@PathVariable("id") Long id, @RequestParam("status") Integer status) {
        AuthContext.requireAdmin();
        adminService.updateUserStatus(AuthContext.requireUserId(), id, status);
        return ApiResponse.success("状态更新成功", null);
    }

    /**
     * 查询后台视频列表。
     *
     * @param keyword 可选关键字，匹配标题或标签
     * @param status  可选状态，0草稿，1上架，2下架
     * @return 视频列表
     */
    @GetMapping("/videos")
    public ApiResponse<PageResult<Map<String, Object>>> videos(@RequestParam(value = "keyword", required = false) String keyword,
                                                               @RequestParam(value = "status", required = false) Integer status,
                                                               @RequestParam(value = "page", defaultValue = "1") Long page,
                                                               @RequestParam(value = "pageSize", defaultValue = "10") Long pageSize) {
        AuthContext.requireAdmin();
        return ApiResponse.success(adminService.listVideos(keyword, status, page, pageSize));
    }

    /**
     * 查询单个视频详情，供后台编辑表单回填使用。
     *
     * @param id 视频ID
     * @return 视频详情
     */
    @GetMapping("/videos/{id}")
    public ApiResponse<Map<String, Object>> videoDetail(@PathVariable("id") Long id) {
        AuthContext.requireAdmin();
        return ApiResponse.success(adminService.getVideoDetail(id));
    }

    /**
     * 新增视频。
     *
     * @param request 视频发布参数
     * @return 新增后的基础信息
     */
    @PostMapping("/videos")
    public ApiResponse<Map<String, Object>> createVideo(@Validated @RequestBody VideoPublishRequest request) {
        AuthContext.requireAdmin();
        return ApiResponse.success("视频保存成功", adminService.saveVideo(AuthContext.requireUserId(), null, request));
    }

    /**
     * 上传视频封面图片。
     * 文件会保存到本地 img 目录，并返回新的封面访问地址。
     *
     * @param file 前端上传的封面文件
     * @return 新的封面访问地址
     */
    @PostMapping("/videos/cover")
    public ApiResponse<Map<String, Object>> uploadVideoCover(@RequestParam("file") MultipartFile file) throws Exception {
        AuthContext.requireAdmin();
        return ApiResponse.success("封面上传成功",
                adminService.uploadVideoCover(AuthContext.requireUserId(),
                        file == null ? null : file.getOriginalFilename(),
                        file == null ? null : file.getBytes()));
    }

    /**
     * 更新视频信息。
     *
     * @param id      视频ID
     * @param request 视频更新参数
     * @return 更新后的基础信息
     */
    @PutMapping("/videos/{id}")
    public ApiResponse<Map<String, Object>> updateVideo(@PathVariable("id") Long id,
                                                        @RequestBody VideoPublishRequest request) {
        AuthContext.requireAdmin();
        return ApiResponse.success("视频更新成功", adminService.saveVideo(AuthContext.requireUserId(), id, request));
    }

    /**
     * 查询视频失效反馈列表。
     *
     * @return 反馈列表
     */
    @GetMapping("/reports")
    public ApiResponse<List<Map<String, Object>>> reports() {
        AuthContext.requireAdmin();
        return ApiResponse.success(adminService.listReports());
    }

    /**
     * 处理视频失效反馈。
     *
     * @param id     反馈记录ID
     * @param status 处理状态，1已确认，2已忽略
     * @return 处理结果
     */
    @PutMapping("/reports/{id}/status")
    public ApiResponse<Void> handleReport(@PathVariable("id") Long id, @RequestParam("status") Integer status) {
        AuthContext.requireAdmin();
        adminService.handleReport(AuthContext.requireUserId(), id, status);
        return ApiResponse.success("反馈处理成功", null);
    }
}
