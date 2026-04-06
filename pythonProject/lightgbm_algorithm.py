# LightGBM推荐系统（原始算法+完整评估指标，用于对比）
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from sklearn.metrics import ndcg_score, roc_auc_score, precision_score
import lightgbm as lgb

# ==============================
# 1. 路径配置（保持你的原始路径）
# ==============================
DATA_FOLDER = "D:\\xx\\毕设\\pythonProject\\processed_data\\"
RESULT_FOLDER = "D:\\xx\\毕设\\pythonProject\\lightgbm_results_original\\"  # 新增original标识，区分优化前后
os.makedirs(RESULT_FOLDER, exist_ok=True)


# ==============================
# 2. 数据加载（保持原始逻辑，仅适配中文行为类型）
# ==============================
def load_dataset():
    """加载数据，使用中文行为类型构造label"""
    # 加载数据
    train_df = pd.read_csv(os.path.join(DATA_FOLDER, "train_set.csv"), encoding="utf-8")
    test_df = pd.read_csv(os.path.join(DATA_FOLDER, "test_set.csv"), encoding="utf-8")
    video_df = pd.read_csv(os.path.join(DATA_FOLDER, "cleaned_video.csv"), encoding="utf-8")
    video_df.rename(columns={"unique_id": "video_unique_id"}, inplace=True)

    # 数据类型转换
    for df in [train_df, test_df]:
        df["user_id"] = df["user_id"].astype(str)
        df["video_unique_id"] = df["video_unique_id"].astype(int)

    # 关联视频特征（分类+播放量）
    video_cat_map = dict(zip(video_df["video_unique_id"], video_df["content_category"]))
    video_play_map = dict(zip(video_df["video_unique_id"], video_df["play_count"]))

    for df in [train_df, test_df]:
        df["content_category"] = df["video_unique_id"].map(video_cat_map).fillna("其他")
        df["play_count"] = df["video_unique_id"].map(video_play_map).fillna(500)

        # 核心：中文行为类型→label（点赞/收藏=1，观看=0）
        df["label"] = df["behavior_type"].isin(["点赞", "收藏"]).astype(int)

    # 打印真实标签分布
    print(f"✅ 数据加载完成（原始算法）")
    print(f"  - 训练集：{len(train_df)} 行 | 测试集：{len(test_df)} 行")
    print(
        f"  - 训练集标签分布：正样本（点赞/收藏）占{train_df['label'].mean():.4f} | 负样本（观看）占{1 - train_df['label'].mean():.4f}")
    print(
        f"  - 测试集标签分布：正样本（点赞/收藏）占{test_df['label'].mean():.4f} | 负样本（观看）占{1 - test_df['label'].mean():.4f}")

    # 校验测试集是否有正样本
    if len(test_df['label'].unique()) < 2:
        print("⚠️ 测试集正样本过少，使用训练集20%数据辅助评估")
        eval_df = pd.concat([test_df, train_df.sample(frac=0.2, random_state=42)])
    else:
        eval_df = test_df

    return train_df, test_df, eval_df


# ==============================
# 3. 特征工程（完全保持原始逻辑）
# ==============================
def create_features(df):
    """构建用户/视频特征（原始版本）"""
    # 用户特征：行为次数、正样本占比
    user_feat = df.groupby("user_id").agg({
        "video_unique_id": "count",  # 用户总行为次数
        "label": "mean"  # 用户点赞/收藏占比
    }).rename(columns={
        "video_unique_id": "user_behavior_count",
        "label": "user_prefer_ratio"
    }).reset_index()

    # 视频特征：平均播放量
    video_feat = df.groupby("video_unique_id").agg({
        "play_count": "mean"
    }).rename(columns={"play_count": "video_avg_play"}).reset_index()

    # 合并特征
    df_feat = df.merge(user_feat, on="user_id", how="left")
    df_feat = df_feat.merge(video_feat, on="video_unique_id", how="left")

    # 填充缺失值
    df_feat = df_feat.fillna({
        "user_behavior_count": 0,
        "user_prefer_ratio": 0,
        "video_avg_play": df_feat["video_avg_play"].mean()
    })

    feature_cols = ["user_behavior_count", "user_prefer_ratio", "video_avg_play"]
    print(f"✅ 特征工程完成 | 特征数：{len(feature_cols)}")
    return df_feat, feature_cols


# ==============================
# 4. 安全获取用户特征（原始逻辑）
# ==============================
def get_user_features(train_feat, user_id, feat_cols):
    """安全获取用户特征，避免索引越界"""
    user_data = train_feat[train_feat["user_id"] == user_id]
    if len(user_data) > 0:
        return user_data[feat_cols].iloc[0]
    else:
        # 无数据时返回训练集均值
        default_feat = {
            "user_behavior_count": train_feat["user_behavior_count"].mean(),
            "user_prefer_ratio": train_feat["user_prefer_ratio"].mean(),
            "video_avg_play": train_feat["video_avg_play"].mean()
        }
        return pd.Series(default_feat)


