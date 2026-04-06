package com.xiyou.video.service.impl;

import com.xiyou.video.common.BusinessException;
import com.xiyou.video.domain.SysUser;
import com.xiyou.video.domain.VideoInfo;
import com.xiyou.video.dto.ProfileUpdateRequest;
import com.xiyou.video.mapper.FavoriteMapper;
import com.xiyou.video.mapper.LikeMapper;
import com.xiyou.video.mapper.UserMapper;
import com.xiyou.video.service.UserService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class UserServiceImpl implements UserService {

    private final UserMapper userMapper;
    private final LikeMapper likeMapper;
    private final FavoriteMapper favoriteMapper;
    private final String imageDir;

    public UserServiceImpl(UserMapper userMapper,
                           LikeMapper likeMapper,
                           FavoriteMapper favoriteMapper,
                           @org.springframework.beans.factory.annotation.Value("${app.file.image-dir}") String imageDir) {
        this.userMapper = userMapper;
        this.likeMapper = likeMapper;
        this.favoriteMapper = favoriteMapper;
        this.imageDir = imageDir;
    }

    @Override
    @Transactional(readOnly = true)
    public Map<String, Object> getProfile(Long userId) {
        SysUser user = userMapper.findById(userId);
        if (user == null) {
            throw new BusinessException("用户不存在");
        }
        Map<String, Object> result = new HashMap<>();
        result.put("id", user.getId());
        result.put("username", user.getUsername());
        result.put("realName", user.getRealName());
        result.put("avatarUrl", user.getAvatarUrl());
        result.put("role", user.getRole());
        result.put("status", user.getStatus());
        List<VideoInfo> likes = likeMapper.listLikedVideos(userId);
        List<VideoInfo> favorites = favoriteMapper.listFavoriteVideos(userId);
        Set<Long> likedVideoIds = likes.stream().map(VideoInfo::getId).collect(Collectors.toCollection(HashSet::new));
        Set<Long> favoriteVideoIds = favorites.stream().map(VideoInfo::getId).collect(Collectors.toCollection(HashSet::new));
        result.put("myLikes", likes.stream()
                .map(video -> simpleVideo(video, likedVideoIds, favoriteVideoIds))
                .collect(Collectors.toList()));
        result.put("myFavorites", favorites.stream()
                .map(video -> simpleVideo(video, likedVideoIds, favoriteVideoIds))
                .collect(Collectors.toList()));
        return result;
    }

    @Override
    @Transactional
    public Map<String, Object> updateProfile(Long userId, ProfileUpdateRequest request) {
        SysUser user = userMapper.findById(userId);
        if (user == null) {
            throw new BusinessException("用户不存在");
        }
        user.setRealName(request.getRealName());
        user.setAvatarUrl(request.getAvatarUrl());
        userMapper.updateProfile(user);
        return getProfile(userId);
    }

    @Override
    @Transactional
    public Map<String, Object> uploadAvatar(Long userId, String originalFilename, byte[] bytes) {
        SysUser user = userMapper.findById(userId);
        if (user == null) {
            throw new BusinessException("用户不存在");
        }
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
            String filename = "avatar_" + userId + "_" + UUID.randomUUID().toString().replace("-", "") + extension;
            Path target = directory.resolve(filename);
            Files.write(target, bytes, StandardOpenOption.CREATE_NEW);
            user.setAvatarUrl("/img/" + filename);
            userMapper.updateProfile(user);
            return getProfile(userId);
        } catch (IOException exception) {
            throw new BusinessException("头像上传失败");
        }
    }

    private Map<String, Object> simpleVideo(VideoInfo videoInfo, Set<Long> likedVideoIds, Set<Long> favoriteVideoIds) {
        Map<String, Object> map = new HashMap<>();
        map.put("id", videoInfo.getId());
        map.put("title", videoInfo.getTitle());
        map.put("coverUrl", videoInfo.getCoverUrl());
        map.put("playMode", videoInfo.getPlayMode());
        map.put("sourcePlatform", videoInfo.getSourcePlatform());
        map.put("playCount", videoInfo.getPlayCount() != null ? videoInfo.getPlayCount() : 0);
        map.put("likeCount", videoInfo.getLikeCount() != null ? videoInfo.getLikeCount() : 0);
        map.put("favoriteCount", videoInfo.getFavoriteCount() != null ? videoInfo.getFavoriteCount() : 0);
        map.put("tags", splitTags(videoInfo.getTags()));
        map.put("liked", likedVideoIds.contains(videoInfo.getId()));
        map.put("favorited", favoriteVideoIds.contains(videoInfo.getId()));
        return map;
    }

    private List<String> splitTags(String tags) {
        if (tags == null || tags.trim().isEmpty()) {
            return new java.util.ArrayList<>();
        }
        java.util.Set<String> set = new java.util.TreeSet<>();
        String[] parts = tags.split("[,，]");
        for (String item : parts) {
            String tag = item.trim();
            if (!tag.isEmpty()) {
                set.add(tag);
            }
        }
        return new java.util.ArrayList<>(set);
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
}
