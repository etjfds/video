import json
import pandas as pd
import numpy as np
import warnings
from datetime import datetime
import os
import pickle
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings('ignore')

# ===================== 1. 核心配置 =====================
PROCESSED_DATA_DIR = r"D:\xx\毕设\pythonProject\processed_data"
CF_OUTPUT_DIR = os.path.join(PROCESSED_DATA_DIR, "cf_results")
MODEL_SAVE_DIR = r"D:\xx\毕设\pythonProject\saved_models\cf"
if not os.path.exists(CF_OUTPUT_DIR):
    os.makedirs(CF_OUTPUT_DIR)
if not os.path.exists(MODEL_SAVE_DIR):
    os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

# 实时行为文件路径（纯列表格式）
REAL_TIME_BEHAVIOR_PATH = os.path.join(MODEL_SAVE_DIR, "real_time_behavior.json")

# 基础参数
BEHAVIOR_WEIGHT = {"观看": 0.1, "点赞": 0.5, "收藏": 1.0}
RANDOM_SEED = 42
TEST_USER_NUM = 100
LOW_ACTIVE_THRESHOLD = 3
GROUP_SIM_FACTOR_MIN = 0.7
GROUP_SIM_FACTOR_MAX = 1.2
RECOMMEND_NUM = 10
SIMILAR_USER_NUM = 15
VIDEO_SIM_THRESHOLD = 0.3
REPEAT_VIEW_WEIGHT = 0.3


# ===================== 2. 日志函数 =====================
def write_log(content, log_file):
    log_content = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {content}"
    print(log_content)
    with open(log_file, "a", encoding="utf-8-sig") as f:
        f.write(log_content + "\n")


# ===================== 3. 行为读写函数（纯列表格式，逐条追加） =====================
def get_user_real_time_behavior(user_id):
    """
    读取用户实时行为（纯列表格式，逐条筛选）
    :param user_id: 用户ID
    :return: 该用户的所有行为列表（按时间排序）
    """
    # 处理文件不存在/空文件
    if not os.path.exists(REAL_TIME_BEHAVIOR_PATH):
        return []
    with open(REAL_TIME_BEHAVIOR_PATH, "r", encoding="utf-8") as f:
        try:
            content = f.read().strip()
            if not content:  # 空文件
                real_time_data = []
            else:
                real_time_data = json.load(f)
            # 确保是列表格式（兼容旧格式）
            if not isinstance(real_time_data, list):
                real_time_data = []
        except:
            real_time_data = []

    # 筛选指定用户的行为，并按时间排序
    user_behaviors = [b for b in real_time_data if b.get("user_id") == user_id]
    # 按行为时间排序（最新的在最后）
    user_behaviors.sort(key=lambda x: x.get("behavior_time", ""))
    return user_behaviors


