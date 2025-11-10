import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from 主干.模型.Doubao_seed_1_6 import DouBaoModel
from 主干.模型.prompts import SystemPromptTemplate
from 支线.教育.文案检查与替换 import check_single_text

def process_texts(input_file, output_file, content_type="学校介绍", callback=None):
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)

    # 初始化输出文件为一个空数组
    if not os.path.exists(output_file):
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

    def process_single_text(original_text, index, total):
        # 为每个线程创建独立的模型实例
        model = DouBaoModel()
        systemprompttemplate = SystemPromptTemplate(type=content_type)  # 使用传入的文案类型
        
        # 读取现有数据
        with open(output_file, "r", encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
        print(f"当前文案数量:{len(data)}, 总数:{total}")

        # 调用回调函数显示原始文案
        if callback:
            callback("original", index, original_text)
        else:
            print("=" * 50 + f"原始文案[{index}]" + "=" * 50 + "\n", original_text)
            
        result = "重写文案"
        while result == "重写文案":
            system_prompt = systemprompttemplate.choice_system_prompt(reference_text=original_text)
            response = model.generate_text(system_prompt)
            # 确保response是字符串类型
            if not isinstance(response, str):
                response = ""
            result = check_single_text(response)
            if result == "重写文案":
                if callback:
                    callback("rewrite", index, "")
                else:
                    print("=" * 50 + f"需要重写，重新生成[{index}]..." + "=" * 50 + "\n")
            else:
                # 调用回调函数显示最终文案
                if callback:
                    callback("result", index, result)
                else:
                    print("=" * 50 + f"最终文案[{index}]:" + "=" * 50 + "\n", result)
        
        return result

    def save_result(result):
        # 读取现有数据
        with open(output_file, "r", encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
        
        # 添加新结果
        data.append(result)
        
        # 写回文件
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_processed_count():
        """获取已处理的文案数量"""
        if not os.path.exists(output_file):
            return 0
        try:
            with open(output_file, "r", encoding='utf-8') as f:
                data = json.load(f)
                return len(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return 0

    with open(input_file, 'r', encoding='utf-8') as f:
        original_school_texts = json.load(f)

    # 获取已处理的文案数量，实现断点续传
    processed_count = get_processed_count()
    print(f"检测到已处理 {processed_count} 条文案，从第 {processed_count + 1} 条开始继续处理...")

    # 使用线程池处理文案，最多3个线程
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 只处理未完成的文案（从processed_count开始）
        future_to_index = {
            executor.submit(process_single_text, text, i, len(original_school_texts)): i 
            for i, text in enumerate(original_school_texts[processed_count:], start=processed_count)
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                save_result(result)
                print(f"✅ 第 {index} 个文案处理完成")
            except Exception as e:
                print(f"❌ 处理第 {index} 个文案时出错: {e}")