package com.xiyou.video.mapper;

import com.xiyou.video.domain.VideoInfo;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

public interface LikeMapper {

    @Select("select count(1) from user_like where user_id = #{userId} and video_id = #{videoId}")
    int count(@Param("userId") Long userId, @Param("videoId") Long videoId);

    @Insert("insert into user_like(user_id, video_id) values(#{userId}, #{videoId})")
    int insert(@Param("userId") Long userId, @Param("videoId") Long videoId);

    @Delete("delete from user_like where user_id = #{userId} and video_id = #{videoId}")
    int delete(@Param("userId") Long userId, @Param("videoId") Long videoId);

    @Select("select video_id from user_like where user_id = #{userId}")
    List<Long> listLikedVideoIds(@Param("userId") Long userId);

    @Select("select v.* from user_like l join video_info v on l.video_id = v.id where l.user_id = #{userId} order by l.id desc")
    List<VideoInfo> listLikedVideos(@Param("userId") Long userId);

    @Select("<script>" +
            "select distinct user_id from user_like where video_id in " +
            "<foreach collection='videoIds' item='videoId' open='(' separator=',' close=')'>" +
            "#{videoId}" +
            "</foreach>" +
            "</script>")
    List<Long> listUserIdsByVideoIds(@Param("videoIds") List<Long> videoIds);

    @Select("<script>" +
            "select video_id from user_like where user_id in " +
            "<foreach collection='userIds' item='userId' open='(' separator=',' close=')'>" +
            "#{userId}" +
            "</foreach>" +
            "</script>")
    List<Long> listLikedVideoIdsByUsers(@Param("userIds") List<Long> userIds);
}
