package com.xiyou.video.service;

import com.xiyou.video.common.PageResult;
import com.xiyou.video.dto.VideoReportRequest;

import java.util.Map;

public interface VideoService {

    PageResult<Map<String, Object>> listVideos(Long userId, String keyword, long page, long pageSize);

    Map<String, Object> getDetail(Long userId, Long videoId);

    Map<String, Object> play(Long userId, Long videoId);

    Map<String, Object> toggleLike(Long userId, Long videoId);

    Map<String, Object> toggleFavorite(Long userId, Long videoId);

    PageResult<Map<String, Object>> recommend(Long userId, String algorithm, long page, long pageSize);

    void reportInvalid(Long userId, Long videoId, VideoReportRequest request);
}
