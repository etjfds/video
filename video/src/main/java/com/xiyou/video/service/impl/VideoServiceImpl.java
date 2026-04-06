package com.xiyou.video.service.impl;

import com.xiyou.video.common.PageResult;
import com.xiyou.video.common.BusinessException;
import com.xiyou.video.domain.VideoInfo;
import com.xiyou.video.domain.VideoInvalidReport;
import com.xiyou.video.dto.VideoReportRequest;
import com.xiyou.video.mapper.FavoriteMapper;
import com.xiyou.video.mapper.LikeMapper;
import com.xiyou.video.mapper.PlayHistoryMapper;
import com.xiyou.video.mapper.ReportMapper;
import com.xiyou.video.mapper.VideoMapper;
import com.xiyou.video.service.VideoService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;

@Service
public class VideoServiceImpl implements VideoService {

    private static final String ALGORITHM_CONTENT = "content";
    private static final String ALGORITHM_SIMILAR = "similar";
    private static final String ALGORITHM_PREFERENCE = "preference";
    private static final String ALGORITHM_HYBRID = "hybrid";

    private final VideoMapper videoMapper;
    private final LikeMapper likeMapper;
    private final FavoriteMapper favoriteMapper;
    private final PlayHistoryMapper playHistoryMapper;
    private final ReportMapper reportMapper;

    public VideoServiceImpl(VideoMapper videoMapper,
                            LikeMapper likeMapper,
                            FavoriteMapper favoriteMapper,
                            PlayHistoryMapper playHistoryMapper,
                            ReportMapper reportMapper) {
        this.videoMapper = videoMapper;
        this.likeMapper = likeMapper;
        this.favoriteMapper = favoriteMapper;
        this.playHistoryMapper = playHistoryMapper;
        this.reportMapper = reportMapper;
    }

    @Override
    @Transactional(readOnly = true)
    public PageResult<Map<String, Object>> listVideos(Long userId, String keyword, long page, long pageSize) {
        long safePage = normalizePage(page);
        long safePageSize = normalizePageSize(pageSize);
        long offset = (safePage - 1) * safePageSize;
        List<VideoInfo> videos = videoMapper.listPublished(keyword, offset, safePageSize);
        long total = videoMapper.countPublished(keyword);
        UserVideoState state = buildUserVideoState(userId);
        List<Map<String, Object>> records = videos.stream()
                .map(video -> toVideoCard(video, state))
                .collect(Collectors.toList());
        return new PageResult<>(records, total, safePage, safePageSize);
    }

    @Override
    @Transactional(readOnly = true)
    public Map<String, Object> getDetail(Long userId, Long videoId) {
        VideoInfo video = videoMapper.findPublishedById(videoId);
        if (video == null) {
            throw new BusinessException("视频不存在或已下架");
        }
        return toVideoDetail(video, buildUserVideoState(userId));
    }