def write_user_real_time_behavior(user_id, video_id, behavior_type, weight):
    """
    写入用户实时行为（纯列表格式，逐条追加，精准去重）
    :param user_id: 用户ID
    :param video_id: 视频ID
    :param behavior_type: 行为类型（观看/点赞/收藏）
    :param weight: 行为权重
    """
    # 单条行为数据（独立条目）
    behavior_data = {
        "user_id": user_id,
        "video_id": str(video_id),  # 统一为字符串，避免类型不一致
        "behavior_type": behavior_type,
        "weight": weight,
        "behavior_time": datetime.now().strftime("%Y-%m-%d")
    }

    # 读取现有数据（纯列表）
    if os.path.exists(REAL_TIME_BEHAVIOR_PATH):
        with open(REAL_TIME_BEHAVIOR_PATH, "r", encoding="utf-8") as f:
            try:
                content = f.read().strip()
                if not content:
                    real_time_data = []
                else:
                    real_time_data = json.load(f)
                # 强制转为列表（兼容旧格式）
                if not isinstance(real_time_data, list):
                    real_time_data = []
            except:
                real_time_data = []
    else:
        real_time_data = []

    # 精准去重逻辑（仅针对点赞/收藏）
    new_data = []
    if behavior_type in ["点赞", "收藏"]:
        # 点赞/收藏：删除同一用户-视频的同类型旧行为（仅保留最新）
        for b in real_time_data:
            if not (b.get("user_id") == user_id and
                    b.get("video_id") == str(video_id) and
                    b.get("behavior_type") == behavior_type):
                new_data.append(b)
    else:
        # 观看行为：不删除任何旧行为，全部保留
        new_data = real_time_data.copy()

    # 追加新行为到列表末尾（逐条追加，不分类）
    new_data.append(behavior_data)

    # 写入文件
    with open(REAL_TIME_BEHAVIOR_PATH, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 用户{user_id}的{behavior_type}行为已追加写入：视频{video_id}（权重{weight}）")


# ===================== 4. 新用户判断函数=====================
def is_new_user(user_id, behavior_df):
    """
    判断用户是否为新用户（双数据集检索）
    :param user_id: 目标用户ID
    :param behavior_df: 历史用户行为数据集
    :return: True=新用户，False=老用户
    """
    # 1. 历史数据集有行为=老用户
    has_history = user_id in behavior_df["user_id"].unique()
    if has_history:
        return False

    # 2. 实时行为≥3条=转老用户（从纯列表中统计）
    real_time_behaviors = get_user_real_time_behavior(user_id)
    if len(real_time_behaviors) >= 3:
        return False

    # 3. 无历史+实时行为<3条=新用户
    return True


# ===================== 5. 数据增强预处理 =====================
def enhance_processed_data(behavior_df, video_df, train_df, test_df, log_file):
    write_log("===== 基于现有清洗文件执行数据增强 =====", log_file)

    # 3.1 计算重复观看次数并调整行为权重
    write_log("1. 计算重复观看次数+调整行为权重", log_file)
    for df in [behavior_df, train_df, test_df]:
        df["user_video_key"] = df["user_id"] + "_" + df["video_unique_id"]

    repeat_count = behavior_df.groupby("user_video_key").size().reset_index(name="repeat_count")

    def add_enhanced_weight(df):
        df = df.merge(repeat_count, on="user_video_key", how="left")
        df["repeat_count"] = df["repeat_count"].fillna(1)
        df["behavior_weight_enhanced"] = df.apply(
            lambda row: BEHAVIOR_WEIGHT.get(row["behavior_type"], 0.1) + min(row["repeat_count"] - 1,
                                                                             2) * REPEAT_VIEW_WEIGHT,
            axis=1
        )
        return df

    train_df = add_enhanced_weight(train_df)
    test_df = add_enhanced_weight(test_df)
    behavior_df = add_enhanced_weight(behavior_df)

    write_log(
        f"✅重复观看权重调整完成：训练集权重范围 {train_df['behavior_weight_enhanced'].min():.2f}~{train_df['behavior_weight_enhanced'].max():.2f}",
        log_file)

    # 3.2 计算用户分类偏好分
    write_log("2. 计算用户分类偏好分", log_file)
    user_cate_prefer = behavior_df.groupby(["user_id", "content_category"])[
        "behavior_weight_enhanced"].sum().reset_index()
    user_total_prefer = user_cate_prefer.groupby("user_id")["behavior_weight_enhanced"].sum().reset_index()
    user_total_prefer.columns = ["user_id", "total_prefer_score"]
    user_cate_prefer = user_cate_prefer.merge(user_total_prefer, on="user_id", how="left")
    user_cate_prefer["cate_prefer_ratio"] = user_cate_prefer["behavior_weight_enhanced"] / user_cate_prefer[
        "total_prefer_score"]

    write_log(f"✅用户分类偏好分计算完成：共{len(user_cate_prefer)}个用户-分类组合", log_file)

    # 3.3 计算视频内容相似度
    write_log("3. 计算视频内容相似度", log_file)
    video_df["topic_tags"] = video_df["topic_tags"].fillna("")
    video_df["title_intro"] = video_df["title_intro"].fillna("")

    all_tags = set()
    for tags in video_df["topic_tags"]:
        if tags.strip():
            all_tags.update(tags.split(","))
    all_tags = list(all_tags)

    tag_matrix = np.zeros((len(video_df), len(all_tags)))
    for idx, tags in enumerate(video_df["topic_tags"]):
        if tags.strip():
            for tag in tags.split(","):
                if tag in all_tags:
                    tag_matrix[idx, all_tags.index(tag)] = 1

    video_content_sim = cosine_similarity(tag_matrix)
    video_content_sim_df = pd.DataFrame(
        video_content_sim,
        index=video_df["unique_id"],
        columns=video_df["unique_id"]
    )
    video_content_sim_df[video_content_sim_df < VIDEO_SIM_THRESHOLD] = 0

    write_log(f"✅视频内容相似度计算完成：{video_content_sim_df.shape[0]}个视频", log_file)

    # 数据格式标准化
    video_df.rename(columns={
        "unique_id": "video_id",
        "video_popularity_score": "popularity"
    }, inplace=True)
    behavior_df.rename(columns={"video_unique_id": "video_id"}, inplace=True)
    train_df.rename(columns={"video_unique_id": "video_id"}, inplace=True)
    test_df.rename(columns={"video_unique_id": "video_id"}, inplace=True)

    video_df["video_id"] = video_df["video_id"].astype(str)
    behavior_df["video_id"] = behavior_df["video_id"].astype(str)
    train_df["video_id"] = train_df["video_id"].astype(str)
    test_df["video_id"] = test_df["video_id"].astype(str)

    return behavior_df, video_df, train_df, test_df, user_cate_prefer, video_content_sim_df


# ===================== 6. 加载现有预处理文件 =====================
def load_existing_processed_data(log_file):
    write_log("===== 加载现有清洗后的数据文件 =====", log_file)
    file_paths = {
        "cleaned_behavior": os.path.join(PROCESSED_DATA_DIR, "cleaned_user_behavior.csv"),
        "cleaned_video": os.path.join(PROCESSED_DATA_DIR, "cleaned_video.csv"),
        "train_set": os.path.join(PROCESSED_DATA_DIR, "train_set.csv"),
        "test_set": os.path.join(PROCESSED_DATA_DIR, "test_set.csv")
    }

    try:
        behavior_df = pd.read_csv(file_paths["cleaned_behavior"], encoding="utf-8-sig")
        video_df = pd.read_csv(file_paths["cleaned_video"], encoding="utf-8-sig")
        train_df = pd.read_csv(file_paths["train_set"], encoding="utf-8-sig")
        test_df = pd.read_csv(file_paths["test_set"], encoding="utf-8-sig")

        write_log(f"✅文件加载成功：", log_file)
        write_log(f"-cleaned_user_behavior.csv：{len(behavior_df)}条", log_file)
        write_log(f"-cleaned_video.csv：{len(video_df)}条", log_file)
        write_log(f"-train_set.csv：{len(train_df)}条 | test_set.csv：{len(test_df)}条", log_file)
    except Exception as e:
        raise Exception(f"❌加载文件失败：{str(e)}（请检查文件路径是否正确）")

    for df in [behavior_df, train_df, test_df]:
        df["user_id"] = df["user_id"].astype(str)
        df["video_unique_id"] = df["video_unique_id"].astype(str)
    video_df["unique_id"] = video_df["unique_id"].astype(str)

    required_cols = ["behavior_type"]
    for df in [behavior_df, train_df, test_df]:
        for col in required_cols:
            if col not in df.columns:
                raise Exception(f"❌{df} 缺少必要字段：{col}")

    behavior_df, video_df, train_df, test_df, user_cate_prefer, video_content_sim_df = enhance_processed_data(
        behavior_df, video_df, train_df, test_df, log_file
    )

    return behavior_df, video_df, train_df, test_df, user_cate_prefer, video_content_sim_df


# ===================== 7. 改进CF推荐器核心类 =====================
class ImprovedCF推荐器:
    def __init__(self, train_df, test_df, video_df, user_cate_prefer, video_content_sim_df, log_file, random_seed=42,
                 save_model=True):
        self.train_df = train_df
        self.test_df = test_df
        self.video_df = video_df
        self.user_cate_prefer = user_cate_prefer
        self.video_content_sim_df = video_content_sim_df
        self.log_file = log_file
        self.random_seed = random_seed
        self.save_model = save_model
        np.random.seed(self.random_seed)

        self.user_video_matrix = None
        self.user_similarity_matrix = None
        self.original_similarity_matrix = None
        self.user_groups = None
        self.low_active_users = None
        self.user_main_cate = None
        self.user_cate_prefer_ratio = None

        self._precompute_user_behavior_stats()
        self._precompute_user_groups_and_prefer()
        self._build_user_video_matrix()
        self._calculate_improved_similarity()

        if self.save_model:
            self._save_model_data()
            write_log(f"✅ CF模型/特征已保存至：{MODEL_SAVE_DIR}", self.log_file)

    def _precompute_user_behavior_stats(self):
        write_log("===== 识别低活跃用户 =====", self.log_file)
        all_behavior_df = pd.concat([self.train_df, self.test_df], ignore_index=True)
        user_behavior_count = all_behavior_df.groupby("user_id")["behavior_type"].count().reset_index()
        user_behavior_count.columns = ["user_id", "behavior_count"]
        self.low_active_users = user_behavior_count[user_behavior_count["behavior_count"] < LOW_ACTIVE_THRESHOLD][
            "user_id"].tolist()
        write_log(f"✅低活跃用户（行为数<{LOW_ACTIVE_THRESHOLD}）：{len(self.low_active_users)}个", self.log_file)

    def _precompute_user_groups_and_prefer(self):
        write_log("===== 划分用户群体+计算偏好权重 =====", self.log_file)
        user_main_cate = self.user_cate_prefer.loc[
            self.user_cate_prefer.groupby("user_id")["behavior_weight_enhanced"].idxmax()]
        self.user_main_cate = user_main_cate.set_index("user_id")["content_category"].to_dict()

        self.user_cate_prefer_ratio = {}
        for _, row in self.user_cate_prefer.iterrows():
            user_id = row["user_id"]
            cate = row["content_category"]
            ratio = row["cate_prefer_ratio"]
            if user_id not in self.user_cate_prefer_ratio:
                self.user_cate_prefer_ratio[user_id] = {}
            self.user_cate_prefer_ratio[user_id][cate] = ratio

        self.user_groups = user_main_cate.groupby("content_category")["user_id"].apply(list).to_dict()
        write_log(f"✅用户群体划分完成：共{len(self.user_groups)}个分类", self.log_file)
        for cate, users in self.user_groups.items():
            write_log(f"-{cate}群体：{len(users)}个用户", self.log_file)

    def _build_user_video_matrix(self):
        write_log("===== 构建用户-视频评分矩阵 =====", self.log_file)
        pivot_col = "video_id" if "video_id" in self.train_df.columns else "video_unique_id"
        user_video_pivot = self.train_df.pivot_table(
            index="user_id",
            columns=pivot_col,
            values="behavior_weight_enhanced",
            fill_value=0
        )
        self.user_video_matrix = user_video_pivot
        write_log(f"✅矩阵构建完成：{self.user_video_matrix.shape[0]}用户 × {self.user_video_matrix.shape[1]}视频",
                  self.log_file)

    def _calculate_original_similarity(self):
        write_log("===== 计算原始用户相似度 =====", self.log_file)
        self.original_similarity_matrix = cosine_similarity(self.user_video_matrix)
        self.original_similarity_matrix = pd.DataFrame(
            self.original_similarity_matrix,
            index=self.user_video_matrix.index,
            columns=self.user_video_matrix.index
        )
        write_log(f"✅原始相似度矩阵完成：{self.original_similarity_matrix.shape}", self.log_file)

    def _calculate_group_similarity_factor(self):
        write_log("===== 计算群体相似度因子 =====", self.log_file)
        group_sim_factors = {}

        for cate, group_users in self.user_groups.items():
            valid_group_users = [u for u in group_users if u in self.user_video_matrix.index]
            if not valid_group_users:
                factor = 1.0
            else:
                group_matrix = self.original_similarity_matrix.loc[valid_group_users, valid_group_users]
                avg_group_sim = group_matrix.values.mean()
                factor = 0.7 + (avg_group_sim * 0.5)
                factor = np.clip(factor, GROUP_SIM_FACTOR_MIN, GROUP_SIM_FACTOR_MAX)
            for user in group_users:
                group_sim_factors[user] = factor

        for user in self.user_video_matrix.index:
            if user not in group_sim_factors:
                group_sim_factors[user] = 1.0

        write_log(f"✅群体因子计算完成：{len(group_sim_factors)}个用户", self.log_file)
        return group_sim_factors

    def _calculate_improved_similarity(self):
        write_log("===== 计算改进版用户相似度 =====", self.log_file)
        self._calculate_original_similarity()
        group_sim_factors = self._calculate_group_similarity_factor()

        self.user_similarity_matrix = self.original_similarity_matrix.copy()
        for user1 in self.user_similarity_matrix.index:
            factor1 = group_sim_factors[user1]
            for user2 in self.user_similarity_matrix.columns:
                factor2 = group_sim_factors[user2]
                self.user_similarity_matrix.loc[user1, user2] *= (factor1 + factor2) / 2

        np.fill_diagonal(self.user_similarity_matrix.values, 0)
        write_log(f"✅改进版相似度矩阵完成", self.log_file)

    def _get_user_main_category(self, user_id):
        if user_id in self.user_main_cate:
            return self.user_main_cate[user_id]
        test_behavior = self.test_df[self.test_df["user_id"] == user_id]
        if not test_behavior.empty:
            return test_behavior["content_category"].value_counts().index[0]
        return "其他"

    def _get_group_hot_videos(self, user_id):
        main_cate = self._get_user_main_category(user_id)
        video_df = self.video_df.copy()
        popularity_col = "popularity" if "popularity" in video_df.columns else "video_popularity_score"
        prefer_ratio = self.user_cate_prefer_ratio.get(user_id, {}).get(main_cate, 0.5)
        video_df["weighted_popularity"] = video_df[popularity_col] * (1 + prefer_ratio * 0.5)

        cate_videos = video_df[video_df["content_category"] == main_cate]
        if cate_videos.empty:
            hot_videos = video_df.sort_values("weighted_popularity", ascending=False)["video_id"].head(
                RECOMMEND_NUM).tolist()
        else:
            hot_videos = cate_videos.sort_values("weighted_popularity", ascending=False)["video_id"].head(
                RECOMMEND_NUM).tolist()
        return hot_videos

    def _get_similar_train_user(self, user_id):
        test_behavior = self.test_df[self.test_df["user_id"] == user_id]
        if test_behavior.empty:
            return np.random.choice(self.user_video_matrix.index, 1)[0]

        test_user_vector = pd.Series(0, index=self.user_video_matrix.columns)
        pivot_col = "video_id" if "video_id" in self.test_df.columns else "video_unique_id"
        for _, row in test_behavior.iterrows():
            video_id = row[pivot_col]
            if video_id in test_user_vector.index:
                test_user_vector[video_id] = row["behavior_weight_enhanced"]

        train_vectors = self.user_video_matrix.values
        similarities = cosine_similarity(test_user_vector.values.reshape(1, -1), train_vectors)[0]
        return self.user_video_matrix.index[np.argmax(similarities)]

    def _get_content_supplement_videos(self, user_id, interacted_videos, need_num):
        user_interacted = interacted_videos
        if not user_interacted:
            return []

        similar_videos = set()
        for video_id in user_interacted:
            if video_id in self.video_content_sim_df.index:
                sim_videos = self.video_content_sim_df[video_id].sort_values(ascending=False).head(20).index
                similar_videos.update(sim_videos)

        supplement_videos = [v for v in similar_videos if v not in user_interacted][:need_num]
        return supplement_videos

    def recommend(self, user_id, top_n=RECOMMEND_NUM):
        if user_id in self.low_active_users:
            return self._get_group_hot_videos(user_id)

        try:
            if user_id in self.user_similarity_matrix.index:
                similar_users = self.user_similarity_matrix[user_id].sort_values(ascending=False)
                similar_users = similar_users[similar_users.index.isin(self.user_video_matrix.index)]
                similar_users = similar_users.head(SIMILAR_USER_NUM).index
            else:
                similar_train_user = self._get_similar_train_user(user_id)
                similar_users = self.user_similarity_matrix[similar_train_user].sort_values(ascending=False).head(
                    SIMILAR_USER_NUM).index

            pivot_col = "video_id" if "video_id" in self.train_df.columns else "video_unique_id"
            similar_user_videos = self.train_df[self.train_df["user_id"].isin(similar_users)]
            video_scores = similar_user_videos.groupby(pivot_col)["behavior_weight_enhanced"].sum().sort_values(
                ascending=False)

            user_interacted_train = self.train_df[self.train_df["user_id"] == user_id][pivot_col].tolist()
            user_interacted_test = self.test_df[self.test_df["user_id"] == user_id][pivot_col].tolist()
            user_interacted_videos = list(set(user_interacted_train + user_interacted_test))
            recommend_videos = video_scores.index[~video_scores.index.isin(user_interacted_videos)].tolist()

            if len(recommend_videos) < top_n:
                content_supplement = self._get_content_supplement_videos(
                    user_id, user_interacted_videos, top_n - len(recommend_videos)
                )
                recommend_videos += content_supplement
            if len(recommend_videos) < top_n:
                hot_supplement = [v for v in self._get_group_hot_videos(user_id) if v not in user_interacted_videos]
                recommend_videos += hot_supplement[:top_n - len(recommend_videos)]

            recommend_videos = list(dict.fromkeys(recommend_videos))[:top_n]
            return recommend_videos

        except Exception as e:
            write_log(f"⚠️ 用户{user_id}推荐失败，改用热门推荐：{str(e)}", self.log_file)
            return self._get_group_hot_videos(user_id)

    def recommend_with_score_old_user(self, user_id, top_n=RECOMMEND_NUM):
        real_time_behaviors = get_user_real_time_behavior(user_id)
        user_vector = pd.Series(0, index=self.user_video_matrix.columns)

        for behavior in real_time_behaviors:
            vid = behavior["video_id"]
            if vid in user_vector.index:
                user_vector[vid] = behavior["weight"]

        train_vectors = self.user_video_matrix.values
        similarities = cosine_similarity(user_vector.values.reshape(1, -1), train_vectors)[0]
        similar_train_user = self.user_video_matrix.index[np.argmax(similarities)]

        similar_users = self.user_similarity_matrix[similar_train_user].sort_values(ascending=False).head(
            SIMILAR_USER_NUM).index
        similar_user_videos = self.train_df[self.train_df["user_id"].isin(similar_users)]
        video_scores = similar_user_videos.groupby("video_id")["behavior_weight_enhanced"].sum().sort_values(
            ascending=False)

        interacted_videos = [b["video_id"] for b in real_time_behaviors]
        recommend_videos = video_scores.index[~video_scores.index.isin(interacted_videos)].tolist()[:top_n]

        max_score = video_scores.max() if not video_scores.empty else 1.0
        scores = [round(video_scores[vid] / max_score, 4) if vid in video_scores else 0.5 for vid in recommend_videos]

        return list(zip(recommend_videos, scores))

    def recommend_with_score(self, user_id, top_n=RECOMMEND_NUM):
        # 老用户逻辑
        if user_id in self.user_similarity_matrix.index:
            recommend_videos = self.recommend(user_id, top_n)
            scores = []
            for video_id in recommend_videos:
                if user_id in self.low_active_users:
                    popularity_col = "popularity" if "popularity" in self.video_df.columns else "video_popularity_score"
                    video_pop = self.video_df[self.video_df["video_id"] == video_id][popularity_col].values[0]
                    max_pop = self.video_df[popularity_col].max()
                    score = video_pop / max_pop if max_pop > 0 else 0.5
                else:
                    pivot_col = "video_id" if "video_id" in self.train_df.columns else "video_unique_id"
                    similar_users = self.user_similarity_matrix[user_id].sort_values(ascending=False).head(
                        SIMILAR_USER_NUM).index
                    similar_user_videos = self.train_df[self.train_df["user_id"].isin(similar_users)]
                    video_score = similar_user_videos[similar_user_videos[pivot_col] == video_id][
                        "behavior_weight_enhanced"].sum()
                    max_score = similar_user_videos["behavior_weight_enhanced"].max()
                    score = video_score / max_score if max_score > 0 else 0.3
                scores.append(round(score, 4))
            return list(zip(recommend_videos, scores))

        # 新用户逻辑
        else:
            real_time_behaviors = get_user_real_time_behavior(user_id)

            # 转老用户
            if len(real_time_behaviors) >= 3:
                print(f"⚠️ 新用户{user_id}累积≥3条行为，自动转为老用户！")
                return self.recommend_with_score_old_user(user_id, top_n)

            # 无实时行为
            if not real_time_behaviors:
                popularity_col = "popularity" if "popularity" in self.video_df.columns else "video_popularity_score"
                hot_videos = self.video_df.copy()
                max_pop = hot_videos[popularity_col].max()
                min_pop = hot_videos[popularity_col].min()
                hot_videos["hot_score"] = (hot_videos[popularity_col] - min_pop) / (
                        max_pop - min_pop) if max_pop > min_pop else 0.5
                hot_recs = hot_videos.sort_values("hot_score", ascending=False).head(top_n)
                return [(str(row["video_id"]), round(row["hot_score"], 4)) for _, row in hot_recs.iterrows()]

            # 有实时行为
            else:
                rec_dict = {}
                # 实时行为视频
                for behavior in real_time_behaviors:
                    vid = behavior["video_id"]
                    weight = behavior["weight"]
                    rec_dict[vid] = 0.9 + weight

                # 相似视频
                for behavior in real_time_behaviors:
                    vid = behavior["video_id"]
                    if vid in self.video_content_sim_df.index:
                        similar_vids = self.video_content_sim_df[vid].sort_values(ascending=False).head(5)
                        for sim_vid, sim_score in similar_vids.items():
                            if sim_vid not in rec_dict and sim_score > 0.3:
                                rec_dict[sim_vid] = sim_score * 0.8

                # 归一化得分
                max_score = max(rec_dict.values()) if rec_dict else 1.0
                normalized_recs = [(vid, round(score / max_score, 4)) for vid, score in rec_dict.items()]

                # 补充热门视频
                if len(normalized_recs) < top_n:
                    hot_recs = self._get_new_user_hot_recommend(top_n - len(normalized_recs))
                    normalized_recs += hot_recs

                return normalized_recs[:top_n]

    def _get_new_user_hot_recommend(self, top_n):
        popularity_col = "popularity" if "popularity" in self.video_df.columns else "video_popularity_score"
        hot_videos = self.video_df.sort_values(popularity_col, ascending=False).head(top_n)
        max_pop = hot_videos[popularity_col].max()
        min_pop = hot_videos[popularity_col].min()
        hot_videos["hot_score"] = (hot_videos[popularity_col] - min_pop) / (
                max_pop - min_pop) if max_pop > min_pop else 0.5
        return [(str(row["video_id"]), round(row["hot_score"], 4)) for _, row in hot_videos.iterrows()]

    def batch_recommend(self, test_users):
        write_log("===== 开始批量推荐 =====", self.log_file)
        recommend_results = {}
        total_users = len(test_users)

        for idx, user_id in enumerate(test_users):
            if idx % 20 == 0:
                write_log(f"进度：{idx}/{total_users}个用户", self.log_file)
            recommend_results[user_id] = self.recommend(user_id)

        write_log(f"✅批量推荐完成：{len(recommend_results)}个用户", self.log_file)
        return recommend_results

    def _save_model_data(self):
        model_data = {
            "user_video_matrix": self.user_video_matrix,
            "user_similarity_matrix": self.user_similarity_matrix,
            "original_similarity_matrix": self.original_similarity_matrix,
            "user_groups": self.user_groups,
            "low_active_users": self.low_active_users,
            "user_main_cate": self.user_main_cate,
            "user_cate_prefer_ratio": self.user_cate_prefer_ratio,
            "video_content_sim_df": self.video_content_sim_df,
            "video_df": self.video_df,
            "train_df": self.train_df,
            "test_df": self.test_df
        }
        with open(os.path.join(MODEL_SAVE_DIR, "cf_model_data.pkl"), "wb") as f:
            pickle.dump(model_data, f)
        with open(os.path.join(MODEL_SAVE_DIR, "cf_recommend_func.pkl"), "wb") as f:
            pickle.dump(self.recommend_with_score, f)

    def export_for_weighted_mix(self, test_users, cf_weight=0.4):
        weighted_mix_dir = MODEL_SAVE_DIR

        mix_result = []
        old_users = [u for u in test_users if u in self.user_similarity_matrix.index]
        for user_id in old_users:
            rec_result = self.recommend_with_score(user_id)
            for video_id, score in rec_result:
                mix_result.append({
                    "user_id": user_id,
                    "video_id": video_id,
                    "cf_score": score
                })
        new_users = [u for u in test_users if u not in self.user_similarity_matrix.index]
        for user_id in new_users:
            rec_result = self.recommend_with_score(user_id)
            for video_id, score in rec_result:
                mix_result.append({
                    "user_id": user_id,
                    "video_id": video_id,
                    "cf_score": score
                })

        mix_result_df = pd.DataFrame(mix_result)
        mix_result_df.to_csv(
            os.path.join(weighted_mix_dir, "cf_user_video_score.csv"),
            index=False, encoding="utf-8-sig"
        )

        weight_config = {
            "module_name": "collaborative_filtering",
            "module_weight": cf_weight,
            "score_min": mix_result_df["cf_score"].min() if not mix_result_df.empty else 0.0,
            "score_max": mix_result_df["cf_score"].max() if not mix_result_df.empty else 1.0,
            "score_normalize": True
        }
        with open(os.path.join(weighted_mix_dir, "cf_weight_config.json"), "w", encoding="utf-8") as f:
            json.dump(weight_config, f, ensure_ascii=False, indent=2)

        write_log(f"✅ CF模块标准化输出完成：", self.log_file)
        write_log(f"- 用户-视频-得分文件：cf_user_video_score.csv", self.log_file)
        write_log(f"- 模块权重配置文件：cf_weight_config.json", self.log_file)
        write_log(f"- 输出目录：{weighted_mix_dir}", self.log_file)

        return weighted_mix_dir


# ===================== 8. 主函数 =====================
if __name__ == "__main__":
    log_file_path = os.path.join(CF_OUTPUT_DIR, "cf_log.txt")
    with open(log_file_path, "w", encoding="utf-8-sig") as f:
        f.write("改进CF算法运行日志\n")

    try:
        # 加载数据
        behavior_df, video_df, train_df, test_df, user_cate_prefer, video_content_sim_df = load_existing_processed_data(
            log_file_path)

        # 初始化推荐器
        improved_cf = ImprovedCF推荐器(
            train_df, test_df, video_df, user_cate_prefer, video_content_sim_df, log_file_path, RANDOM_SEED,
            save_model=True
        )

        # 批量推荐
        test_users = test_df["user_id"].unique()[:TEST_USER_NUM]
        improved_recommend_results = improved_cf.batch_recommend(test_users)

        # 标记新/老用户
        new_users = [u for u in test_users if is_new_user(u, behavior_df)]
        old_users = [u for u in test_users if not is_new_user(u, behavior_df)]
        write_log(f"测试用户统计：老用户{len(old_users)}个，新用户{len(new_users)}个", log_file_path)

        # 输出混合加权文件
        improved_cf.export_for_weighted_mix(test_users, cf_weight=0.4)

        # 测试用户推荐
        print("\n📌 实际存在的用户ID前10个：")
        print(improved_cf.user_similarity_matrix.index[:10].tolist())

        test_user_id = improved_cf.user_similarity_matrix.index[0]
        print(f"\n🔍 测试用户ID（自动选择存在的）：{test_user_id}")

        recommend_result = improved_cf.recommend_with_score(test_user_id)
        print(f"\n✅ 老用户增量推荐结果：{recommend_result}")

        # 测试新用户行为写入（纯列表格式）
        print("\n" + "=" * 50)
        print("📌 测试新用户行为写入：")
        print("=" * 50)
        new_test_user = "new_user_999"
        # 清空该用户原有行为
        if os.path.exists(REAL_TIME_BEHAVIOR_PATH):
            with open(REAL_TIME_BEHAVIOR_PATH, "r", encoding="utf-8") as f:
                real_time_data = json.load(f)
            # 过滤该用户的所有行为
            real_time_data = [b for b in real_time_data if b.get("user_id") != new_test_user]
            with open(REAL_TIME_BEHAVIOR_PATH, "w", encoding="utf-8") as f:
                json.dump(real_time_data, f, ensure_ascii=False, indent=2)

        # 模拟写入行为（逐条追加）
        sample_video_ids = improved_cf.video_df["video_id"].tolist()[:3]
        # 重复观看（保留多条）
        write_user_real_time_behavior(new_test_user, sample_video_ids[0], "观看", 0.1)
        write_user_real_time_behavior(new_test_user, sample_video_ids[0], "观看", 0.1)
        # 重复点赞（仅保留最新）
        write_user_real_time_behavior(new_test_user, sample_video_ids[1], "点赞", 0.5)
        write_user_real_time_behavior(new_test_user, sample_video_ids[1], "点赞", 0.5)
        # 收藏
        write_user_real_time_behavior(new_test_user, sample_video_ids[2], "收藏", 1.0)

        # 验证行为读取
        user_behaviors = get_user_real_time_behavior(new_test_user)
        print(f"\n🔍 新用户{new_test_user}的所有行为：")
        for idx, b in enumerate(user_behaviors):
            print(f"  行为{idx + 1}：{b}")

        # 判定新用户
        is_new = is_new_user(new_test_user, behavior_df)
        print(f"\n🔍 新用户{new_test_user}判定结果：{'新用户' if is_new else '老用户（转）'}")

        # 新用户推荐
        new_user_rec = improved_cf.recommend_with_score(new_test_user)
        print(f"\n✅ 新用户推荐结果：{new_user_rec}")

        write_log("\n✅改进CF算法全量训练完成！", log_file_path)

    except Exception as e:
        write_log(f"\n❌算法运行失败：{str(e)}", log_file_path)
        import traceback

        traceback.print_exc()