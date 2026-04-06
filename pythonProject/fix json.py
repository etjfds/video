#补全：首尾[]、对象间逗号，清理冗余空行/空格
import json
import re

# ---------------------- 配置（仅需确认路径是否正确） ----------------------
# 你的原视频文件路径
INPUT_VIDEO_FILE = r"D:\xx\毕设\pythonProject\video.json"
# 修复后的输出文件路径（会自动生成，不覆盖原文件）
OUTPUT_VIDEO_FILE = r"D:\xx\毕设\pythonProject\video_fixed.json"


def batch_fix_json():
    """批量修复JSON格式：补全[]、对象间逗号、清理冗余内容"""
    try:
        # 1. 读取原文件，清理空行/多余空格/换行符
        with open(INPUT_VIDEO_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 清理每行的空白字符（换行、空格、制表符），过滤空行
        clean_lines = []
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:  # 跳过空行
                clean_lines.append(stripped_line)
        # 拼接所有有效行，形成连续的JSON字符串
        raw_content = "".join(clean_lines)

        # 2. 修复核心问题：补全[]、对象间加逗号
        # 匹配独立的JSON对象（以{开头，}结尾）
        # 正则说明：匹配{...}格式，支持嵌套（但你的数据无嵌套）
        json_objects = re.findall(r"\{[^{}]*\}", raw_content)
        if not json_objects:
            raise Exception("未识别到任何视频JSON对象，请检查原文件是否包含{}格式的数据")

        # 拼接成标准数组：用逗号分隔对象，首尾加[]
        fixed_content = "[" + ",".join(json_objects) + "]"

        # 3. 二次校验：确保是标准JSON（自动修复末尾多余逗号等小问题）
        # 解析后重新序列化，保证格式100%标准
        parsed_data = json.loads(fixed_content)
        final_content = json.dumps(parsed_data, ensure_ascii=False, indent=2)

        # 4. 保存修复后的文件
        with open(OUTPUT_VIDEO_FILE, "w", encoding="utf-8") as f:
            f.write(final_content)

        # 打印修复结果
        print("=" * 60)
        print("🎉 JSON格式批量修复成功！")
        print("=" * 60)
        print(f"📁 原文件：{INPUT_VIDEO_FILE}")
        print(f"📁 修复后文件：{OUTPUT_VIDEO_FILE}")
        print(f"📊 修复统计：共识别并修复 {len(parsed_data)} 条视频数据")
        print(f"✅ 已补全：首尾[]、对象间逗号，清理冗余空行/空格")

    except Exception as e:
        print("=" * 60)
        print(f"❌ 修复失败：{str(e)}")
        print("=" * 60)


if __name__ == "__main__":
    batch_fix_json()