    @Override
    @Transactional
    public Map<String, Object> play(Long userId, Long videoId) {
        VideoInfo video = videoMapper.findPublishedById(videoId);
        if (video == null) {
            throw new BusinessException("视频不存在或已下架");
        }
        videoMapper.incrementPlayCount(videoId);
        if (userId != null) {
            playHistoryMapper.insert(userId, videoId);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("videoId", videoId);
        result.put("playMode", video.getPlayMode());
        result.put("playUrl", video.getPlayUrl());
        result.put("embedUrl", video.getEmbedUrl());
        result.put("sourceUrl", video.getSourceUrl());
        result.put("title", video.getTitle());
        return result;
    }

    @Override
    @Transactional
    public Map<String, Object> toggleLike(Long userId, Long videoId) {
        VideoInfo video = videoMapper.findPublishedById(videoId);
        if (video == null) {
            throw new BusinessException("视频不存在或已下架");
        }
        int currentLikeCount = safe(video.getLikeCount());
        boolean liked = likeMapper.count(userId, videoId) > 0;
        if (liked) {
            likeMapper.delete(userId, videoId);
            videoMapper.incrementLikeCount(videoId, -1);
        } else {
            likeMapper.insert(userId, videoId);
            videoMapper.incrementLikeCount(videoId, 1);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("liked", !liked);
        result.put("likeCount", Math.max(currentLikeCount + (liked ? -1 : 1), 0));
        return result;
    }

    @Override
    @Transactional
    public Map<String, Object> toggleFavorite(Long userId, Long videoId) {
        VideoInfo video = videoMapper.findPublishedById(videoId);
        if (video == null) {
            throw new BusinessException("视频不存在或已下架");
        }
        int currentFavoriteCount = safe(video.getFavoriteCount());
        boolean favorited = favoriteMapper.count(userId, videoId) > 0;
        if (favorited) {
            favoriteMapper.delete(userId, videoId);
            videoMapper.incrementFavoriteCount(videoId, -1);
        } else {
            favoriteMapper.insert(userId, videoId);
            videoMapper.incrementFavoriteCount(videoId, 1);
        }
        Map<String, Object> result = new HashMap<>();
        result.put("favorited", !favorited);
        result.put("favoriteCount", Math.max(currentFavoriteCount + (favorited ? -1 : 1), 0));
        return result;
    }

    @Override
    @Transactional(readOnly = true)
    public PageResult<Map<String, Object>> recommend(Long userId, String algorithm, long page, long pageSize) {
        long safePage = normalizePage(page);
        long safePageSize = normalizePageSize(pageSize);
        String resolvedAlgorithm = resolveAlgorithm(algorithm);
        List<VideoInfo> candidates = new ArrayList<>(videoMapper.listAllPublished());
        if (candidates.isEmpty()) {
            return new PageResult<>(new ArrayList<>(), 0, safePage, safePageSize);
        }
        UserVideoState state = buildUserVideoState(userId);
        if (userId == null) {
            List<VideoInfo> guestVideos = buildGuestRecommendations(candidates, resolvedAlgorithm);
            List<Map<String, Object>> records = paginateVideos(guestVideos, state, safePage, safePageSize, true);
            return new PageResult<>(records, guestVideos.size(), safePage, safePageSize);
        }
        RecommendationProfile profile = buildRecommendationProfile(userId);
        List<VideoInfo> recommendableCandidates = filterOutEngagedVideos(candidates, profile.engagedVideoIds);
        if (recommendableCandidates.isEmpty()) {
            recommendableCandidates = candidates;
        }
        List<VideoInfo> sortedVideos = buildRecommendationsByAlgorithm(userId, resolvedAlgorithm, recommendableCandidates, candidates, profile);
        List<Map<String, Object>> records = paginateVideos(sortedVideos, state, safePage, safePageSize, true);
        return new PageResult<>(records, sortedVideos.size(), safePage, safePageSize);
    }

    @Override
    @Transactional
    public void reportInvalid(Long userId, Long videoId, VideoReportRequest request) {
        VideoInfo video = videoMapper.findPublishedById(videoId);
        if (video == null) {
            throw new BusinessException("视频不存在或已下架");
        }
        if (reportMapper.countPendingByUser(userId, videoId) > 0) {
            throw new BusinessException("你已经提交过待处理反馈");
        }
        VideoInvalidReport report = new VideoInvalidReport();
        report.setUserId(userId);
        report.setVideoId(videoId);
        report.setReason(request.getReason());
        reportMapper.insert(report);
        videoMapper.incrementInvalidReportCount(videoId);
    }

    private void collectTagWeight(Map<String, Integer> tagWeight, List<VideoInfo> videos, int baseWeight) {
        for (VideoInfo video : videos) {
            for (String tag : splitTags(video.getTags())) {
                tagWeight.merge(tag, baseWeight, Integer::sum);
            }
        }
    }

    private List<VideoInfo> buildGuestRecommendations(List<VideoInfo> candidates, String algorithm) {
        if (ALGORITHM_CONTENT.equals(algorithm)) {
            return candidates.stream()
                    .sorted(Comparator.comparingInt((VideoInfo video) -> contentSimilarityScore(video)).reversed()
                            .thenComparing(VideoInfo::getCreateTime, Comparator.reverseOrder()))
                    .collect(Collectors.toList());
        }
        if (ALGORITHM_SIMILAR.equals(algorithm)) {
            return candidates.stream()
                    .sorted(Comparator.comparingInt((VideoInfo video) -> qualityScore(video)).reversed()
                            .thenComparing(VideoInfo::getId, Comparator.reverseOrder()))
                    .collect(Collectors.toList());
        }
        if (ALGORITHM_PREFERENCE.equals(algorithm)) {
            return candidates.stream()
                    .sorted(Comparator.comparingInt((VideoInfo video) -> freshnessScore(video)).reversed()
                            .thenComparing(VideoInfo::getCreateTime, Comparator.reverseOrder()))
                    .collect(Collectors.toList());
        }
        return buildHybridRecommendations(candidates);
    }

    private List<VideoInfo> buildRecommendationsByAlgorithm(Long userId,
                                                            String algorithm,
                                                            List<VideoInfo> recommendableCandidates,
                                                            List<VideoInfo> allCandidates,
                                                            RecommendationProfile profile) {
        if (ALGORITHM_CONTENT.equals(algorithm)) {
            return buildContentBasedRecommendations(recommendableCandidates, allCandidates, profile);
        }
        if (ALGORITHM_SIMILAR.equals(algorithm)) {
            return buildSimilarUserRecommendations(userId, recommendableCandidates, profile);
        }
        if (ALGORITHM_PREFERENCE.equals(algorithm)) {
            return buildPreferenceRecommendations(recommendableCandidates, allCandidates, profile);
        }
        return buildHybridRecommendations(recommendableCandidates, allCandidates, profile);
    }

    private List<VideoInfo> buildTagRecommendations(List<VideoInfo> recommendableCandidates,
                                                    List<VideoInfo> allCandidates,
                                                    RecommendationProfile profile) {
        Map<String, Integer> tagWeight = new HashMap<>();
        collectTagWeight(tagWeight, profile.likedVideos, 5);
        collectTagWeight(tagWeight, profile.favoriteVideos, 7);
        for (String tagString : profile.recentPlayedTags) {
            for (String tag : splitTags(tagString)) {
                tagWeight.merge(tag, 2, Integer::sum);
            }
        }
        if (tagWeight.isEmpty()) {
            return buildHotRecommendations(allCandidates);
        }
        return recommendableCandidates.stream()
                .sorted(Comparator.comparingInt((VideoInfo video) -> tagPreferenceScore(video, tagWeight)).reversed()
                        .thenComparing(VideoInfo::getId, Comparator.reverseOrder()))
                .collect(Collectors.toList());
    }

    private List<VideoInfo> buildSimilarUserRecommendations(Long userId,
                                                            List<VideoInfo> recommendableCandidates,
                                                            RecommendationProfile profile) {
        if (profile.engagedVideoIds.isEmpty()) {
            return recommendableCandidates.stream()
                    .sorted(Comparator.comparingInt(this::qualityScore).reversed()
                            .thenComparing(VideoInfo::getUpdateTime))
                    .collect(Collectors.toList());
        }
        List<Long> seedVideoIds = new ArrayList<>(profile.engagedVideoIds);
        Set<Long> neighborUserIds = new LinkedHashSet<>();
        neighborUserIds.addAll(likeMapper.listUserIdsByVideoIds(seedVideoIds));
        neighborUserIds.addAll(favoriteMapper.listUserIdsByVideoIds(seedVideoIds));
        neighborUserIds.addAll(playHistoryMapper.listUserIdsByVideoIds(seedVideoIds));
        neighborUserIds.remove(userId);
        if (neighborUserIds.isEmpty()) {
            return recommendableCandidates.stream()
                    .sorted(Comparator.comparingInt(this::qualityScore).reversed()
                            .thenComparing(VideoInfo::getUpdateTime))
                    .collect(Collectors.toList());
        }

        List<Long> neighborIds = new ArrayList<>(neighborUserIds);
        Map<Long, Integer> collaborativeScore = new HashMap<>();
        collectVideoScore(collaborativeScore, likeMapper.listLikedVideoIdsByUsers(neighborIds), 5);
        collectVideoScore(collaborativeScore, favoriteMapper.listFavoriteVideoIdsByUsers(neighborIds), 7);
        collectVideoScore(collaborativeScore, playHistoryMapper.listPlayedVideoIdsByUsers(neighborIds), 2);
        if (collaborativeScore.isEmpty()) {
            return recommendableCandidates.stream()
                    .sorted(Comparator.comparingInt(this::qualityScore).reversed()
                            .thenComparing(VideoInfo::getUpdateTime))
                    .collect(Collectors.toList());
        }

        return recommendableCandidates.stream()
                .sorted(Comparator.comparingInt((VideoInfo video) -> calculateCollaborativeScore(video, collaborativeScore)).reversed()
                        .thenComparing(VideoInfo::getUpdateTime))
                .collect(Collectors.toList());
    }

    private void collectVideoScore(Map<Long, Integer> videoScore, List<Long> videoIds, int weight) {
        for (Long videoId : videoIds) {
            if (videoId != null) {
                videoScore.merge(videoId, weight, Integer::sum);
            }
        }
    }

    private int qualityScore(VideoInfo video) {
        return safe(video.getLikeCount()) * 4 + safe(video.getFavoriteCount()) * 6 + safe(video.getPlayCount());
    }

    private int freshnessScore(VideoInfo video) {
        return safe(video.getLikeCount()) * 2 + safe(video.getFavoriteCount()) * 3 + Math.toIntExact(safeLong(video.getId()));
    }

    private int hotScore(VideoInfo video) {
        int score = safe(video.getPlayCount()) + safe(video.getLikeCount()) * 3 + safe(video.getFavoriteCount()) * 5;
        score -= safe(video.getInvalidReportCount()) * 5;
        return score;
    }

    private int tagPreferenceScore(VideoInfo video, Map<String, Integer> tagWeight) {
        int score = hotScore(video);
        for (String tag : splitTags(video.getTags())) {
            score += tagWeight.getOrDefault(tag, 0) * 10;
        }
        return score;
    }

    private int calculateCollaborativeScore(VideoInfo video, Map<Long, Integer> collaborativeScoreMap) {
        return collaborativeScoreMap.getOrDefault(video.getId(), 0) * 100 + hotScore(video);
    }

    private List<VideoInfo> buildHotRecommendations(List<VideoInfo> candidates) {
        return candidates.stream()
                .sorted(Comparator.comparingInt(this::hotScore).reversed()
                        .thenComparing(VideoInfo::getId, Comparator.reverseOrder()))
                .collect(Collectors.toList());
    }

    private int contentSimilarityScore(VideoInfo video) {
        return safe(video.getLikeCount()) * 3 + safe(video.getFavoriteCount()) * 4 + safe(video.getPlayCount()) / 2;
    }

    private List<VideoInfo> buildContentBasedRecommendations(List<VideoInfo> recommendableCandidates,
                                                             List<VideoInfo> allCandidates,
                                                             RecommendationProfile profile) {
        Map<String, Integer> tagWeight = new HashMap<>();
        collectTagWeight(tagWeight, profile.likedVideos, 3);
        collectTagWeight(tagWeight, profile.favoriteVideos, 5);
        for (String tagString : profile.recentPlayedTags) {
            for (String tag : splitTags(tagString)) {
                tagWeight.merge(tag, 1, Integer::sum);
            }
        }
        if (tagWeight.isEmpty()) {
            return allCandidates.stream()
                    .sorted(Comparator.comparingInt(this::contentSimilarityScore).reversed()
                            .thenComparing(VideoInfo::getCreateTime, Comparator.reverseOrder()))
                    .collect(Collectors.toList());
        }
        return recommendableCandidates.stream()
                .sorted(Comparator.comparingInt((VideoInfo v) -> contentSimilarityScore(v) + calculateTagMatchScore(v, tagWeight) * 3).reversed()
                        .thenComparing(VideoInfo::getCreateTime, Comparator.reverseOrder()))
                .collect(Collectors.toList());
    }

    private List<VideoInfo> buildPreferenceRecommendations(List<VideoInfo> recommendableCandidates,
                                                           List<VideoInfo> allCandidates,
                                                           RecommendationProfile profile) {
        Map<String, Integer> tagWeight = new HashMap<>();
        collectTagWeight(tagWeight, profile.likedVideos, 5);
        collectTagWeight(tagWeight, profile.favoriteVideos, 7);
        for (String tagString : profile.recentPlayedTags) {
            for (String tag : splitTags(tagString)) {
                tagWeight.merge(tag, 3, Integer::sum);
            }
        }
        if (tagWeight.isEmpty()) {
            return allCandidates.stream()
                    .sorted(Comparator.comparingInt(this::freshnessScore).reversed()
                            .thenComparing(VideoInfo::getCreateTime, Comparator.reverseOrder()))
                    .collect(Collectors.toList());
        }
        return recommendableCandidates.stream()
                .sorted(Comparator.comparingInt((VideoInfo v) -> calculatePureTagScore(v, tagWeight)).reversed()
                        .thenComparing(VideoInfo::getCreateTime, Comparator.reverseOrder()))
                .collect(Collectors.toList());
    }

    private List<VideoInfo> buildHybridRecommendations(List<VideoInfo> recommendableCandidates,
                                                       List<VideoInfo> allCandidates,
                                                       RecommendationProfile profile) {
        Map<String, Integer> tagWeight = new HashMap<>();
        collectTagWeight(tagWeight, profile.likedVideos, 4);
        collectTagWeight(tagWeight, profile.favoriteVideos, 6);
        for (String tagString : profile.recentPlayedTags) {
            for (String tag : splitTags(tagString)) {
                tagWeight.merge(tag, 2, Integer::sum);
            }
        }
        List<VideoInfo> candidates = recommendableCandidates.isEmpty() ? allCandidates : recommendableCandidates;
        return candidates.stream()
                .sorted(Comparator.comparingInt((VideoInfo v) -> {
                    int score = hotScore(v);
                    if (!tagWeight.isEmpty()) {
                        score += calculateTagMatchScore(v, tagWeight) * 2;
                    }
                    return score;
                }).reversed()
                        .thenComparing(VideoInfo::getCreateTime))
                .collect(Collectors.toList());
    }

    private List<VideoInfo> buildHybridRecommendations(List<VideoInfo> candidates) {
        return candidates.stream()
                .sorted(Comparator.comparingInt(this::hotScore).reversed()
                        .thenComparing(VideoInfo::getCreateTime))
                .collect(Collectors.toList());
    }

    private int calculateTagMatchScore(VideoInfo video, Map<String, Integer> tagWeight) {
        int score = 0;
        for (String tag : splitTags(video.getTags())) {
            score += tagWeight.getOrDefault(tag, 0);
        }
        return score;
    }

    private int calculatePureTagScore(VideoInfo video, Map<String, Integer> tagWeight) {
        int tagScore = 0;
        for (String tag : splitTags(video.getTags())) {
            tagScore += tagWeight.getOrDefault(tag, 0) * 15;
        }
        return tagScore + safe(video.getLikeCount()) + safe(video.getFavoriteCount()) * 2;
    }

    private Map<String, Object> toVideoCard(VideoInfo video, UserVideoState state) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("id", video.getId());
        map.put("title", video.getTitle());
        map.put("coverUrl", video.getCoverUrl());
        map.put("tags", splitTags(video.getTags()));
        map.put("sourcePlatform", video.getSourcePlatform());
        map.put("playMode", video.getPlayMode());
        map.put("playCount", safe(video.getPlayCount()));
        map.put("likeCount", safe(video.getLikeCount()));
        map.put("favoriteCount", safe(video.getFavoriteCount()));
        map.put("liked", state.likedVideoIds.contains(video.getId()));
        map.put("favorited", state.favoriteVideoIds.contains(video.getId()));
        return map;
    }

    private Map<String, Object> toVideoDetail(VideoInfo video, UserVideoState state) {
        Map<String, Object> map = toVideoCard(video, state);
        map.put("description", video.getDescription());
        map.put("playUrl", video.getPlayUrl());
        map.put("embedUrl", video.getEmbedUrl());
        map.put("sourceUrl", video.getSourceUrl());
        map.put("invalidReportCount", safe(video.getInvalidReportCount()));
        return map;
    }

    private UserVideoState buildUserVideoState(Long userId) {
        if (userId == null) {
            return new UserVideoState();
        }
        Set<Long> likedVideoIds = new HashSet<>(likeMapper.listLikedVideoIds(userId));
        Set<Long> favoriteVideoIds = new HashSet<>(favoriteMapper.listFavoriteVideoIds(userId));
        return new UserVideoState(likedVideoIds, favoriteVideoIds);
    }

    private RecommendationProfile buildRecommendationProfile(Long userId) {
        List<VideoInfo> likedVideos = likeMapper.listLikedVideos(userId);
        List<VideoInfo> favoriteVideos = favoriteMapper.listFavoriteVideos(userId);
        List<String> recentPlayedTags = playHistoryMapper.listRecentTags(userId);
        Set<Long> engagedVideoIds = new LinkedHashSet<>();
        engagedVideoIds.addAll(extractVideoIds(likedVideos));
        engagedVideoIds.addAll(extractVideoIds(favoriteVideos));
        engagedVideoIds.addAll(distinctIds(playHistoryMapper.listRecentVideoIds(userId)));
        return new RecommendationProfile(likedVideos, favoriteVideos, recentPlayedTags, engagedVideoIds);
    }

    private List<VideoInfo> filterOutEngagedVideos(List<VideoInfo> videos, Set<Long> engagedVideoIds) {
        if (engagedVideoIds.isEmpty()) {
            return videos;
        }
        List<VideoInfo> filtered = videos.stream()
                .filter(video -> !engagedVideoIds.contains(video.getId()))
                .collect(Collectors.toList());
        return filtered.isEmpty() ? videos : filtered;
    }

    private Set<Long> extractVideoIds(List<VideoInfo> videos) {
        Set<Long> ids = new LinkedHashSet<>();
        for (VideoInfo video : videos) {
            if (video != null && video.getId() != null) {
                ids.add(video.getId());
            }
        }
        return ids;
    }

    private Set<Long> distinctIds(List<Long> videoIds) {
        if (videoIds == null || videoIds.isEmpty()) {
            return Collections.emptySet();
        }
        Set<Long> ids = new LinkedHashSet<>();
        for (Long videoId : videoIds) {
            if (videoId != null) {
                ids.add(videoId);
            }
        }
        return ids;
    }

    private List<Map<String, Object>> paginateVideos(List<VideoInfo> videos,
                                                     UserVideoState state,
                                                     long page,
                                                     long pageSize,
                                                     boolean shuffleCurrentPage) {
        int fromIndex = (int) Math.min((page - 1) * pageSize, videos.size());
        int toIndex = (int) Math.min(fromIndex + pageSize, videos.size());
        List<VideoInfo> pageVideos = new ArrayList<>(videos.subList(fromIndex, toIndex));
        if (shuffleCurrentPage && pageVideos.size() > 1) {
            Collections.shuffle(pageVideos);
        }
        return pageVideos.stream()
                .map(video -> toVideoCard(video, state))
                .collect(Collectors.toList());
    }

    private long normalizePage(long page) {
        return Math.max(page, 1);
    }

    private long normalizePageSize(long pageSize) {
        if (pageSize <= 0) {
            return 12;
        }
        return Math.min(pageSize, 24);
    }

    private int safe(Integer value) {
        return value == null ? 0 : value;
    }

    private long safeLong(Long value) {
        return value == null ? 0L : value;
    }

    private List<String> splitTags(String tags) {
        if (tags == null || tags.trim().isEmpty()) {
            return new ArrayList<>();
        }
        Set<String> set = new TreeSet<>();
        String[] parts = tags.split("[,，]");
        for (String item : parts) {
            String tag = item.trim();
            if (!tag.isEmpty()) {
                set.add(tag);
            }
        }
        return new ArrayList<>(set);
    }

    private String resolveAlgorithm(String algorithm) {
        if (ALGORITHM_CONTENT.equalsIgnoreCase(algorithm)) {
            return ALGORITHM_CONTENT;
        }
        if (ALGORITHM_SIMILAR.equalsIgnoreCase(algorithm)) {
            return ALGORITHM_SIMILAR;
        }
        if (ALGORITHM_PREFERENCE.equalsIgnoreCase(algorithm)) {
            return ALGORITHM_PREFERENCE;
        }
        return ALGORITHM_HYBRID;
    }

    private static class RecommendationProfile {
        private final List<VideoInfo> likedVideos;
        private final List<VideoInfo> favoriteVideos;
        private final List<String> recentPlayedTags;
        private final Set<Long> engagedVideoIds;

        private RecommendationProfile(List<VideoInfo> likedVideos,
                                      List<VideoInfo> favoriteVideos,
                                      List<String> recentPlayedTags,
                                      Set<Long> engagedVideoIds) {
            this.likedVideos = likedVideos;
            this.favoriteVideos = favoriteVideos;
            this.recentPlayedTags = recentPlayedTags;
            this.engagedVideoIds = engagedVideoIds;
        }
    }

    private static class UserVideoState {
        private final Set<Long> likedVideoIds;
        private final Set<Long> favoriteVideoIds;

        private UserVideoState() {
            this(new HashSet<>(), new HashSet<>());
        }

        private UserVideoState(Set<Long> likedVideoIds, Set<Long> favoriteVideoIds) {
            this.likedVideoIds = likedVideoIds;
            this.favoriteVideoIds = favoriteVideoIds;
        }
    }
}
