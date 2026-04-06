package com.xiyou.video.service;

import com.xiyou.video.dto.ProfileUpdateRequest;

import java.util.Map;

public interface UserService {

    Map<String, Object> getProfile(Long userId);

    Map<String, Object> updateProfile(Long userId, ProfileUpdateRequest request);

    Map<String, Object> uploadAvatar(Long userId, String originalFilename, byte[] bytes);
}
