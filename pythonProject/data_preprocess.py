import json
import pandas as pd
import numpy as np
import warnings
from datetime import datetime
import os

warnings.filterwarnings('ignore')

# ===================== 1. 核心配置 =====================
RAW_USER_BEHAVIOR_PATH = r"D:\xx\毕设\pythonProject\user_behavior.json"
RAW_VIDEO_PATH = r"D:\xx\毕设\pythonProject\video.json"
PROCESSED_DATA_DIR = r"D:\xx\毕设\pythonProject\processed_data"
if not os.path.exists(PROCESSED_DATA_DIR):
    os.makedirs(PROCESSED_DATA_DIR)
BEHAVIOR_WEIGHT = {"观看": 0.1, "点赞": 0.5, "收藏": 1.0}
RANDOM_SEED = 42
TEST_USER_NUM = 100


# ===================== 2. 日志函数 =====================
def write_log(content, log_file):
    log_content = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {content}"
    print(log_content)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_content + "\n")


# ===================== 3. 加载并校验原始数据 =====================
def load_and_validate_raw_data(log_file):
    write_log("===== 开始加载并校验原始数据 =====", log_file)
    # 加载用户行为数据
    try:
        with open(RAW_USER_BEHAVIOR_PATH, "r", encoding="utf-8") as f:
            behavior_raw = json.load(f)
        behavior_df = pd.DataFrame(behavior_raw)
        write_log(f"✅用户行为数据加载成功：共{len(behavior_df)}条，{behavior_df['user_id'].nunique()}个用户", log_file)
    except Exception as e:
        raise Exception(f"❌加载用户行为数据失败：{e}")

    # 加载视频数据
    try:
        with open(RAW_VIDEO_PATH, "r", encoding="utf-8") as f:
            video_raw = json.load(f)
        video_df = pd.DataFrame(video_raw)
        write_log(f"✅视频数据加载成功：共{len(video_df)}条，{video_df['content_category'].nunique()}个分类", log_file)
    except Exception as e:
        raise Exception(f"❌加载视频数据失败：{e}")

    # 核心字段校验
    behavior_required_cols = ["user_id", "video_unique_id", "behavior_type", "behavior_time"]
    video_required_cols = ["unique_id", "content_category", "play_count",
                           "publish_date"]  # 修改1：publish_time → publish_date

    # 补充：如果视频数据没有publish_date，需提示
    if "publish_date" not in video_df.columns:
        write_log("⚠️ 视频数据缺失publish_date字段，将跳过发布时间相关特征生成", log_file)

    for col in behavior_required_cols:
        if col not in behavior_df.columns:
            raise Exception(f"❌用户行为数据缺失核心字段：{col}")
    for col in video_required_cols[:-1]:  # publish_date非必选（跳过最后一个）
        if col not in video_df.columns:
            raise Exception(f"❌视频数据缺失核心字段：{col}")

    write_log("✅核心字段校验通过，进入数据清洗阶段", log_file)
    return behavior_df, video_df, behavior_raw, video_raw


# ===================== 4. 深度数据清洗 =====================
def clean_data(behavior_df, video_df, behavior_raw, video_raw, log_file):
    write_log("===== 开始深度数据清洗 =====", log_file)
    # ---- 清洗用户行为数据 ----
    behavior_df = behavior_df.dropna(subset=["user_id", "video_unique_id", "behavior_type"])
    valid_behavior_types = list(BEHAVIOR_WEIGHT.keys())
    behavior_df = behavior_df[behavior_df["behavior_type"].isin(valid_behavior_types)]
    behavior_df = behavior_df.drop_duplicates(subset=["user_id", "video_unique_id", "behavior_type"])
    # 行为时间格式标准化（仅年月日）
    behavior_df["behavior_time"] = pd.to_datetime(behavior_df["behavior_time"], errors="coerce").dt.date
    behavior_df = behavior_df.dropna(subset=["behavior_time"])

    # ---- 清洗视频数据 ----
    video_df["content_category"] = video_df["content_category"].fillna("其他")
    video_df["play_count"] = video_df["play_count"].fillna(0).astype(int)
    video_df.loc[video_df["play_count"] < 0, "play_count"] = 0
    video_df = video_df.drop_duplicates(subset=["unique_id"], keep="first")
    # 发布时间格式标准化（仅年月日）→ 修改2：publish_time → publish_date
    if "publish_date" in video_df.columns:
        video_df["publish_date"] = pd.to_datetime(video_df["publish_date"], errors="coerce").dt.date
        video_df = video_df.dropna(subset=["publish_date"])

    # ---- 关联校验 ----
    valid_video_ids = video_df["unique_id"].astype(str).tolist()
    behavior_df["video_unique_id"] = behavior_df["video_unique_id"].astype(str)
    behavior_df = behavior_df[behavior_df["video_unique_id"].isin(valid_video_ids)]

    # 清洗结果统计
    behavior_clean_loss = len(behavior_raw) - len(behavior_df)
    video_clean_loss = len(video_raw) - len(video_df)
    write_log(f"✅数据清洗完成：", log_file)
    write_log(f"-用户行为数据：清洗后{len(behavior_df)}条（删除{behavior_clean_loss}条无效数据）", log_file)
    write_log(f"-视频数据：清洗后{len(video_df)}条（删除{video_clean_loss}条无效数据）", log_file)
    return behavior_df, video_df


