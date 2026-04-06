package com.xiyou.video.security;

import com.xiyou.video.common.BusinessException;

public final class AuthContext {

    private static final ThreadLocal<AuthUser> HOLDER = new ThreadLocal<>();

    private AuthContext() {
    }

    public static void set(AuthUser user) {
        HOLDER.set(user);
    }

    public static AuthUser get() {
        return HOLDER.get();
    }

    public static Long requireUserId() {
        AuthUser user = get();
        if (user == null) {
            throw new BusinessException("请先登录");
        }
        return user.getId();
    }

    public static AuthUser requireUser() {
        AuthUser user = get();
        if (user == null) {
            throw new BusinessException("请先登录");
        }
        return user;
    }

    public static void requireAdmin() {
        AuthUser user = requireUser();
        if (!"ADMIN".equals(user.getRole()) && !"SUPER_ADMIN".equals(user.getRole())) {
            throw new BusinessException("无管理员权限");
        }
    }

    public static void requireSuperAdmin() {
        AuthUser user = requireUser();
        if (!"SUPER_ADMIN".equals(user.getRole())) {
            throw new BusinessException("仅超管可操作");
        }
    }

    public static void clear() {
        HOLDER.remove();
    }
}
