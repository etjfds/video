import pandas as pd
import numpy as np
import os
import pickle
import json
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# --------------------------
# 核心：导入原模块函数
# --------------------------
from cf_algorithm_metrics import ImprovedCF推荐器
from cbr_algorithm_metrics import cbr_recommend_with_score_global
from lightgbm2 import incremental_recommend, load_lgb_model

# ==============================
# 1. 核心配置
# ==============================
BASE_DIR = r"D:\xx\毕设\pythonProject"
CF_MODEL_DIR = os.path.join(BASE_DIR, "saved_models/cf")
CBR_MODEL_DIR = os.path.join(BASE_DIR, "saved_models/cbr")
LGB_MODEL_DIR = os.path.join(BASE_DIR, "saved_models/lgb")
REAL_TIME_BEHAVIOR_PATH = os.path.join(BASE_DIR, "saved_models/cf/real_time_behavior.json")
MIX_OUTPUT_DIR = os.path.join(BASE_DIR, "saved_models/mix_weight")
if not os.path.exists(MIX_OUTPUT_DIR):
    os.makedirs(MIX_OUTPUT_DIR, exist_ok=True)

TOP_N = 30
WEIGHT_CONFIG = {
    "old_user": {"cf": 0.4, "cbr": 0.2, "lgb": 0.4},
    "new_user": {"cf": 0.1, "cbr": 0.5, "lgb": 0.4}
}


