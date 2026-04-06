package com.xiyou.video.mapper;

import com.xiyou.video.domain.SysUser;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

public interface UserMapper {

    @Select("select * from sys_user where username = #{username} limit 1")
    SysUser findByUsername(@Param("username") String username);

    @Select("select * from sys_user where id = #{id} limit 1")
    SysUser findById(@Param("id") Long id);

    @Insert("insert into sys_user(username, password, real_name, avatar_url, role, status) " +
            "values(#{username}, #{password}, #{realName}, #{avatarUrl}, #{role}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(SysUser user);

    @Update("update sys_user set real_name = #{realName}, avatar_url = #{avatarUrl} where id = #{id}")
    int updateProfile(SysUser user);

    @Update("update sys_user set status = #{status} where id = #{id}")
    int updateStatus(@Param("id") Long id, @Param("status") Integer status);

    @Select("<script>" +
            "select * from sys_user " +
            "where 1=1 " +
            "<if test='keyword != null and keyword != \"\"'>" +
            "and (username like concat('%', #{keyword}, '%') or real_name like concat('%', #{keyword}, '%')) " +
            "</if>" +
            "<if test='role != null and role != \"\"'>" +
            "and role = #{role} " +
            "</if>" +
            "order by id desc " +
            "limit #{limit} offset #{offset}" +
            "</script>")
    List<SysUser> listUsers(@Param("keyword") String keyword,
                            @Param("role") String role,
                            @Param("offset") long offset,
                            @Param("limit") long limit);

    @Select("<script>" +
            "select count(1) from sys_user " +
            "where 1=1 " +
            "<if test='keyword != null and keyword != \"\"'>" +
            "and (username like concat('%', #{keyword}, '%') or real_name like concat('%', #{keyword}, '%')) " +
            "</if>" +
            "<if test='role != null and role != \"\"'>" +
            "and role = #{role} " +
            "</if>" +
            "</script>")
    long countUsers(@Param("keyword") String keyword, @Param("role") String role);
}
