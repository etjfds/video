#把xlsx文件转换为json格式
import pandas as pd
import os
import json
import re  # 改用兼容所有Python版本的正则

# 1. 定义文件路径
input_xlsx = "D:\\xx\\毕设\\weibo_视频\\list_260203_final_cleaned.xlsx"
output_jsonl = "D:\\xx\\毕设\\weibo_视频\\list_260203_final_cleaned_legal.json"

# 2. 检查Excel文件是否存在
if not os.path.exists(input_xlsx):
    print(f"❌ 错误：未找到文件 {input_xlsx}")
else:
    try:
        # 3. 读取Excel并处理日期类型
        df = pd.read_excel(input_xlsx, engine="openpyxl")
        # 把Timestamp转为字符串（避免序列化错误）
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")

        print(f"✅ 成功读取Excel文件，共 {len(df)} 行数据")


        # 4. 兼容版：仅清理JSON非法控制字符（保留;、中文、emoji）
        def clean_illegal_chars(text):
            if isinstance(text, str):
                # 匹配ASCII控制字符（\x00-\x1F是不可见控制符，\x7F是删除符），替换为空格
                # 兼容所有Python版本，不使用\p{C}
                text = re.sub(r'[\x00-\x1F\x7F]', ' ', text)
                # 移除多余的换行/制表符（保留语义，替换为单个空格）
                text = re.sub(r'[\n\t\r]', ' ', text)
                return text.strip()  # 仅去首尾空格
            return text  # 非字符串类型直接返回


        # 替代弃用的applymap：逐列处理，实现逐元素清理
        df = df.apply(lambda col: col.map(clean_illegal_chars))

        # 5. 生成腾讯云兼容的JSON Lines文件
        with open(output_jsonl, "w", encoding="utf-8") as f:
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                # 序列化时保留所有正常字符，精简格式
                json.dump(row_dict, f, ensure_ascii=False, separators=(',', ':'))
                f.write("\n")  # 每行一个JSON对象

        print(f"\n✅ 合规JSON Lines文件生成完成！")
        print(f"文件路径：{output_jsonl}")
        print("✅ 保留了;、中文、emoji等正常字符，仅清理了非法控制字符")

    except Exception as e:
        print(f"❌ 转换失败：{str(e)}")