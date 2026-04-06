#生成虚拟的用户行为数据集
import json
import random
from datetime import datetime, timedelta
import os

# ---------------------- 核心配置（完全按你的需求，无需修改） ----------------------
USER_COUNT = 500  # 总用户数
TOTAL_BEHAVIOR_COUNT = 18000  # 总行为数（精准1.5w条）
BEHAVIOR_TYPES = ["观看", "点赞", "收藏"]  # 核心行为类型
BEHAVIOR_WEIGHTS = [0.7, 0.2, 0.1]  # 行为占比：观看70%、点赞20%、收藏10%
TIME_RANGE_DAYS = 30  # 行为时间范围：近30天
RECENT_DAYS = 15  # 近30天行为占15%（突出粉丝近期偏好）
# 你的真实视频数据绝对路径（已硬编码，直接使用）
REAL_VIDEO_FILE_PATH = r"D:\xx\毕设\pythonProject\video.json"
# 生成的用户行为文件保存路径（和视频数据同目录，自动生成）
OUTPUT_BEHAVIOR_FILE = os.path.join(os.path.dirname(REAL_VIDEO_FILE_PATH),
                                    "user_behavior.json")
# 用户行为数分布（15%新用户<3条，65%普通，20%活跃）
USER_BEHAVIOR_DISTRIBUTION = {
    "新用户（1-2条）": {"ratio": 0.15, "min": 1, "max": 2},
    "普通用户（20-35条）": {"ratio": 0.65, "min": 20, "max": 35},
    "活跃用户（40-50条）": {"ratio": 0.2, "min": 40, "max": 50}
}