# ===================== 5. 特征工程（新增适配年月日的特征） =====================
def feature_engineering(behavior_df, video_df, log_file):
    write_log("===== 开始核心特征工程（新增年月日维度特征） =====", log_file)

    # 修改3：先关联视频的content_category到行为数据（解决KeyError）
    behavior_df["video_unique_id"] = behavior_df["video_unique_id"].astype(str)
    video_df["unique_id"] = video_df["unique_id"].astype(str)
    behavior_df = pd.merge(
        behavior_df,
        video_df[["unique_id", "content_category"]],  # 关联视频分类到行为数据
        left_on="video_unique_id",
        right_on="unique_id",
        how="left"
    )
    behavior_df["content_category"] = behavior_df["content_category"].fillna("其他")  # 填充缺失分类

    # ---- 1. 行为数据新增特征（核心）----
    # 基础行为权重（原有）
    behavior_df["behavior_weight"] = behavior_df["behavior_type"].map(BEHAVIOR_WEIGHT)

    # 时间特征（仅年月日）
    behavior_df["behavior_time_dt"] = pd.to_datetime(behavior_df["behavior_time"])  # 转回datetime用于计算
    behavior_df["behavior_weekday"] = behavior_df["behavior_time_dt"].dt.weekday + 1  # 星期几（1=周一，7=周日）
    behavior_df["behavior_day_of_month"] = behavior_df["behavior_time_dt"].dt.day  # 当月第几天（1-31）

    # 用户活跃度特征
    # ① 用户活跃天数（总行为天数）
    user_active_days = behavior_df.groupby("user_id")["behavior_time"].nunique().reset_index()
    user_active_days.columns = ["user_id", "user_active_days"]
    # ② 用户总行为数/总权重（原有）
    user_behavior_stats = behavior_df.groupby("user_id").agg(
        total_behavior_count=("behavior_type", "count"),
        total_behavior_weight=("behavior_weight", "sum")
    ).reset_index()
    # 合并活跃度特征
    user_stats = pd.merge(user_active_days, user_behavior_stats, on="user_id", how="inner")
    behavior_df = pd.merge(behavior_df, user_stats, on="user_id", how="left")

    # 用户分类偏好分（细化偏好）→ 现在有content_category字段了，不会报错
    user_cate_weight = behavior_df.groupby(["user_id", "content_category"])["behavior_weight"].sum().reset_index()
    user_cate_weight.columns = ["user_id", "content_category", "user_cate_prefer_score"]
    behavior_df = pd.merge(behavior_df, user_cate_weight, on=["user_id", "content_category"], how="left")

    # ---- 2. 视频数据新增特征（核心）----
    # 原有特征（分类编码、播放量归一化）
    cate_mapping = {cate: idx for idx, cate in enumerate(video_df["content_category"].unique())}
    video_df["content_category_code"] = video_df["content_category"].map(cate_mapping)
    max_play_count = video_df["play_count"].max()
    video_df["play_count_norm"] = video_df["play_count"] / max_play_count if max_play_count > 0 else 0

    # 时间特征（仅年月日）→ 修改4：publish_time → publish_date
    if "publish_date" in video_df.columns:
        video_df["publish_date_dt"] = pd.to_datetime(video_df["publish_date"])
        video_df["publish_weekday"] = video_df["publish_date_dt"].dt.weekday + 1  # 发布星期几
        video_df["publish_day_of_month"] = video_df["publish_date_dt"].dt.day  # 发布当月第几天
        # 视频发布天数（越新的视频，数值越小）
        current_date = pd.to_datetime(datetime.now().date())
        video_df["video_age_days"] = (current_date - video_df["publish_date_dt"]).dt.days
        video_df["video_age_norm"] = 1 - (
                    video_df["video_age_days"] / video_df["video_age_days"].max())  # 归一化（0-1，越新越接近1）

    # 热度特征（融合播放量+新鲜度）
    if "video_age_norm" in video_df.columns:
        video_df["video_popularity_score"] = video_df["play_count_norm"] * 0.7 + video_df["video_age_norm"] * 0.3
    else:
        video_df["video_popularity_score"] = video_df["play_count_norm"]  # 无发布时间则只用播放量

    # 分类内播放占比（筛选分类内优质视频）
    cate_total_play = video_df.groupby("content_category")["play_count"].sum().reset_index()
    cate_total_play.columns = ["content_category", "cate_total_play"]
    video_df = pd.merge(video_df, cate_total_play, on="content_category", how="left")
    video_df["cate_play_ratio"] = video_df["play_count"] / video_df["cate_total_play"]  # 分类内播放占比
    video_df["cate_play_ratio"] = video_df["cate_play_ratio"].fillna(0)  # 填充0

    # 保存分类编码映射表
    cate_mapping_df = pd.DataFrame({
        "content_category": list(cate_mapping.keys()),
        "content_category_code": list(cate_mapping.values())
    })
    cate_mapping_path = os.path.join(PROCESSED_DATA_DIR, "cate_mapping.csv")
    cate_mapping_df.to_csv(cate_mapping_path, encoding="utf-8-sig", index=False)
    write_log(f"✅分类编码映射表已保存：{cate_mapping_path}", log_file)

    # 新增特征统计
    new_behavior_features = ["behavior_weekday", "behavior_day_of_month", "user_active_days", "user_cate_prefer_score"]
    new_video_features = ["publish_weekday", "video_age_days", "video_popularity_score", "cate_play_ratio"]
    write_log(f"✅核心特征工程完成：", log_file)
    write_log(f"-行为数据新增特征：{', '.join(new_behavior_features)}", log_file)
    write_log(f"-视频数据新增特征：{', '.join(new_video_features)}", log_file)
    write_log(f"-原有特征保留：behavior_weight、total_behavior_count、content_category_code、play_count_norm", log_file)

    # 清理临时列
    behavior_df = behavior_df.drop(columns=["behavior_time_dt", "unique_id"], errors="ignore")  # 新增删除冗余的unique_id
    video_df = video_df.drop(columns=["publish_date_dt", "video_age_norm"], errors="ignore")

    return behavior_df, video_df, cate_mapping


