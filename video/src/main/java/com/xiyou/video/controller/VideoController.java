package com.xiyou.video.controller;

import com.xiyou.video.common.ApiResponse;
import com.xiyou.video.common.PageResult;
import com.xiyou.video.dto.VideoReportRequest;
import com.xiyou.video.security.AuthContext;
import com.xiyou.video.security.AuthUser;
import com.xiyou.video.service.VideoService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 视频相关接口。
 * 提供视频列表、推荐、详情、播放、点赞、收藏和失效反馈能力。
 */
@RestController
@RequestMapping("/api/video")
public class VideoController {

    private final VideoService videoService;

    public VideoController(VideoService videoService) {
        this.videoService = videoService;
    }

    /**
     * 查询视频列表。
     * 未登录也可以访问；登录后会额外返回当前用户的点赞和收藏状态。
     *
     * @param keyword 可选搜索关键字，用于匹配标题或标签
     * @return 视频卡片列表
     */
    @GetMapping("/list")
    public ApiResponse<PageResult<Map<String, Object>>> list(@RequestParam(value = "keyword", required = false) String keyword,
                                                             @RequestParam(value = "page", defaultValue = "1") Long page,
                                                             @RequestParam(value = "pageSize", defaultValue = "12") Long pageSize) {
        AuthUser user = AuthContext.get();
        return ApiResponse.success(videoService.listVideos(user == null ? null : user.getId(), keyword, page, pageSize));
    }

    /**
     * 查询推荐视频列表。
     * 支持三种推荐算法：标签偏好、相似用户、热门趋势。
     * 未登录时会回退到公开推荐策略，以便三个选项仍然展示不同数据。
     *
     * @return 推荐视频列表
     */
    @GetMapping("/recommend")
    public ApiResponse<PageResult<Map<String, Object>>> recommend(@RequestParam(value = "algorithm", defaultValue = "tag") String algorithm,
                                                                  @RequestParam(value = "page", defaultValue = "1") Long page,
                                                                  @RequestParam(value = "pageSize", defaultValue = "12") Long pageSize) {
        AuthUser user = AuthContext.get();
        return ApiResponse.success(videoService.recommend(user == null ? null : user.getId(), algorithm, page, pageSize));
    }

    /**
     * 查询视频详情。
     *
     * @param id 视频ID
     * @return 视频详情，包括播放模式、来源地址、统计信息等
     */
    @GetMapping("/{id}")
    public ApiResponse<Map<String, Object>> detail(@PathVariable("id") Long id) {
        AuthUser user = AuthContext.get();
        return ApiResponse.success(videoService.getDetail(user == null ? null : user.getId(), id));
    }

    /**
     * 记录视频播放行为并返回实际播放信息。
     * 前端根据 playMode 决定使用 video、iframe 还是原站跳转。
     *
     * @param id 视频ID
     * @return 播放模式及对应播放地址
     */
    @PostMapping("/{id}/play")
    public ApiResponse<Map<String, Object>> play(@PathVariable("id") Long id) {
        AuthUser user = AuthContext.get();
        return ApiResponse.success(videoService.play(user == null ? null : user.getId(), id));
    }

    /**
     * 点赞或取消点赞当前视频。
     *
     * @param id 视频ID
     * @return 最新点赞状态
     */
    @PostMapping("/{id}/like")
    public ApiResponse<Map<String, Object>> like(@PathVariable("id") Long id) {
        return ApiResponse.success(videoService.toggleLike(AuthContext.requireUserId(), id));
    }

    /**
     * 收藏或取消收藏当前视频。
     *
     * @param id 视频ID
     * @return 最新收藏状态
     */
    @PostMapping("/{id}/favorite")
    public ApiResponse<Map<String, Object>> favorite(@PathVariable("id") Long id) {
        return ApiResponse.success(videoService.toggleFavorite(AuthContext.requireUserId(), id));
    }

    /**
     * 提交视频失效反馈。
     *
     * @param id      视频ID
     * @param request 反馈原因
     * @return 提交结果
     */
    @PostMapping("/{id}/report")
    public ApiResponse<Void> report(@PathVariable("id") Long id, @Validated @RequestBody VideoReportRequest request) {
        videoService.reportInvalid(AuthContext.requireUserId(), id, request);
        return ApiResponse.success("反馈已提交", null);
    }
}