# ---------------------- 工具函数 ----------------------
def load_real_video_data(file_path):
    """加载指定路径的真实视频数据，提取unique_id和content_category，按分类分组"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            video_data = json.load(f)
        # 按分类分组真实视频ID，过滤无核心字段的无效视频
        video_by_cate = {}
        invalid_count = 0  # 统计无效视频数（无unique_id/分类）
        for video in video_data:
            if "unique_id" in video and "content_category" in video:
                cate = video["content_category"]
                vid = video["unique_id"]
                if cate not in video_by_cate:
                    video_by_cate[cate] = []
                # 避免重复视频ID（若有）
                if vid not in video_by_cate[cate]:
                    video_by_cate[cate].append(vid)
            else:
                invalid_count += 1
        # 校验有效视频数据
        if not video_by_cate:
            raise Exception("未提取到有效视频数据！")
        # 打印加载信息
        print(f"✅成功加载真实视频数据！")
        print(f" -视频文件路径：{file_path}")
        print(f" -总视频数：{len(video_data)}条（有效{len(video_data)-invalid_count}条，无效{invalid_count}条）")
        print(f" -视频分类及有效ID数：")
        for cate, vids in video_by_cate.items():
            print(f"     → {cate}：{len(vids)}条真实视频ID")
        return video_by_cate
    except FileNotFoundError:
        raise Exception(f"❌ 未找到视频文件！请检查路径是否正确：{file_path}")
    except json.JSONDecodeError:
        raise Exception(f"❌ 视频文件格式错误！{file_path} 不是标准的JSON文件")
    except Exception as e:
        raise Exception(f"❌ 加载视频数据失败：{str(e)}")

def generate_user_ids(count):
    """生成500个用户ID：user_001 ~ user_500（补零格式化，美观统一）"""
    return [f"user_{str(i+1).zfill(3)}" for i in range(count)]

def assign_user_preferences(users, video_categories):
    """为用户均衡分配分类偏好（基于真实视频的分类，无人工新增）"""
    user_preferences = {}
    users_per_cate = len(users) // len(video_categories)
    # 循环分配，保证每类分类用户数均衡
    for i, cate in enumerate(video_categories):
        start_idx = i * users_per_cate
        # 最后一个分类兜底所有剩余用户，避免数量不均
        end_idx = start_idx + users_per_cate if i < len(video_categories)-1 else len(users)
        for user in users[start_idx:end_idx]:
            user_preferences[user] = cate
    return user_preferences

def assign_user_behavior_count():
    """按分布为用户分配行为数，最终精准凑齐1.5w条，无偏差"""
    user_behavior_counts = []
    remaining_users = USER_COUNT
    total_assigned = 0

    # 按比例分配各类型用户
    for config in USER_BEHAVIOR_DISTRIBUTION.values():
        user_num = int(USER_COUNT * config["ratio"])
        remaining_users -= user_num
        for _ in range(user_num):
            cnt = random.randint(config["min"], config["max"])
            user_behavior_counts.append(cnt)
            total_assigned += cnt

    # 剩余用户补充到普通用户（20-35条）
    for _ in range(remaining_users):
        cnt = random.randint(20, 35)
        user_behavior_counts.append(cnt)
        total_assigned += cnt

    # 微调总行为数至15000条，确保精准（核心步骤）
    diff = TOTAL_BEHAVIOR_COUNT - total_assigned
    for i in range(abs(diff)):
        idx = random.randint(0, len(user_behavior_counts)-1)
        user_behavior_counts[idx] += 1 if diff > 0 else -1
        # 确保行为数≥1，避免新用户行为数为0
        if user_behavior_counts[idx] < 1:
            user_behavior_counts[idx] = 1

    return user_behavior_counts

def get_random_behavior_time():
    """生成行为时间：近90天内，近30天占60%，格式YYYY-MM-DD"""
    now = datetime.now()
    # 60%概率生成近30天，40%生成31-90天
    if random.random() < 0.6:
        day_diff = random.randint(0, RECENT_DAYS - 1)
    else:
        day_diff = random.randint(RECENT_DAYS, TIME_RANGE_DAYS - 1)
    target_date = now - timedelta(days=day_diff)
    return target_date.strftime("%Y-%m-%d")

# ---------------------- 核心生成逻辑 ----------------------
def generate_behavior_data():
    try:
        print("="*60)
        print("开始基于视频数据生成用户行为数据")
        print("="*60)
        start_time = datetime.now()

        # 1. 加载真实视频数据（核心：读取你指定路径的video.json）
        video_by_cate = load_real_video_data(REAL_VIDEO_FILE_PATH)
        video_categories = list(video_by_cate.keys())  # 真实视频的分类列表

        # 2. 生成基础数据：用户ID、用户偏好、用户行为数
        users = generate_user_ids(USER_COUNT)
        user_preferences = assign_user_preferences(users, video_categories)  # 均衡分配偏好
        user_behavior_counts = assign_user_behavior_count()  # 分配行为数（含新用户）

        # 基础数据统计
        preference_count = {cate:0 for cate in video_categories}
        for pref in user_preferences.values():
            preference_count[pref] += 1
        newbie_count = sum(1 for cnt in user_behavior_counts if cnt < 3)  # 新用户数
        print(f"\n✅ 基础数据准备完成！")
        print(f"   - 总用户数：{len(users)}个（新用户{newbie_count}个，行为数<3条）")
        print(f"   - 用户偏好分布（按真实视频分类）：{preference_count}")

        # 3. 生成1.5w条用户行为数据（基于真实视频ID，允许重复行为）
        all_behavior = []
        for idx, user_id in enumerate(users):
            user_cate = user_preferences[user_id]  # 用户的偏好分类
            user_cate_vids = video_by_cate[user_cate]  # 该分类下的所有真实视频ID
            user_cnt = user_behavior_counts[idx]  # 该用户需要生成的行为数

            # 为当前用户生成指定数量的行为
            for _ in range(user_cnt):
                behavior_item = {
                    "user_id": user_id,
                    "video_unique_id": random.choice(user_cate_vids),  # 随机选真实视频ID（允许重复）
                    "behavior_type": random.choices(BEHAVIOR_TYPES, weights=BEHAVIOR_WEIGHTS)[0],
                    "behavior_time": get_random_behavior_time()
                }
                all_behavior.append(behavior_item)

            # 每生成1000条打印进度，直观查看
            if len(all_behavior) % 1000 == 0:
                print(f"📈 已生成 {len(all_behavior)}/{TOTAL_BEHAVIOR_COUNT} 条行为数据")

        # 4. 将行为数据写入JSON文件（UTF-8编码，适配腾讯云导入）
        with open(OUTPUT_BEHAVIOR_FILE, "w", encoding="utf-8") as f:
            json.dump(all_behavior, f, ensure_ascii=False, indent=2)

        # 5. 生成详细统计信息，方便验证
        total_time = (datetime.now() - start_time).total_seconds()
        # 统计行为类型分布
        behavior_type_count = {btype:0 for btype in BEHAVIOR_TYPES}
        for b in all_behavior:
            behavior_type_count[b["behavior_type"]] += 1
        # 统计各分类的行为数（真实视频分类）
        cate_behavior_count = {cate:0 for cate in video_categories}
        for b in all_behavior:
            for cate, vids in video_by_cate.items():
                if b["video_unique_id"] in vids:
                    cate_behavior_count[cate] += 1
                    break
        # 统计用户行为数分布
        behavior_range_count = {"<3条(新用户)":0, "20-35条(普通)":0, "40-50条(活跃)":0}
        for cnt in user_behavior_counts:
            if cnt < 3:
                behavior_range_count["<3条(新用户)"] += 1
            elif 20 <= cnt <= 35:
                behavior_range_count["20-35条(普通)"] += 1
            elif 40 <= cnt <= 50:
                behavior_range_count["40-50条(活跃)"] += 1

        # 打印最终结果
        print("="*60)
        print("用户行为数据生成成功！")
        print("="*60)
        print(f"📁 生成文件路径：{OUTPUT_BEHAVIOR_FILE}")
        print(f"📊 核心统计信息：")
        print(f"   1. 总行为数：{len(all_behavior)}条")
        print(f"   2. 总用户数：{len(users)}个 | {behavior_range_count}")
        print(f"   3. 行为类型分布：{behavior_type_count}")
        print(f"   4. 分类行为分布：{cate_behavior_count}")
        print(f"   5. 用户偏好分布：{preference_count}")
        print(f"   6. 生成耗时：{total_time:.2f}秒")
        print(f"   7. 核心字段：user_id / video_unique_id / behavior_type / behavior_time")

    except Exception as e:
        print(f"="*60)
        print(f"❌ 数据生成失败：{str(e)}")
        print(f"="*60)

# ---------------------- 执行生成（直接运行即可） ----------------------
if __name__ == "__main__":
    generate_behavior_data()