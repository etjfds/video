package com.xiyou.video.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Param;

public interface AdminLogMapper {

    @Insert("insert into sys_admin_operation_log(admin_id, operation_type, target_id, content) values(#{adminId}, #{operationType}, #{targetId}, #{content})")
    int insert(@Param("adminId") Long adminId,
               @Param("operationType") String operationType,
               @Param("targetId") Long targetId,
               @Param("content") String content);
}
