CREATE DATABASE IF NOT EXISTS video_portal DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE video_portal;

DROP TABLE IF EXISTS sys_admin_operation_log;
DROP TABLE IF EXISTS video_invalid_report;
DROP TABLE IF EXISTS video_play_history;
DROP TABLE IF EXISTS user_favorite;
DROP TABLE IF EXISTS user_like;
DROP TABLE IF EXISTS video_info;
DROP TABLE IF EXISTS sys_user;

CREATE TABLE sys_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户主键ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '登录用户名',
    password VARCHAR(128) NOT NULL COMMENT '密码摘要，使用SHA-256存储',
    real_name VARCHAR(50) NOT NULL COMMENT '用户真实姓名',
    avatar_url VARCHAR(255) COMMENT '头像访问地址',
    role VARCHAR(20) NOT NULL COMMENT '角色：USER/ADMIN/SUPER_ADMIN',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态：1启用，0禁用',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) COMMENT='系统用户表';

CREATE TABLE video_info (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '视频主键ID',
    title VARCHAR(120) NOT NULL COMMENT '视频标题',
    cover_url VARCHAR(255) COMMENT '视频封面地址',
    play_url VARCHAR(500) COMMENT '直链播放地址，DIRECT模式使用',
    embed_url VARCHAR(500) COMMENT '嵌入播放地址，EMBED模式使用',
    source_url VARCHAR(500) COMMENT '原站详情页或原始来源地址',
    description TEXT COMMENT '视频简介或原始文案',
    source_platform VARCHAR(50) COMMENT '来源平台，例如WEIBO、YOUTUBE',
    tags VARCHAR(255) COMMENT '视频标签，多个标签用逗号分隔',
    play_mode VARCHAR(20) NOT NULL DEFAULT 'LINK' COMMENT '播放模式：DIRECT/EMBED/LINK',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '状态：0草稿，1上架，2下架',
    play_count INT NOT NULL DEFAULT 0 COMMENT '播放次数',
    like_count INT NOT NULL DEFAULT 0 COMMENT '点赞次数',
    favorite_count INT NOT NULL DEFAULT 0 COMMENT '收藏次数',
    invalid_report_count INT NOT NULL DEFAULT 0 COMMENT '失效反馈次数',
    create_by BIGINT COMMENT '创建人ID，通常为管理员ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) COMMENT='视频信息表';

CREATE TABLE user_like (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '点赞记录主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    video_id BIGINT NOT NULL COMMENT '视频ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
    UNIQUE KEY uk_user_video_like (user_id, video_id)
) COMMENT='用户点赞记录表';

CREATE TABLE user_favorite (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '收藏记录主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    video_id BIGINT NOT NULL COMMENT '视频ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
    UNIQUE KEY uk_user_video_favorite (user_id, video_id)
) COMMENT='用户收藏记录表';

CREATE TABLE video_play_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '播放记录主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    video_id BIGINT NOT NULL COMMENT '视频ID',
    play_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '实际播放时间',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) COMMENT='视频播放历史表';

CREATE TABLE video_invalid_report (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '失效反馈主键ID',
    user_id BIGINT NOT NULL COMMENT '反馈用户ID',
    video_id BIGINT NOT NULL COMMENT '被反馈视频ID',
    reason VARCHAR(255) COMMENT '反馈原因',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '处理状态：0待处理，1已确认，2已忽略',
    handle_by BIGINT COMMENT '处理人管理员ID',
    handle_time DATETIME COMMENT '处理时间',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '反馈时间'
) COMMENT='视频失效反馈表';

CREATE TABLE sys_admin_operation_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '操作日志主键ID',
    admin_id BIGINT NOT NULL COMMENT '管理员ID',
    operation_type VARCHAR(50) NOT NULL COMMENT '操作类型',
    target_id BIGINT COMMENT '被操作对象ID',
    content VARCHAR(255) NOT NULL COMMENT '操作内容描述',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间'
) COMMENT='管理员操作日志表';

INSERT INTO sys_user (username, password, real_name, role, status)
VALUES
('superadmin', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '系统超管', 'SUPER_ADMIN', 1),
('admin', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '平台管理员', 'ADMIN', 1),
('demo', '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92', '演示用户', 'USER', 1);

INSERT INTO video_info
(title, cover_url, play_url, embed_url, source_url, description, source_platform, tags, play_mode, status, create_by)
VALUES
('站内直链示例', 'https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?auto=format&fit=crop&w=800&q=80',
 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4', NULL,
 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4',
 '使用原生 video 播放的示例视频。', 'DIRECT', '自然,风景,演示', 'DIRECT', 1, 2),
('微博外链示例', 'https://images.unsplash.com/photo-1516321497487-e288fb19713f?auto=format&fit=crop&w=800&q=80',
 NULL, NULL,
 'https://video.weibo.com/show?fid=1034:5260727951228931',
 '微博详情页通常不适合直接 iframe 嵌入，这里按跳转原站播放处理。', 'WEIBO', '资讯,热点,微博', 'LINK', 1, 2),
('可嵌入示例', 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=80',
 NULL, 'https://www.youtube.com/embed/jNQXAC9IVRw',
 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
 '使用 iframe 嵌入播放器的示例。', 'YOUTUBE', '教育,演示,嵌入', 'EMBED', 1, 2);
