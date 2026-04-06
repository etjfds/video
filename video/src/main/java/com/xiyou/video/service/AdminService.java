package com.xiyou.video.service;

import com.xiyou.video.common.PageResult;
import com.xiyou.video.dto.AdminCreateRequest;
import com.xiyou.video.dto.VideoPublishRequest;

import java.util.List;
import java.util.Map;

public interface AdminService {

    Map<String, Object> createAdmin(Long operatorId, AdminCreateRequest request);

    PageResult<Map<String, Object>> listUsers(String keyword, String role, long page, long pageSize);

    void updateUserStatus(Long operatorId, Long userId, Integer status);

    Map<String, Object> getVideoDetail(Long videoId);

    Map<String, Object> uploadVideoCover(Long operatorId, String originalFilename, byte[] bytes);

    Map<String, Object> saveVideo(Long operatorId, Long videoId, VideoPublishRequest request);

    PageResult<Map<String, Object>> listVideos(String keyword, Integer status, long page, long pageSize);

    List<Map<String, Object>> listReports();

    void handleReport(Long operatorId, Long reportId, Integer status);
}