# ==============================
# 5. 计算完整评估指标（新增Recall@10/MAP@10/Coverage）
# ==============================
def calculate_complete_metrics(model, eval_feat, feat_cols):
    """计算完整指标（与优化后一一对应）"""
    # 预测正样本概率
    eval_feat["pred_score"] = model.predict_proba(eval_feat[feat_cols])[:, 1]

    # 1. AUC（原始已有）
    auc_score = roc_auc_score(eval_feat['label'], eval_feat['pred_score'])

    # 2. NDCG@10（原始已有）
    # 3. Recall@10（新增）
    # 4. MAP@10（新增）
    ndcg_scores = []
    recall_scores = []
    map_scores = []
    valid_user_count = 0

    for uid in eval_feat["user_id"].unique()[:50]:
        user_data = eval_feat[eval_feat["user_id"] == uid]
        # 只计算有正/负样本的用户
        if len(user_data) >= 2 and len(user_data['label'].unique()) >= 2:
            # 按预测得分排序
            user_data_sorted = user_data.sort_values('pred_score', ascending=False)
            top10 = user_data_sorted.head(10)

            # NDCG@10
            ndcg = ndcg_score([user_data['label'].tolist()[:10]], [user_data['pred_score'].tolist()[:10]])
            ndcg_scores.append(ndcg)

            # Recall@10：Top10中真实正样本数 / 总真实正样本数
            total_pos = user_data['label'].sum()
            top10_pos = top10['label'].sum()
            recall = top10_pos / total_pos if total_pos > 0 else 0
            recall_scores.append(recall)

            # MAP@10：平均精确率均值
            precision_list = []
            hit_count = 0
            for idx, (_, row) in enumerate(top10.iterrows()):
                if row['label'] == 1:
                    hit_count += 1
                    precision_list.append(hit_count / (idx + 1))
            avg_precision = np.mean(precision_list) if precision_list else 0
            map_scores.append(avg_precision)

            valid_user_count += 1

    # 汇总排序类指标
    ndcg_10 = np.mean(ndcg_scores) if ndcg_scores else 0.0
    recall_10 = np.mean(recall_scores) if recall_scores else 0.0
    map_10 = np.mean(map_scores) if map_scores else 0.0

    # 5. Coverage（新增）：推荐视频覆盖度
    all_videos = eval_feat['video_unique_id'].nunique()
    # 获取所有用户Top10推荐的视频
    recommended_videos = []
    for uid in eval_feat["user_id"].unique()[:50]:
        user_data = eval_feat[eval_feat["user_id"] == uid].sort_values('pred_score', ascending=False)
        recommended_videos.extend(user_data.head(10)['video_unique_id'].tolist())
    recommended_videos = len(set(recommended_videos))
    coverage = recommended_videos / all_videos if all_videos > 0 else 0.0

    # 格式化输出
    print(f"✅ 完整指标计算完成 | 有效评估用户数：{valid_user_count}")
    print(f"\n📊 原始算法完整评估指标：")
    print(f"  - AUC: {auc_score:.4f}")
    print(f"  - Coverage: {coverage:.4f}")
    print(f"  - Recall@10: {recall_10:.4f}")
    print(f"  - MAP@10: {map_10:.4f}")
    print(f"  - NDCG@10: {ndcg_10:.4f}")

    return round(auc_score, 4), round(coverage, 4), round(recall_10, 4), round(map_10, 4), round(ndcg_10, 4)


# ==============================
# 6. 可视化完整指标（适配新增指标）
# ==============================
def plot_complete_metrics(auc, coverage, recall, map_score, ndcg):
    """绘制完整指标图表（与优化后格式一致）"""
    plt.rcParams["font.sans-serif"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(12, 6))
    metrics = ["AUC", "Coverage", "Recall@10", "MAP@10", "NDCG@10"]
    values = [auc, coverage, recall, map_score, ndcg]
    colors = ["#2E86AB", "#F18F01", "#C73E1D", "#6A994E", "#7209B7"]

    # 绘制柱状图
    bars = ax.bar(metrics, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1)

    # 添加数值标签
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.,
            bar.get_height() + 0.01,
            f"{val:.4f}",
            ha='center', va='bottom',
            fontweight='bold', fontsize=12
        )

    # 图表美化
    ax.set_title("LightGBM视频推荐模型原始算法完整评估指标", fontsize=16, fontweight='bold', pad=20)
    ax.set_ylabel("指标值", fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1.0)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # 保存高分辨率图表
    plt.tight_layout()
    plt.savefig(
        os.path.join(RESULT_FOLDER, "原始算法完整评估指标图表.png"),
        dpi=300, bbox_inches='tight'
    )
    plt.close()
    print("✅ 原始算法指标图表保存完成（300dpi）")


