package com.xiyou.video.mapper;

import com.xiyou.video.domain.VideoInvalidReport;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;
import java.util.Map;

public interface ReportMapper {

    @Insert("insert into video_invalid_report(user_id, video_id, reason, status) values(#{userId}, #{videoId}, #{reason}, 0)")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(VideoInvalidReport report);

    @Select("select count(1) from video_invalid_report where user_id = #{userId} and video_id = #{videoId} and status = 0")
    int countPendingByUser(@Param("userId") Long userId, @Param("videoId") Long videoId);

    @Select("select r.id, r.video_id as videoId, v.title as videoTitle, r.user_id as userId, u.username, r.reason, r.status, r.create_time as createTime " +
            "from video_invalid_report r " +
            "join video_info v on r.video_id = v.id " +
            "join sys_user u on r.user_id = u.id " +
            "order by r.id desc")
    List<Map<String, Object>> listReports();

    @Update("update video_invalid_report set status = #{status}, handle_by = #{handleBy}, handle_time = now() where id = #{id}")
    int handle(@Param("id") Long id, @Param("status") Integer status, @Param("handleBy") Long handleBy);
}
