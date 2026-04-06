#清除json文件所有对象间的逗号，生成新文件！目的为导入腾讯云开发
import json
import os

# 1. 定义文件路径（你的JSON文件路径）
input_json = "D:\\xx\\毕设\\pythonProject\\user_behavior.json"
# 处理后的输出文件（加_clean后缀区分，避免覆盖原文件）
output_jsonl = "D:\\xx\\毕设\\数据集\\user_behavior.json"

# 2. 检查原文件是否存在
if not os.path.exists(input_json):
    print(f"❌ 错误：未找到文件 {input_json}")
else:
    try:
        # 3. 读取并解析原JSON文件
        with open(input_json, "r", encoding="utf-8") as f:
            raw_content = f.read().strip()

        # 4. 分场景处理：兼容「数组格式」和「错误加逗号的JSON Lines」
        data_list = []
        if raw_content.startswith("[") and raw_content.endswith("]"):
            # 场景1：原文件是数组格式 [{...}, {...}] → 解析为列表
            data_list = json.loads(raw_content)
        else:
            # 场景2：原文件是JSON Lines但有多余逗号 → 逐行清理
            lines = raw_content.split("\n")
            for line in lines:
                line = line.strip()
                # 移除行尾/行首的逗号、多余空格
                if line and not line.startswith("//") and not line.startswith("#"):
                    clean_line = line.rstrip(",").strip()
                    if clean_line:
                        data_list.append(json.loads(clean_line))

        print(f"✅ 成功解析文件，共识别到 {len(data_list)} 个JSON对象")

        # 5. 生成「无对象间逗号」的JSON Lines文件（每行一个对象）
        with open(output_jsonl, "w", encoding="utf-8") as f:
            for obj in data_list:
                # 逐行写入独立JSON对象，无逗号分隔
                json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
                f.write("\n")  # 仅换行，无逗号

        print(f"\n✅ 已清除所有对象间的逗号，生成新文件！")
        print(f"处理后文件路径：{output_jsonl}")
        print("📌 新文件格式：每行一个JSON对象，对象间无逗号，可直接导入腾讯云等平台")

    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败：{e}")
        print("提示：请检查原文件是否为合法JSON格式（比如是否有未闭合的引号）")
    except Exception as e:
        print(f"❌ 处理失败：{str(e)}")