# ===================== 6. 划分训练集/测试集 =====================
def split_train_test_data(behavior_df, log_file):
    write_log("===== 开始划分训练集/测试集 =====", log_file)
    all_users = behavior_df["user_id"].unique()
    total_user_num = len(all_users)
    write_log(f"总用户数：{total_user_num}，计划选取{TEST_USER_NUM}个测试用户", log_file)

    np.random.seed(RANDOM_SEED)
    test_user_num = min(TEST_USER_NUM, total_user_num)
    test_users = np.random.choice(all_users, size=test_user_num, replace=False)

    train_df = behavior_df[~behavior_df["user_id"].isin(test_users)]
    test_df = behavior_df[behavior_df["user_id"].isin(test_users)]

    write_log(f"✅数据划分完成：", log_file)
    write_log(f"-训练集：{len(train_df)}条行为数据，{train_df['user_id'].nunique()}个用户", log_file)
    write_log(f"-测试集：{len(test_df)}条行为数据，{test_df['user_id'].nunique()}个用户", log_file)
    return train_df, test_df


# ===================== 7. 保存处理后的数据 =====================
def save_processed_data(behavior_df, video_df, train_df, test_df, log_file):
    write_log("===== 开始保存处理后的数据 =====", log_file)
    # 定义保存路径
    behavior_csv_path = os.path.join(PROCESSED_DATA_DIR, "cleaned_user_behavior.csv")
    video_csv_path = os.path.join(PROCESSED_DATA_DIR, "cleaned_video.csv")
    train_csv_path = os.path.join(PROCESSED_DATA_DIR, "train_set.csv")
    test_csv_path = os.path.join(PROCESSED_DATA_DIR, "test_set.csv")

    # 保存CSV（核心，算法训练用）
    behavior_df.to_csv(behavior_csv_path, encoding="utf-8-sig", index=False)
    video_df.to_csv(video_csv_path, encoding="utf-8-sig", index=False)
    train_df.to_csv(train_csv_path, encoding="utf-8-sig", index=False)
    test_df.to_csv(test_csv_path, encoding="utf-8-sig", index=False)

    write_log(f"✅处理后数据已保存：", log_file)
    write_log(f"-清洗后行为数据：{behavior_csv_path}", log_file)
    write_log(f"-清洗后视频数据：{video_csv_path}", log_file)
    write_log(f"-训练集：{train_csv_path} | 测试集：{test_csv_path}", log_file)


# ===================== 主函数 =====================
if __name__ == "__main__":
    # 初始化日志文件
    log_file_path = os.path.join(PROCESSED_DATA_DIR, "preprocess_log.txt")
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write("")

    try:
        # 步骤1：加载并校验原始数据
        behavior_df, video_df, behavior_raw, video_raw = load_and_validate_raw_data(log_file_path)

        # 步骤2：深度数据清洗
        behavior_df, video_df = clean_data(behavior_df, video_df, behavior_raw, video_raw, log_file_path)

        # 步骤3：核心特征工程（新增年月日维度特征）
        behavior_df, video_df, cate_mapping = feature_engineering(behavior_df, video_df, log_file_path)

        # 步骤4：划分训练集/测试集
        train_df, test_df = split_train_test_data(behavior_df, log_file_path)

        # 步骤5：保存处理后的数据
        save_processed_data(behavior_df, video_df, train_df, test_df, log_file_path)

        write_log("\n✅核心特征数据处理全部完成！所有新增特征已保存至CSV文件", log_file_path)
    except Exception as e:
        write_log(f"\n❌数据处理失败：{str(e)}", log_file_path)
        raise e