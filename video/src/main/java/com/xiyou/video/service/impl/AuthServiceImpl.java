package com.xiyou.video.service.impl;

import com.xiyou.video.common.BusinessException;
import com.xiyou.video.common.PasswordUtil;
import com.xiyou.video.domain.SysUser;
import com.xiyou.video.dto.LoginRequest;
import com.xiyou.video.dto.RegisterRequest;
import com.xiyou.video.mapper.UserMapper;
import com.xiyou.video.security.AuthUser;
import com.xiyou.video.security.JwtUtil;
import com.xiyou.video.service.AuthService;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class AuthServiceImpl implements AuthService {

    private final UserMapper userMapper;
    private final JwtUtil jwtUtil;

    public AuthServiceImpl(UserMapper userMapper, JwtUtil jwtUtil) {
        this.userMapper = userMapper;
        this.jwtUtil = jwtUtil;
    }

    @Override
    public Map<String, Object> register(RegisterRequest request) {
        if (userMapper.findByUsername(request.getUsername()) != null) {
            throw new BusinessException("用户名已存在");
        }
        SysUser user = new SysUser();
        user.setUsername(request.getUsername());
        user.setPassword(PasswordUtil.sha256(request.getPassword()));
        user.setRealName(request.getRealName());
        user.setRole("USER");
        user.setStatus(1);
        userMapper.insert(user);
        return buildLoginResult(user);
    }

    @Override
    public Map<String, Object> login(LoginRequest request, boolean adminOnly) {
        SysUser user = userMapper.findByUsername(request.getUsername());
        if (user == null || !user.getPassword().equals(PasswordUtil.sha256(request.getPassword()))) {
            throw new BusinessException("用户名或密码错误");
        }
        if (user.getStatus() == null || user.getStatus() != 1) {
            throw new BusinessException("账号已被禁用");
        }
        if (adminOnly && !"ADMIN".equals(user.getRole()) && !"SUPER_ADMIN".equals(user.getRole())) {
            throw new BusinessException("当前账号不是管理员");
        }
        return buildLoginResult(user);
    }

    private Map<String, Object> buildLoginResult(SysUser user) {
        AuthUser authUser = new AuthUser(user.getId(), user.getUsername(), user.getRole());
        String token = jwtUtil.generateToken(authUser);
        Map<String, Object> result = new HashMap<>();
        result.put("token", token);
        result.put("user", toUserMap(user));
        return result;
    }

    private Map<String, Object> toUserMap(SysUser user) {
        Map<String, Object> map = new HashMap<>();
        map.put("id", user.getId());
        map.put("username", user.getUsername());
        map.put("realName", user.getRealName());
        map.put("avatarUrl", user.getAvatarUrl());
        map.put("role", user.getRole());
        map.put("status", user.getStatus());
        return map;
    }
}