# ==============================
# 7. 生成推荐结果（保持原始逻辑）
# ==============================
def generate_recommendations(model, train_feat, test_feat, feat_cols):
    """生成用户Top-10推荐（原始逻辑）"""
    target_users = test_feat["user_id"].unique()[:50]
    candidate_videos = train_feat["video_unique_id"].unique()[:200]
    reco_results = []
    valid_user_count = 0

    for user_id in target_users:
        try:
            # 排除已交互视频
            interacted_videos = train_feat[train_feat["user_id"] == user_id]["video_unique_id"].tolist()
            valid_candidates = [v for v in candidate_videos if v not in interacted_videos]

            # 确保至少10个候选
            if len(valid_candidates) < 10:
                valid_candidates = candidate_videos[:10]

            # 获取用户特征
            user_feat_vals = get_user_features(train_feat, user_id, feat_cols)

            # 构建候选特征
            candidate_df = pd.DataFrame({"video_unique_id": valid_candidates[:30]})
            for col in feat_cols:
                candidate_df[col] = user_feat_vals[col]

            # 预测概率
            candidate_df["pred_prefer_prob"] = model.predict_proba(candidate_df[feat_cols])[:, 1]

            # 排序取Top-10
            top10_videos = candidate_df.sort_values("pred_prefer_prob", ascending=False).head(10)

            # 整理结果
            reco_results.append({
                "用户ID": user_id,
                "Top10推荐视频ID": ",".join(map(str, top10_videos["video_unique_id"].tolist())),
                "对应推荐概率": ",".join([f"{s:.4f}" for s in top10_videos["pred_prefer_prob"].tolist()])
            })
            valid_user_count += 1

        except Exception as e:
            print(f"⚠️ 用户 {user_id} 推荐生成失败：{str(e)[:50]}")
            continue

    # 保存推荐结果
    reco_df = pd.DataFrame(reco_results)
    reco_df.to_csv(
        os.path.join(RESULT_FOLDER, "原始算法用户推荐结果.csv"),
        index=False,
        encoding="utf-8-sig"
    )
    print(f"\n✅ 原始算法推荐结果生成完成 | 成功为 {valid_user_count} 个用户生成推荐")
    return reco_df


# ==============================
# 8. 主函数（执行全流程+完整指标）
# ==============================
def run_original_system():
    print("=" * 70)
    print("🎯 LightGBM推荐系统（原始算法+完整评估指标）")
    print("=" * 70)

    # 步骤1：加载数据
    train_data, test_data, eval_data = load_dataset()

    # 步骤2：构建特征
    train_feat, feat_cols = create_features(train_data)
    test_feat, _ = create_features(test_data)
    eval_feat, _ = create_features(eval_data)

    # 步骤3：训练模型（原始参数）
    model = lgb.LGBMClassifier(
        n_estimators=50,
        learning_rate=0.06,
        num_leaves=20,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )

    print("\n🚀 开始训练原始模型...")
    model.fit(train_feat[feat_cols], train_feat["label"])
    print("✅ 原始模型训练完成")

    # 步骤4：生成推荐结果
    generate_recommendations(model, train_feat, test_feat, feat_cols)

    # 步骤5：计算完整指标（新增核心）
    auc, coverage, recall_10, map_10, ndcg_10 = calculate_complete_metrics(model, eval_feat, feat_cols)

    # 步骤6：保存完整指标（与优化后格式一致）
    metrics_df = pd.DataFrame({
        "AUC": [auc],
        "Coverage": [coverage],
        "Recall@10": [recall_10],
        "MAP@10": [map_10],
        "NDCG@10": [ndcg_10],
        "LightGBM版本": [lgb.__version__],
        "有效评估用户数": [len([uid for uid in eval_feat["user_id"].unique()[:50] if len(eval_feat[eval_feat["user_id"]==uid])>=2])]
    })
    metrics_df.to_csv(
        os.path.join(RESULT_FOLDER, "原始算法完整评估指标.csv"),
        index=False,
        encoding="utf-8-sig"
    )
    print("✅ 原始算法完整指标保存完成")

    # 步骤7：可视化完整指标
    plot_complete_metrics(auc, coverage, recall_10, map_10, ndcg_10)

    # 最终结果打印
    print("\n" + "=" * 50)
    print("📊 原始算法最终完整指标：")
    print(f"  - AUC: {auc:.4f}")
    print(f"  - Coverage: {coverage:.4f}")
    print(f"  - Recall@10: {recall_10:.4f}")
    print(f"  - MAP@10: {map_10:.4f}")
    print(f"  - NDCG@10: {ndcg_10:.4f}")
    print("=" * 50)
    print(f"\n🎉 原始算法所有文件已保存至：{RESULT_FOLDER}")
    print("📁 生成文件清单：")
    print("  1. 原始算法完整评估指标.csv - 5个核心指标（与优化后对齐）")
    print("  2. 原始算法用户推荐结果.csv - 50个用户Top-10推荐")
    print("  3. 原始算法完整评估指标图表.png - 高分辨率可视化图表")
    print("=" * 70)


# ==============================
# 运行入口
# ==============================
if __name__ == "__main__":
    run_original_system()