import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
import warnings
import pickle
import json
from datetime import datetime

warnings.filterwarnings('ignore')

# ===================== 1. 核心配置（统一路径+适配混合加权） =====================
PROCESSED_DATA_DIR = r"D:\xx\毕设\pythonProject\processed_data"
MODEL_SAVE_DIR = r"D:\xx\毕设\pythonProject\saved_models\cbr"
# 关键：统一实时行为文件路径（与CF保持一致）
REAL_TIME_BEHAVIOR_PATH = r"D:\xx\毕设\pythonProject\saved_models\cf\real_time_behavior.json"
RECOMMEND_TOP_N = 10
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

if not os.path.exists(MODEL_SAVE_DIR):
    os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

# 最优参数组合
BEST_FEATURE_WEIGHTS = {"user_cate_prefer_score": 0.6, "cate_play_ratio": 0.2, "video_popularity_score": 0.2}
BEST_DIVERSITY_RATIO = 0.0
CBR_MODULE_WEIGHT = 0.2  # 匹配混合加权权重

# 全局变量存储模型数据
global_model_data = {}


# ===================== 2. 工具函数=====================
def write_real_time_behavior(user_id, video_id, behavior_type, weight):
    # 单条行为数据（包含user_id，纯列表格式）
    behavior_data = {
        "user_id": str(user_id),  # 统一为字符串，避免类型冲突
        "video_id": str(video_id),  # 统一为字符串
        "behavior_type": behavior_type,
        "weight": weight,
        "behavior_time": datetime.now().strftime("%Y-%m-%d")
    }

    # 读取现有文件
    if os.path.exists(REAL_TIME_BEHAVIOR_PATH):
        with open(REAL_TIME_BEHAVIOR_PATH, "r", encoding="utf-8") as f:
            try:
                real_time_data = json.load(f)
                if isinstance(real_time_data, dict):
                    real_time_data = []
            except json.JSONDecodeError:
                real_time_data = []
    else:
        real_time_data = []

    # 去重逻辑（仅针对点赞/收藏）
    if behavior_type in ["点赞", "收藏"]:
        real_time_data = [
            b for b in real_time_data
            if not (b.get("user_id") == str(user_id) and
                    b.get("video_id") == str(video_id) and
                    b.get("behavior_type") == behavior_type)
        ]
    # 观看行为不查重，直接保留
    # 追加新行为到列表末尾（逐条追加）
    real_time_data.append(behavior_data)

    # 写入文件
    with open(REAL_TIME_BEHAVIOR_PATH, "w", encoding="utf-8") as f:
        json.dump(real_time_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 实时行为已写入：用户{user_id} - 视频{video_id} - {behavior_type}（权重{weight}）")


def get_real_time_behavior(user_id):
    if not os.path.exists(REAL_TIME_BEHAVIOR_PATH):
        return []

    with open(REAL_TIME_BEHAVIOR_PATH, "r", encoding="utf-8") as f:
        try:
            real_time_data = json.load(f)
            # 强制转为列表（兼容旧格式）
            if not isinstance(real_time_data, list):
                real_time_data = []
        except json.JSONDecodeError:
            real_time_data = []

    # 筛选指定用户的行为，并按时间排序（最新的在最后）
    user_behaviors = [b for b in real_time_data if b.get("user_id") == str(user_id)]
    user_behaviors.sort(key=lambda x: x.get("behavior_time", ""))

    return user_behaviors


def is_user_converted_to_old(user_id):
    """
    判断新用户是否累积≥3条行为，转为老用户
    """
    # 1. 原本就是老用户 → 直接返回True
    if "user_feature_matrix" in global_model_data and str(user_id) in global_model_data["user_feature_matrix"].index:
        return True
    # 2. 新用户：统计实时行为数量
    real_time_behaviors = get_real_time_behavior(user_id)
    return len(real_time_behaviors) >= 3


def build_new_user_feature(user_id):
    """为累积≥3条行为的新用户构建特征矩阵"""
    video_df = global_model_data["video_df"]
    all_categories = global_model_data["all_categories"]

    real_time_behaviors = get_real_time_behavior(user_id)
    rt_video_ids = [b["video_id"] for b in real_time_behaviors]
    rt_weights = [b["weight"] for b in real_time_behaviors]

    # 1. 构建分类偏好特征
    rt_video_info = video_df[video_df["video_id"].isin(rt_video_ids)].copy()
    rt_video_info = rt_video_info.reset_index(drop=True)
    if len(rt_weights) >= len(rt_video_info):
        rt_video_info["behavior_weight"] = rt_weights[:len(rt_video_info)]
    else:
        rt_video_info["behavior_weight"] = rt_weights + [0.1] * (len(rt_video_info) - len(rt_weights))

    # 计算加权分类偏好
    cate_prefer = {}
    for cate in all_categories:
        cate_videos = rt_video_info[rt_video_info["content_category"] == cate]
        if not cate_videos.empty:
            cate_prefer[cate] = (cate_videos["behavior_weight"] * BEST_FEATURE_WEIGHTS["user_cate_prefer_score"]).sum()
        else:
            cate_prefer[cate] = 0.0

    # 2. 构建视频质量特征
    rt_video_info["weighted_cate_play"] = rt_video_info["category_play_ratio"] * BEST_FEATURE_WEIGHTS["cate_play_ratio"]
    rt_video_info["weighted_popularity"] = rt_video_info["popularity"] * BEST_FEATURE_WEIGHTS["video_popularity_score"]

    avg_cate_play = rt_video_info["weighted_cate_play"].mean() if not rt_video_info.empty else 0.0
    avg_popularity = rt_video_info["weighted_popularity"].mean() if not rt_video_info.empty else 0.0

    # 3. 组装特征行
    feature_row = [str(user_id)] + [cate_prefer[cate] for cate in all_categories] + [avg_cate_play, avg_popularity]
    feature_cols = ["user_id"] + all_categories + ["avg_cate_play_ratio", "avg_video_popularity"]

    new_user_feature = pd.DataFrame([feature_row], columns=feature_cols).set_index("user_id")
    return new_user_feature


# ===================== 全局推荐函数 =====================
def cbr_recommend_global(user_id, return_similarity=False):
    global global_model_data
    user_id_str = str(user_id)  # 强制转为字符串，避免类型冲突

    # 1. 检查并加载模型数据
    if not global_model_data or "user_feature_matrix" not in global_model_data:
        try:
            with open(os.path.join(MODEL_SAVE_DIR, "cbr_model_data.pkl"), "rb") as f:
                global_model_data = pickle.load(f)
        except:
            # 兜底：加载视频数据生成热门推荐
            video_df = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "cleaned_video.csv"))
            video_df.rename(columns={"unique_id": "video_id"}, inplace=True)
            cold_videos = video_df.sort_values(by=["play_count"], ascending=False)["video_id"].astype(str).tolist()
            final_videos = cold_videos[:RECOMMEND_TOP_N]
            final_sims = [0.5] * len(final_videos)

            if return_similarity:
                return final_videos, final_sims
            return final_videos

    # 2. 获取核心数据
    user_feature_matrix = global_model_data["user_feature_matrix"]
    video_feature_matrix = global_model_data["video_feature_matrix"]
    video_df = global_model_data["video_df"]
    all_categories = global_model_data["all_categories"]

    # 3. 判断用户类型并生成推荐
    final_videos = []
    final_sims = []

    # 老用户/转老用户逻辑
    if is_user_converted_to_old(user_id_str):
        # 构建新用户特征
        if user_id_str not in user_feature_matrix.index:
            new_user_feat = build_new_user_feature(user_id_str)
            user_feature_matrix = pd.concat([user_feature_matrix, new_user_feat])

        # 计算相似度
        user_feat = user_feature_matrix.loc[user_id_str].values.reshape(1, -1)
        video_feats = video_feature_matrix.drop("video_id", axis=1).values
        similarities = cosine_similarity(user_feat, video_feats)[0]

        # 获取用户偏好分类
        user_cate_scores = user_feature_matrix.loc[user_id_str][all_categories]
        user_top_cate = user_cate_scores.idxmax()

        # 筛选偏好分类的视频并排序
        prefer_videos = video_df[video_df["content_category"] == user_top_cate]["video_id"].tolist()
        video_sim_df = video_feature_matrix.copy()
        video_sim_df["similarity"] = similarities
        prefer_sim = video_sim_df[video_sim_df["video_id"].isin(prefer_videos)].sort_values("similarity",
                                                                                            ascending=False)

        final_videos = prefer_sim["video_id"].astype(str).tolist()[:RECOMMEND_TOP_N]
        final_sims = prefer_sim["similarity"].tolist()[:RECOMMEND_TOP_N]

    # 新用户逻辑
    else:
        real_time_behaviors = get_real_time_behavior(user_id_str)
        if real_time_behaviors:
            # 基于实时行为推导偏好
            rt_video_ids = [b["video_id"] for b in real_time_behaviors]
            rt_video_cates = video_df[video_df["video_id"].isin(rt_video_ids)]["content_category"].tolist()

            if rt_video_cates:
                user_top_cate = max(set(rt_video_cates), key=rt_video_cates.count)
                prefer_videos = video_df[video_df["content_category"] == user_top_cate].sort_values(
                    by=["popularity", "category_play_ratio"], ascending=False
                )["video_id"].astype(str).tolist()
                final_videos = prefer_videos[:RECOMMEND_TOP_N]

                # 计算热度归一化得分
                max_pop = video_df["popularity"].max()
                final_sims = [round(video_df[video_df["video_id"] == vid]["popularity"].values[0] / max_pop, 4)
                              for vid in final_videos]
            else:
                # 无分类偏好，推荐热门
                hot_videos = video_df.sort_values(by=["popularity"], ascending=False)["video_id"].astype(str).tolist()
                final_videos = hot_videos[:RECOMMEND_TOP_N]
                final_sims = [round(0.3 + i * 0.01, 4) for i in range(RECOMMEND_TOP_N)]
        else:
            # 纯冷启动，推荐热门
            hot_videos = video_df.sort_values(by=["play_count"], ascending=False)["video_id"].astype(str).tolist()
            final_videos = hot_videos[:RECOMMEND_TOP_N]
            final_sims = [0.3] * len(final_videos)


    final_videos = [str(vid) for vid in final_videos[:RECOMMEND_TOP_N]]
    final_sims = [float(score) for score in final_sims[:RECOMMEND_TOP_N]]

    # 确保长度一致
    if len(final_videos) < RECOMMEND_TOP_N:
        final_videos += ['0'] * (RECOMMEND_TOP_N - len(final_videos))
        final_sims += [0.0] * (RECOMMEND_TOP_N - len(final_sims))

    if return_similarity:
        return final_videos, final_sims
    return final_videos


