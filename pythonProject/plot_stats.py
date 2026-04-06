import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ---------------------- 1. 配置中文显示（解决乱码问题） ----------------------
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用SimHei字体显示中文
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示问题
plt.rcParams['figure.dpi'] = 100              # 图表清晰度

# ---------------------- 2. 从你的统计信息中提取的数据 ----------------------
# 数据1：用户偏好分布（按视频分类）
preference_cate = ['其他', '舞台', '影视', '物料']
preference_count = [125, 125, 125, 125]
preference_color = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']

# 数据2：行为类型分布
behavior_type = ['观看', '点赞', '收藏']
behavior_count = [10455, 3085, 1460]
behavior_color = ['#FF9999', '#66B2FF', '#99FF99']

# 数据3：分类行为分布（各视频分类对应的行为数）
cate_behavior_cate = ['其他', '舞台', '影视', '物料']
cate_behavior_count = [1867, 3762, 3791, 5580]
cate_behavior_color = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']

# 数据4：用户行为数分布
user_behavior_range = ['<3条（新用户）', '20-35条（普通）', '40-50条（活跃）']
user_behavior_range_count = [7, 268, 80]
user_behavior_range_color = ['#FF6347', '#32CD32', '#1E90FF']

# ---------------------- 3. 创建组合图表（4个子图） ----------------------
fig, axes = plt.subplots(2, 2, figsize=(14, 10))  # 2行2列的子图，尺寸14x10
fig.suptitle('用户行为数据统计图表', fontsize=16, fontweight='bold', y=0.98)

# 子图1：用户偏好分布（饼图）
axes[0, 0].pie(preference_count, labels=preference_cate, colors=preference_color,
               autopct='%1.1f%%', startangle=90, textprops={'fontsize': 10})
axes[0, 0].set_title('用户偏好分布（按视频分类）', fontsize=12, fontweight='bold', pad=10)

# 子图2：行为类型分布（柱状图）
bars2 = axes[0, 1].bar(behavior_type, behavior_count, color=behavior_color, width=0.6)
axes[0, 1].set_title('行为类型分布', fontsize=12, fontweight='bold', pad=10)
axes[0, 1].set_ylabel('行为数量')
# 在柱子上添加数值标签
for bar in bars2:
    height = bar.get_height()
    axes[0, 1].text(bar.get_x() + bar.get_width()/2., height + 100,
                    f'{height}', ha='center', va='bottom', fontsize=9)

# 子图3：分类行为分布（柱状图）
bars3 = axes[1, 0].bar(cate_behavior_cate, cate_behavior_count, color=cate_behavior_color, width=0.6)
axes[1, 0].set_title('各视频分类对应的行为数', fontsize=12, fontweight='bold', pad=10)
axes[1, 0].set_ylabel('行为数量')
# 在柱子上添加数值标签
for bar in bars3:
    height = bar.get_height()
    axes[1, 0].text(bar.get_x() + bar.get_width()/2., height + 50,
                    f'{height}', ha='center', va='bottom', fontsize=9)

# 子图4：用户行为数分布（柱状图）
bars4 = axes[1, 1].bar(user_behavior_range, user_behavior_range_count, color=user_behavior_range_color, width=0.6)
axes[1, 1].set_title('用户行为数分布', fontsize=12, fontweight='bold', pad=10)
axes[1, 1].set_ylabel('用户数量')
# 在柱子上添加数值标签
for bar in bars4:
    height = bar.get_height()
    axes[1, 1].text(bar.get_x() + bar.get_width()/2., height + 2,
                    f'{height}', ha='center', va='bottom', fontsize=9)

# 调整子图间距，避免标题重叠
plt.tight_layout(rect=[0, 0, 1, 0.95])  # 留出顶部标题的空间

# ---------------------- 4. 保存图片+显示图表 ----------------------
plt.savefig('user_behavior_stats.png', dpi=300, bbox_inches='tight')  # 保存为高清图片
plt.show()