# ==============================
# 2. 日志工具
# ==============================
def init_logger():
    def log_info(msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [INFO] {msg}")

    def log_warning(msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [WARNING] {msg}")

    def log_error(msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [ERROR] {msg}")

    return log_info, log_warning, log_error


log_info, log_warning, log_error = init_logger()


# ==============================
# 3. 行为读写函数
# ==============================
def write_user_real_time_behavior(user_id, video_id, behavior_type, weight):
    behavior_data = {
        "user_id": str(user_id),
        "video_id": str(video_id),
        "behavior_type": behavior_type,
        "weight": weight,
        "behavior_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if os.path.exists(REAL_TIME_BEHAVIOR_PATH):
        with open(REAL_TIME_BEHAVIOR_PATH, "r", encoding="utf-8") as f:
            try:
                content = f.read().strip()
                real_time_data = json.loads(content) if content else []
            except:
                real_time_data = []
    else:
        real_time_data = []

    # 去重逻辑
    if behavior_type in ["点赞", "收藏"]:
        real_time_data = [b for b in real_time_data if not (
                b["user_id"] == str(user_id) and
                b["video_id"] == str(video_id) and
                b["behavior_type"] == behavior_type
        )]

    real_time_data.append(behavior_data)
    with open(REAL_TIME_BEHAVIOR_PATH, "w", encoding="utf-8") as f:
        json.dump(real_time_data, f, ensure_ascii=False, indent=2)

    log_info(f"✅ 用户{user_id}行为已写入：{behavior_type}视频{video_id}（权重{weight}）")


def get_user_real_time_behavior(user_id):
    if not os.path.exists(REAL_TIME_BEHAVIOR_PATH):
        return []
    try:
        with open(REAL_TIME_BEHAVIOR_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            real_time_data = json.loads(content)
        if isinstance(real_time_data, dict):
            real_time_data = []
        user_behaviors = [b for b in real_time_data if b["user_id"] == str(user_id)]
        user_behaviors.sort(key=lambda x: x["behavior_time"])
        return user_behaviors
    except Exception as e:
        log_error(f"读取用户{user_id}实时行为失败：{str(e)}")
        return []


def judge_user_type(user_id, history_user_list):
    user_id_str = str(user_id)
    if user_id_str in history_user_list:
        log_info(f"用户{user_id}：老用户（存在历史行为）")
        return "old_user"
    real_time_behaviors = get_user_real_time_behavior(user_id_str)
    if len(real_time_behaviors) >= 3:
        log_info(f"用户{user_id}：老用户（实时行为≥3条）")
        return "old_user"
    else:
        log_info(f"用户{user_id}：新用户（实时行为{len(real_time_behaviors)}条）")
        return "new_user"


# ==============================
# 4. 加载模块数据
# ==============================
def load_single_module_score(module_name):
    module_dir = {"cf": CF_MODEL_DIR, "cbr": CBR_MODEL_DIR, "lgb": LGB_MODEL_DIR}[module_name]
    score_path = os.path.join(module_dir, f"{module_name}_user_video_score.csv")

    if not os.path.exists(score_path):
        log_error(f"{module_name}得分文件不存在：{score_path}")
        return pd.DataFrame()

    df = pd.read_csv(score_path, encoding="utf-8-sig")
    df["user_id"] = df["user_id"].astype(str)
    df["video_id"] = df["video_id"].astype(str)
    df[f"{module_name}_score"] = df[f"{module_name}_score"].clip(0, 1).astype(float)

    log_info(f"加载{module_name}得分表完成：{len(df)}条记录")
    return df


def load_base_data():
    """加载所有模块数据"""
    # 1. 加载得分数据
    cf_score_df = load_single_module_score("cf")
    cbr_score_df = load_single_module_score("cbr")
    lgb_score_df = load_single_module_score("lgb")

    # 2. 获取所有用户
    all_users = set()
    for df in [cf_score_df, cbr_score_df, lgb_score_df]:
        if not df.empty:
            all_users.update(df["user_id"].unique())
    history_user_list = list(all_users)

    # 3. 加载热门视频
    hot_videos = []
    try:
        video_df = pd.read_csv(os.path.join(BASE_DIR, "processed_data/cleaned_video.csv"))
        video_df.rename(columns={"unique_id": "video_id"}, inplace=True)
        hot_videos = video_df.sort_values("play_count", ascending=False)["video_id"].astype(str).tolist()[:100]
    except:
        hot_videos = [f"video_{i}" for i in range(100)]

    # 4. 加载模型和函数
    # CF函数（请确保返回 (video_id, score) 格式的列表）
    cf_func = ImprovedCF推荐器  # 请根据实际函数名调整

    # CBR函数
    cbr_func = cbr_recommend_with_score_global

    # LGB模型和函数
    lgb_model, lgb_feat_cols = load_lgb_model()

    # 包装LGB函数
    def lgb_wrapper(user_id, top_n=TOP_N):
        if not lgb_model or not lgb_feat_cols:
            return []
        # 加载必要数据
        train_feat = pd.read_csv(os.path.join(BASE_DIR, "processed_data/train_set.csv"))
        train_feat.rename(columns={"video_unique_id": "video_id"}, inplace=True)
        train_feat["user_id"] = train_feat["user_id"].astype(str)
        train_feat["video_id"] = train_feat["video_id"].astype(str)

        video_df = pd.read_csv(os.path.join(BASE_DIR, "processed_data/cleaned_video.csv"))
        video_df.rename(columns={"unique_id": "video_id"}, inplace=True)
        video_df["video_id"] = video_df["video_id"].astype(str)

        return incremental_recommend(lgb_model, train_feat, video_df, user_id, lgb_feat_cols, top_n)

    return {
        "history_user_list": history_user_list,
        "cf_score_df": cf_score_df,
        "cbr_score_df": cbr_score_df,
        "lgb_score_df": lgb_score_df,
        "hot_videos": hot_videos,
        "cf_func": cf_func,
        "cbr_func": cbr_func,
        "lgb_func": lgb_wrapper,
        "lgb_model": lgb_model,
        "lgb_feat_cols": lgb_feat_cols
    }


BASE_DATA = load_base_data()


# ==============================
# 5. 核心混合推荐函数
# ==============================
def get_recommend_list(user_id):
    """生成混合加权推荐列表"""
    log_info(f"\n========== 用户{user_id}请求推荐列表 ==========")
    user_id_str = str(user_id)

    # 1. 获取基础数据
    data = BASE_DATA
    user_type = judge_user_type(user_id_str, data["history_user_list"])
    weights = WEIGHT_CONFIG[user_type]

    log_info(f"用户类型：{user_type} | 权重配置：CF={weights['cf']}, CBR={weights['cbr']}, LGB={weights['lgb']}")

    # 2. 获取各模块推荐结果
    module_results = {}

    # CF推荐
    try:
        cf_result = data["cf_func"](user_id_str, top_n=TOP_N)  # 请确保返回 (video_id, score) 列表
        # 转换为字典格式
        module_results["cf"] = {str(k): float(v) for k, v in cf_result}
        log_info(f"CF模块返回 {len(module_results['cf'])} 条推荐")
    except Exception as e:
        log_error(f"CF推荐失败：{str(e)}")
        module_results["cf"] = {}

    # CBR推荐
    try:
        cbr_result = data["cbr_func"](user_id_str)
        module_results["cbr"] = {str(k): float(v) for k, v in cbr_result}
        log_info(f"CBR模块返回 {len(module_results['cbr'])} 条推荐")
    except Exception as e:
        log_error(f"CBR推荐失败：{str(e)}")
        module_results["cbr"] = {}

    # LGB推荐
    try:
        lgb_result = data["lgb_func"](user_id_str, top_n=TOP_N)
        module_results["lgb"] = {str(k): float(v) for k, v in lgb_result}
        log_info(f"LGB模块返回 {len(module_results['lgb'])} 条推荐")
    except Exception as e:
        log_error(f"LGB推荐失败：{str(e)}")
        module_results["lgb"] = {}

    # 3. 混合加权计算
    all_video_scores = {}

    # 遍历所有模块
    for module, weight in weights.items():
        score_dict = module_results.get(module, {})
        for video_id, score in score_dict.items():
            weighted_score = score * weight
            if video_id in all_video_scores:
                all_video_scores[video_id] += weighted_score
            else:
                all_video_scores[video_id] = weighted_score

    # 4. 兜底处理（无推荐结果时）
    if len(all_video_scores) == 0:
        log_warning("所有模块均无推荐结果，使用热门视频兜底")
        default_scores = np.linspace(1.0, 0.5, len(data["hot_videos"]))
        all_video_scores = dict(zip(data["hot_videos"], default_scores))

    # 5. 排序并生成最终推荐
    sorted_videos = sorted(all_video_scores.items(), key=lambda x: x[1], reverse=True)
    final_top30 = sorted_videos[:TOP_N]

    recommend_result = [
        {"video_id": vid, "final_score": round(score, 4)}
        for vid, score in final_top30
    ]

    # 打印各模块贡献
    log_info(f"\n各模块有效推荐数：")
    log_info(f"  - CF：{len(module_results['cf'])} 条")
    log_info(f"  - CBR：{len(module_results['cbr'])} 条")
    log_info(f"  - LGB：{len(module_results['lgb'])} 条")
    log_info(f"最终推荐列表：{len(recommend_result)} 条")
    log_info(f"Top5得分：{[item['final_score'] for item in recommend_result[:5]]}")

    return recommend_result


def update_recommend_after_behavior(user_id, video_id, behavior_type, weight):
    """用户行为后更新推荐列表"""
    log_info(f"\n========== 用户{user_id}产生新行为，更新推荐列表 ==========")
    write_user_real_time_behavior(user_id, video_id, behavior_type, weight)
    updated_recommend_list = get_recommend_list(user_id)

    # 保存更新后的推荐列表
    save_path = os.path.join(MIX_OUTPUT_DIR, f"user_{user_id}_recommend_updated.csv")
    pd.DataFrame(updated_recommend_list).to_csv(save_path, index=False, encoding="utf-8-sig")
    log_info(f"用户{user_id}更新后的推荐列表已保存：{save_path}")

    return updated_recommend_list


# ==============================
# 6. 模拟APP交互
# ==============================
def demo_app_interaction():
    """模拟交互流程"""
    log_info("\n========== 开始模拟交互流程 ==========")
    test_user_id = "app_user_10086"

    # 场景1：初始推荐
    log_info("\n【场景1】用户打开，请求推荐列表")
    initial_recommend = get_recommend_list(test_user_id)
    log_info(f"初始推荐Top5：{initial_recommend[:5]}")

    if initial_recommend:
        # 场景2：点赞行为
        log_info(f"\n【场景2】用户给视频{initial_recommend[0]['video_id']}点赞")
        updated_recommend = update_recommend_after_behavior(
            user_id=test_user_id,
            video_id=initial_recommend[0]["video_id"],
            behavior_type="点赞",
            weight=0.5
        )
        log_info(f"更新后推荐Top5：{updated_recommend[:5]}")

        # 场景3：观看行为
        log_info(f"\n【场景3】用户观看视频99999")
        updated_recommend_2 = update_recommend_after_behavior(
            user_id=test_user_id,
            video_id="99999",
            behavior_type="观看",
            weight=0.1
        )
        log_info(f"再次更新后推荐Top5：{updated_recommend_2[:5]}")

        # 场景4：收藏行为（转为老用户）
        log_info(f"\n【场景4】用户收藏视频88888，行为数≥3")
        updated_recommend_3 = update_recommend_after_behavior(
            user_id=test_user_id,
            video_id="88888",
            behavior_type="收藏",
            weight=1.0
        )
        log_info(f"转为老用户后推荐Top5：{updated_recommend_3[:5]}")

    log_info("\n========== 交互模拟完成 ==========")


# ==============================
# 运行入口
# ==============================
if __name__ == "__main__":
    demo_app_interaction()