def cbr_recommend_with_score_global(user_id):
    """全局增量推荐接口（返回(视频ID, 得分)格式）"""
    videos, scores = cbr_recommend_global(user_id, return_similarity=True)
    return list(zip(videos, scores))  # 直接返回列表，而非字典


# ===================== 混合加权输出函数 =====================
def export_for_weighted_mix_global(test_users):
    """全局混合加权输出函数"""
    mix_result = []
    for user_id in test_users:
        rec_result = cbr_recommend_with_score_global(user_id)
        for video_id, score in rec_result:
            mix_result.append({
                "user_id": str(user_id),
                "video_id": str(video_id),
                "cbr_score": float(score)
            })

    mix_result_df = pd.DataFrame(mix_result)
    mix_result_df.to_csv(
        os.path.join(MODEL_SAVE_DIR, "cbr_user_video_score.csv"),
        index=False, encoding="utf-8-sig"
    )

    weight_config = {
        "module_name": "case_based_reasoning",
        "module_weight": CBR_MODULE_WEIGHT,
        "score_min": mix_result_df["cbr_score"].min() if not mix_result_df.empty else 0.0,
        "score_max": mix_result_df["cbr_score"].max() if not mix_result_df.empty else 1.0,
        "score_normalize": True
    }
    with open(os.path.join(MODEL_SAVE_DIR, "cbr_weight_config.json"), "w", encoding="utf-8") as f:
        json.dump(weight_config, f, ensure_ascii=False, indent=2)

    # 保存推荐函数（供混合加权调用）
    with open(os.path.join(MODEL_SAVE_DIR, "cbr_recommend_func.pkl"), "wb") as f:
        pickle.dump({
            "cbr_recommend_global": cbr_recommend_global,
            "cbr_recommend_with_score_global": cbr_recommend_with_score_global
        }, f)

    print(f"✅ CBR模块标准化输出完成")
    return MODEL_SAVE_DIR


