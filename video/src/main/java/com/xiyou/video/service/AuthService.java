package com.xiyou.video.service;

import com.xiyou.video.dto.LoginRequest;
import com.xiyou.video.dto.RegisterRequest;

import java.util.Map;

public interface AuthService {

    Map<String, Object> register(RegisterRequest request);

    Map<String, Object> login(LoginRequest request, boolean adminOnly);
}
