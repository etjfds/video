package com.xiyou.video.mapper;

import com.xiyou.video.domain.VideoInfo;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

public interface VideoMapper {

    @Insert("insert into video_info(title, cover_url, play_url, embed_url, source_url, description, source_platform, tags, play_mode, status, create_by) " +
            "values(#{title}, #{coverUrl}, #{playUrl}, #{embedUrl}, #{sourceUrl}, #{description}, #{sourcePlatform}, #{tags}, #{playMode}, #{status}, #{createBy})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(VideoInfo videoInfo);

    @Update("update video_info set title = #{title}, cover_url = #{coverUrl}, play_url = #{playUrl}, embed_url = #{embedUrl}, " +
            "source_url = #{sourceUrl}, description = #{description}, source_platform = #{sourcePlatform}, tags = #{tags}, " +
            "play_mode = #{playMode}, status = #{status} where id = #{id}")
    int update(VideoInfo videoInfo);

    @Select("select * from video_info where id = #{id} limit 1")
    VideoInfo findById(@Param("id") Long id);

    @Select("select * from video_info where id = #{id} and status = 1 limit 1")
    VideoInfo findPublishedById(@Param("id") Long id);

    @Select("<script>" +
            "select * from video_info where status = 1 " +
            "<if test='keyword != null and keyword != \"\"'>" +
            "and (title like concat('%', #{keyword}, '%') or tags like concat('%', #{keyword}, '%')) " +
            "</if>" +
            "order by create_time desc " +
            "limit #{limit} offset #{offset}" +
            "</script>")
    List<VideoInfo> listPublished(@Param("keyword") String keyword,
                                  @Param("offset") long offset,
                                  @Param("limit") long limit);

    @Select("<script>" +
            "select count(1) from video_info where status = 1 " +
            "<if test='keyword != null and keyword != \"\"'>" +
            "and (title like concat('%', #{keyword}, '%') or tags like concat('%', #{keyword}, '%')) " +
            "</if>" +
            "</script>")
    long countPublished(@Param("keyword") String keyword);

    @Select("<script>" +
            "select * from video_info where 1=1 " +
            "<if test='keyword != null and keyword != \"\"'>" +
            "and (title like concat('%', #{keyword}, '%') or tags like concat('%', #{keyword}, '%')) " +
            "</if>" +
            "<if test='status != null'>" +
            "and status = #{status} " +
            "</if>" +
            "order by id desc " +
            "limit #{limit} offset #{offset}" +
            "</script>")
    List<VideoInfo> listManage(@Param("keyword") String keyword,
                               @Param("status") Integer status,
                               @Param("offset") long offset,
                               @Param("limit") long limit);

    @Select("<script>" +
            "select count(1) from video_info where 1=1 " +
            "<if test='keyword != null and keyword != \"\"'>" +
            "and (title like concat('%', #{keyword}, '%') or tags like concat('%', #{keyword}, '%')) " +
            "</if>" +
            "<if test='status != null'>" +
            "and status = #{status} " +
            "</if>" +
            "</script>")
    long countManage(@Param("keyword") String keyword, @Param("status") Integer status);

    @Select("select * from video_info where status = 1 order by (play_count + like_count * 3 + favorite_count * 5 - invalid_report_count * 2) desc, id desc limit #{limit}")
    List<VideoInfo> listHot(@Param("limit") int limit);

    @Select("select * from video_info where status = 1")
    List<VideoInfo> listAllPublished();

    @Update("update video_info set play_count = play_count + 1 where id = #{id}")
    int incrementPlayCount(@Param("id") Long id);

    @Update("update video_info set like_count = greatest(like_count + #{delta}, 0) where id = #{id}")
    int incrementLikeCount(@Param("id") Long id, @Param("delta") int delta);

    @Update("update video_info set favorite_count = greatest(favorite_count + #{delta}, 0) where id = #{id}")
    int incrementFavoriteCount(@Param("id") Long id, @Param("delta") int delta);

    @Update("update video_info set invalid_report_count = invalid_report_count + 1 where id = #{id}")
    int incrementInvalidReportCount(@Param("id") Long id);
}
