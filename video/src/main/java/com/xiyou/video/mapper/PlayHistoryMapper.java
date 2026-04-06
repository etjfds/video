package com.xiyou.video.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

public interface PlayHistoryMapper {

    @Insert("insert into video_play_history(user_id, video_id, play_time) values(#{userId}, #{videoId}, now())")
    int insert(@Param("userId") Long userId, @Param("videoId") Long videoId);

    @Select("select v.tags from video_play_history h join video_info v on h.video_id = v.id where h.user_id = #{userId} order by h.id desc limit 20")
    List<String> listRecentTags(@Param("userId") Long userId);

    @Select("select video_id from video_play_history where user_id = #{userId} order by id desc limit 30")
    List<Long> listRecentVideoIds(@Param("userId") Long userId);

    @Select("<script>" +
            "select distinct user_id from video_play_history where video_id in " +
            "<foreach collection='videoIds' item='videoId' open='(' separator=',' close=')'>" +
            "#{videoId}" +
            "</foreach>" +
            "</script>")
    List<Long> listUserIdsByVideoIds(@Param("videoIds") List<Long> videoIds);

    @Select("<script>" +
            "select video_id from video_play_history where user_id in " +
            "<foreach collection='userIds' item='userId' open='(' separator=',' close=')'>" +
            "#{userId}" +
            "</foreach> order by id desc" +
            "</script>")
    List<Long> listPlayedVideoIdsByUsers(@Param("userIds") List<Long> userIds);
}