# ===================== 数据加载与模型构建 =====================
def load_processed_data():
    behavior_df = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "cleaned_user_behavior.csv"), encoding="utf-8-sig")
    video_df = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "cleaned_video.csv"), encoding="utf-8-sig")
    test_df = pd.read_csv(os.path.join(PROCESSED_DATA_DIR, "test_set.csv"), encoding="utf-8-sig")

    # 数据类型统一
    behavior_df["video_unique_id"] = behavior_df["video_unique_id"].astype(str)
    video_df["unique_id"] = video_df["unique_id"].astype(str)
    test_df["video_unique_id"] = test_df["video_unique_id"].astype(str)
    behavior_df["user_id"] = behavior_df["user_id"].astype(str)
    test_df["user_id"] = test_df["user_id"].astype(str)

    # 格式标准化
    video_df.rename(columns={
        "unique_id": "video_id",
        "video_popularity_score": "popularity",
        "cate_play_ratio": "category_play_ratio"
    }, inplace=True)
    behavior_df.rename(columns={
        "video_unique_id": "video_id",
        "user_cate_prefer_score": "category_prefer_score"
    }, inplace=True)
    test_df.rename(columns={"video_unique_id": "video_id"}, inplace=True)

    return behavior_df, video_df, test_df


def build_best_cbr_recommender(behavior_df, video_df, save_model=True):
    """构建最优推荐器"""
    all_categories = sorted(behavior_df["content_category"].unique())

    # 1. 构建用户特征矩阵
    user_cate_base = behavior_df.groupby(["user_id", "content_category"])["category_prefer_score"].sum().reset_index()
    user_cate_base["weighted_cate_score"] = user_cate_base["category_prefer_score"] * BEST_FEATURE_WEIGHTS[
        "user_cate_prefer_score"]
    user_cate_matrix = user_cate_base.pivot(
        index="user_id",
        columns="content_category",
        values="weighted_cate_score"
    ).fillna(0)

    for cate in all_categories:
        if cate not in user_cate_matrix.columns:
            user_cate_matrix[cate] = 0
    user_cate_matrix = user_cate_matrix[all_categories]

    # 2. 构建视频特征矩阵
    behavior_with_video_feat = pd.merge(
        behavior_df[["user_id", "video_id"]],
        video_df[["video_id", "popularity", "category_play_ratio"]],
        on="video_id",
        how="left"
    ).fillna(0)

    behavior_with_video_feat["weighted_cate_play"] = behavior_with_video_feat["category_play_ratio"] * \
                                                     BEST_FEATURE_WEIGHTS["cate_play_ratio"]
    behavior_with_video_feat["weighted_popularity"] = behavior_with_video_feat["popularity"] * BEST_FEATURE_WEIGHTS[
        "video_popularity_score"]

    user_video_feat = behavior_with_video_feat.groupby("user_id").agg(
        avg_cate_play_ratio=("weighted_cate_play", "mean"),
        avg_video_popularity=("weighted_popularity", "mean")
    ).reset_index().fillna(0)

    # 3. 合并用户特征
    user_feature_matrix = pd.merge(
        user_cate_matrix.reset_index(),
        user_video_feat,
        on="user_id",
        how="left"
    ).fillna(0).set_index("user_id")

    # 4. 构建视频特征矩阵
    video_cate_dummies = pd.get_dummies(video_df["content_category"], prefix="cate")
    for cate in all_categories:
        col_name = f"cate_{cate}"
        if col_name not in video_cate_dummies.columns:
            video_cate_dummies[col_name] = 0

    def normalize_feat(feat_series):
        max_val = feat_series.max()
        return feat_series / max_val if max_val > 0 else 0

    video_df["cate_play_ratio_norm"] = normalize_feat(video_df["category_play_ratio"])
    video_df["video_popularity_norm"] = normalize_feat(video_df["popularity"])
    video_df["weighted_cate_play"] = video_df["cate_play_ratio_norm"] * BEST_FEATURE_WEIGHTS["cate_play_ratio"]
    video_df["weighted_popularity"] = video_df["video_popularity_norm"] * BEST_FEATURE_WEIGHTS["video_popularity_score"]

    video_feature_matrix = pd.concat([
        video_df["video_id"].reset_index(drop=True),
        video_cate_dummies[[f"cate_{cate}" for cate in all_categories]].reset_index(drop=True),
        video_df["weighted_cate_play"].reset_index(drop=True),
        video_df["weighted_popularity"].reset_index(drop=True)
    ], axis=1)
    video_feature_matrix.columns = ["video_id"] + all_categories + ["avg_cate_play_ratio", "avg_video_popularity"]

    # 5. 保存模型数据
    global global_model_data
    global_model_data = {
        "user_feature_matrix": user_feature_matrix,
        "video_feature_matrix": video_feature_matrix,
        "all_categories": all_categories,
        "video_df": video_df,
        "best_weights": BEST_FEATURE_WEIGHTS,
        "diversity_ratio": BEST_DIVERSITY_RATIO
    }

    if save_model:
        with open(os.path.join(MODEL_SAVE_DIR, "cbr_model_data.pkl"), "wb") as f:
            pickle.dump(global_model_data, f)
        print(f"✅ CBR模型已保存至：{MODEL_SAVE_DIR}")

    return cbr_recommend_global, cbr_recommend_with_score_global, all_categories, export_for_weighted_mix_global


# ===================== 主函数 =====================
if __name__ == "__main__":
    try:
        print("=" * 50)
        print("CBR算法")
        print("=" * 50)

        # 1. 加载数据
        behavior_df, video_df, test_df = load_processed_data()
        print("✅ 数据加载完成")

        # 2. 构建推荐器
        cbr_recommend, cbr_recommend_with_score, all_cates, export_for_weighted_mix = build_best_cbr_recommender(
            behavior_df, video_df, save_model=True
        )
        print("✅ CBR推荐器构建完成")

        # 3. 混合加权输出
        test_users = test_df["user_id"].unique()[:100]
        export_for_weighted_mix(test_users)

        # 4. 测试推荐
        test_user = "test_user_001"
        rec_result = cbr_recommend_with_score(test_user)
        print(f"\n🔍 测试用户{test_user}推荐结果：")
        print(f"   {rec_result}")

    except Exception as e:
        print(f"\n❌ 运行失败：{str(e)}")
        raise e