package com.xiyou.video.service.impl;

import com.xiyou.video.common.PageResult;
import com.xiyou.video.common.BusinessException;
import com.xiyou.video.common.PasswordUtil;
import com.xiyou.video.domain.SysUser;
import com.xiyou.video.domain.VideoInfo;
import com.xiyou.video.dto.AdminCreateRequest;
import com.xiyou.video.dto.VideoPublishRequest;
import com.xiyou.video.mapper.AdminLogMapper;
import com.xiyou.video.mapper.ReportMapper;
import com.xiyou.video.mapper.UserMapper;
import com.xiyou.video.mapper.VideoMapper;
import com.xiyou.video.service.AdminService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class AdminServiceImpl implements AdminService {

    private final UserMapper userMapper;
    private final VideoMapper videoMapper;
    private final ReportMapper reportMapper;
    private final AdminLogMapper adminLogMapper;
    private final String imageDir;

    public AdminServiceImpl(UserMapper userMapper,
                            VideoMapper videoMapper,
                            ReportMapper reportMapper,
                            AdminLogMapper adminLogMapper,
                            @Value("${app.file.image-dir}") String imageDir) {
        this.userMapper = userMapper;
        this.videoMapper = videoMapper;
        this.reportMapper = reportMapper;
        this.adminLogMapper = adminLogMapper;
        this.imageDir = imageDir;
    }

    @Override
    @Transactional
    public Map<String, Object> createAdmin(Long operatorId, AdminCreateRequest request) {
        if (userMapper.findByUsername(request.getUsername()) != null) {
            throw new BusinessException("用户名已存在");
        }
        SysUser user = new SysUser();
        user.setUsername(request.getUsername());
        user.setPassword(PasswordUtil.sha256(request.getPassword()));
        user.setRealName(request.getRealName());
        user.setRole("ADMIN");
        user.setStatus(1);
        userMapper.insert(user);
        adminLogMapper.insert(operatorId, "CREATE_ADMIN", user.getId(), "新增管理员:" + user.getUsername());
        Map<String, Object> result = new HashMap<>();
        result.put("id", user.getId());
        result.put("username", user.getUsername());
        result.put("realName", user.getRealName());
        result.put("role", user.getRole());
        result.put("status", user.getStatus());
        return result;
    }

    @Override
    @Transactional(readOnly = true)
    public PageResult<Map<String, Object>> listUsers(String keyword, String role, long page, long pageSize) {
        long safePage = normalizePage(page);
        long safePageSize = normalizePageSize(pageSize);
        long offset = (safePage - 1) * safePageSize;
        List<Map<String, Object>> records = userMapper.listUsers(keyword, role, offset, safePageSize).stream().map(user -> {
            Map<String, Object> map = new HashMap<>();
            map.put("id", user.getId());
            map.put("username", user.getUsername());
            map.put("realName", user.getRealName());
            map.put("role", user.getRole());
            map.put("status", user.getStatus());
            map.put("createTime", user.getCreateTime());
            return map;
        }).collect(Collectors.toList());
        long total = userMapper.countUsers(keyword, role);
        return new PageResult<>(records, total, safePage, safePageSize);
    }

    @Override
    @Transactional
    public void updateUserStatus(Long operatorId, Long userId, Integer status) {
        SysUser target = userMapper.findById(userId);
        if (target == null) {
            throw new BusinessException("用户不存在");
        }
        if (!"USER".equals(target.getRole())) {
            throw new BusinessException("当前版本只允许启停普通用户");
        }
        userMapper.updateStatus(userId, status);
        adminLogMapper.insert(operatorId, "UPDATE_USER_STATUS", userId, "更新用户状态为:" + status);
    }

    @Override
    @Transactional(readOnly = true)
    public Map<String, Object> getVideoDetail(Long videoId) {
        VideoInfo video = videoMapper.findById(videoId);
        if (video == null) {
            throw new BusinessException("视频不存在");
        }
        return buildVideoDetail(video);
    }

    @Override
    @Transactional
    public Map<String, Object> uploadVideoCover(Long operatorId, String originalFilename, byte[] bytes) {
        if (bytes == null || bytes.length == 0) {
            throw new BusinessException("上传文件不能为空");
        }
        String extension = getExtension(originalFilename);
        if (!isAllowedImageExtension(extension)) {
            throw new BusinessException("仅支持 jpg、jpeg、png、gif、webp 图片");
        }
        try {
            Path directory = Paths.get(imageDir).toAbsolutePath().normalize();
            Files.createDirectories(directory);
            String filename = "cover_" + operatorId + "_" + UUID.randomUUID().toString().replace("-", "") + extension;
            Path target = directory.resolve(filename);
            Files.write(target, bytes, StandardOpenOption.CREATE_NEW);
            Map<String, Object> result = new HashMap<>();
            result.put("coverUrl", "/img/" + filename);
            return result;
        } catch (IOException exception) {
            throw new BusinessException("封面上传失败");
        }
    }

    @Override
    @Transactional
    public Map<String, Object> saveVideo(Long operatorId, Long videoId, VideoPublishRequest request) {
        VideoInfo video;
        if (videoId == null) {
            video = new VideoInfo();
            applyCreateFields(video, request);
        } else {
            video = videoMapper.findById(videoId);
            if (video == null) {
                throw new BusinessException("视频不存在");
            }
            applyUpdateFields(video, request);
        }
        validateVideo(video);
        if (videoId == null) {
            video.setCreateBy(operatorId);
            videoMapper.insert(video);
            adminLogMapper.insert(operatorId, "CREATE_VIDEO", video.getId(), "新增视频:" + video.getTitle());
        } else {
            videoMapper.update(video);
            adminLogMapper.insert(operatorId, "UPDATE_VIDEO", video.getId(), "编辑视频:" + video.getTitle());
        }
        Map<String, Object> result = new HashMap<>();
        result.put("id", video.getId());
        result.put("title", video.getTitle());
        result.put("playMode", video.getPlayMode());
        result.put("status", video.getStatus());
        return result;
    }

    @Override
    @Transactional(readOnly = true)
    public PageResult<Map<String, Object>> listVideos(String keyword, Integer status, long page, long pageSize) {
        long safePage = normalizePage(page);
        long safePageSize = normalizePageSize(pageSize);
        long offset = (safePage - 1) * safePageSize;
        List<Map<String, Object>> records = videoMapper.listManage(keyword, status, offset, safePageSize).stream().map(video -> {
            Map<String, Object> map = new HashMap<>();
            map.put("id", video.getId());
            map.put("title", video.getTitle());
            map.put("playMode", video.getPlayMode());
            map.put("status", video.getStatus());
            map.put("sourcePlatform", video.getSourcePlatform());
            map.put("playCount", video.getPlayCount());
            map.put("likeCount", video.getLikeCount());
            map.put("favoriteCount", video.getFavoriteCount());
            map.put("invalidReportCount", video.getInvalidReportCount());
            map.put("updateTime", video.getUpdateTime());
            return map;
        }).collect(Collectors.toList());
        long total = videoMapper.countManage(keyword, status);
        return new PageResult<>(records, total, safePage, safePageSize);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Map<String, Object>> listReports() {
        return reportMapper.listReports();
    }

    @Override
    @Transactional
    public void handleReport(Long operatorId, Long reportId, Integer status) {
        reportMapper.handle(reportId, status, operatorId);
        adminLogMapper.insert(operatorId, "HANDLE_REPORT", reportId, "处理失效反馈，状态:" + status);
    }

    private void applyCreateFields(VideoInfo video, VideoPublishRequest request) {
        video.setTitle(clean(request.getTitle()));
        video.setCoverUrl(clean(request.getCoverUrl()));
        video.setPlayUrl(clean(request.getPlayUrl()));
        video.setEmbedUrl(clean(request.getEmbedUrl()));
        video.setSourceUrl(clean(request.getSourceUrl()));
        video.setDescription(clean(request.getDescription()));
        video.setSourcePlatform(clean(request.getSourcePlatform()));
        video.setTags(clean(request.getTags()));
        video.setPlayMode(clean(request.getPlayMode()));
        video.setStatus(request.getStatus());
    }

    private void applyUpdateFields(VideoInfo video, VideoPublishRequest request) {
        if (isNotBlank(request.getTitle())) {
            video.setTitle(clean(request.getTitle()));
        }
        if (isNotBlank(request.getCoverUrl())) {
            video.setCoverUrl(clean(request.getCoverUrl()));
        }
        if (isNotBlank(request.getPlayUrl())) {
            video.setPlayUrl(clean(request.getPlayUrl()));
        }
        if (isNotBlank(request.getEmbedUrl())) {
            video.setEmbedUrl(clean(request.getEmbedUrl()));
        }
        if (isNotBlank(request.getSourceUrl())) {
            video.setSourceUrl(clean(request.getSourceUrl()));
        }
        if (isNotBlank(request.getDescription())) {
            video.setDescription(clean(request.getDescription()));
        }
        if (isNotBlank(request.getSourcePlatform())) {
            video.setSourcePlatform(clean(request.getSourcePlatform()));
        }
        if (isNotBlank(request.getTags())) {
            video.setTags(clean(request.getTags()));
        }
        if (isNotBlank(request.getPlayMode())) {
            video.setPlayMode(clean(request.getPlayMode()));
        }
        if (request.getStatus() != null) {
            video.setStatus(request.getStatus());
        }
    }

    private void validateVideo(VideoInfo video) {
        if (isBlank(video.getTitle())) {
            throw new BusinessException("标题不能为空");
        }
        String playMode = video.getPlayMode();
        if (!"DIRECT".equals(playMode) && !"EMBED".equals(playMode) && !"LINK".equals(playMode)) {
            throw new BusinessException("播放模式仅支持 DIRECT / EMBED / LINK");
        }
        if (video.getStatus() == null) {
            throw new BusinessException("状态不能为空");
        }
        if ("DIRECT".equals(playMode) && isBlank(video.getPlayUrl())) {
            throw new BusinessException("DIRECT 模式必须填写 playUrl");
        }
        if ("EMBED".equals(playMode) && isBlank(video.getEmbedUrl())) {
            throw new BusinessException("EMBED 模式必须填写 embedUrl");
        }
        if ("LINK".equals(playMode) && isBlank(video.getSourceUrl()) && isBlank(video.getPlayUrl())) {
            throw new BusinessException("LINK 模式必须至少填写 sourceUrl 或 playUrl");
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private boolean isNotBlank(String value) {
        return !isBlank(value);
    }

    private String clean(String value) {
        return isBlank(value) ? null : value.trim();
    }

    private Map<String, Object> buildVideoDetail(VideoInfo video) {
        Map<String, Object> map = new HashMap<>();
        map.put("id", video.getId());
        map.put("title", video.getTitle());
        map.put("coverUrl", video.getCoverUrl());
        map.put("playUrl", video.getPlayUrl());
        map.put("embedUrl", video.getEmbedUrl());
        map.put("sourceUrl", video.getSourceUrl());
        map.put("description", video.getDescription());
        map.put("sourcePlatform", video.getSourcePlatform());
        map.put("tags", video.getTags());
        map.put("playMode", video.getPlayMode());
        map.put("status", video.getStatus());
        map.put("playCount", video.getPlayCount());
        map.put("likeCount", video.getLikeCount());
        map.put("favoriteCount", video.getFavoriteCount());
        map.put("invalidReportCount", video.getInvalidReportCount());
        return map;
    }

    private String getExtension(String originalFilename) {
        if (originalFilename == null || !originalFilename.contains(".")) {
            return ".jpg";
        }
        return originalFilename.substring(originalFilename.lastIndexOf('.')).toLowerCase();
    }

    private boolean isAllowedImageExtension(String extension) {
        return ".jpg".equals(extension)
                || ".jpeg".equals(extension)
                || ".png".equals(extension)
                || ".gif".equals(extension)
                || ".webp".equals(extension);
    }

    private long normalizePage(long page) {
        return Math.max(page, 1);
    }

    private long normalizePageSize(long pageSize) {
        if (pageSize <= 0) {
            return 10;
        }
        return Math.min(pageSize, 20);
    }
}
