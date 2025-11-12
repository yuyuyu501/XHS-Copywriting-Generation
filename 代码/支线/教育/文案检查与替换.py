#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import random
from openai import OpenAI
import hashlib
from collections import defaultdict

# === 配置 ===
SCHOOL_CSV = "D:\\小红书文案2\\代码\\支线\\教育\\guangzhou_all_schools.csv"

client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="baea195a-fe33-4be1-9c68-9292a4a66a5c",
)
MODEL = "doubao-seed-1-6-250615"

# === 1. 读取 CSV 原始内容（给 AI 用）===
with open(SCHOOL_CSV, encoding="utf-8") as f:
    CSV_RAW_CONTENT = f.read()

# === 2. 提取所有学校名（跳过表头，用于随机兜底）===
def load_school_names_for_fallback(csv_path):
    with open(csv_path, encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
    if not lines:
        return []
    # 跳过第一行（表头），其余每行取第一个字段（假设学校名在第一列）
    school_names = []
    for line in lines[1:]:
        if line.strip():
            # 按逗号分割，取第一个字段并去除引号（兼容标准 CSV）
            name = line.split(',')[0].strip().strip('"')
            if name:
                school_names.append(name)
    return school_names

ALL_SCHOOLS_FOR_FALLBACK = load_school_names_for_fallback(SCHOOL_CSV)
print(f"✅ 已加载 {len(ALL_SCHOOLS_FOR_FALLBACK)} 所学校用于兜底随机选择。")

# 存储每个学校被选中的次数，用于权重计算
school_selection_count = defaultdict(int)

def get_weighted_random_school():
    """
    根据学校被选中的次数分配权重，选中次数越少的学校权重越高
    """
    if not ALL_SCHOOLS_FOR_FALLBACK:
        return "广州市第一中学"  # 最终 fallback
    
    # 计算每个学校的权重（选中次数越少，权重越高）
    weights = []
    for school in ALL_SCHOOLS_FOR_FALLBACK:
        # 使用选中次数的倒数作为权重基础，确保未选中的学校也有权重
        selections = school_selection_count[school]
        # 权重计算：1 / (1 + 选中次数)，避免除零错误
        weight = 1.0 / (1 + selections)
        weights.append(weight)
    
    # 使用权重随机选择学校
    selected_school = random.choices(ALL_SCHOOLS_FOR_FALLBACK, weights=weights, k=1)[0]
    
    # 更新选中次数
    school_selection_count[selected_school] += 1
    
    return selected_school

def get_random_school():
    return get_weighted_random_school()

# === 提示词（同前，略作精简）===
def build_prompt(text):
    return f"""你是一个广州教育文案审核专家。以下是一个包含广州市所有合法学校的 CSV 文件的完整原始内容：

--- CSV START ---
{CSV_RAW_CONTENT}
--- CSV END ---

请严格审核文案中的学校名称：
- 若提到模糊词（如"这所学校""【这所学校】""某中学"），必须替换为 CSV 中存在的真实校名；
- 若拼写错误或虚构，必须纠正；
- 若完全正确，返回正常；
- 若完全无关，返回无相关内容。

❗ 强制：只要涉及学校，"replace" 必须是非空的真实校名。

待审核文案：
{text}

仅输出 JSON，格式：
- 有错误/缺失：{{"original": "...", "replace": "真实校名"}}
- 正常：{{"status": "文案正常，不用修改"}}
- 无关：{{"status": "无学校相关内容"}}
"""

def parse_originals(original_str):
    """
    将 "original" 字符串解析为多个待替换词列表。
    支持分隔符：顿号、逗号、分号、空格、换行等。
    """
    if not original_str:
        return []
    # 使用正则分割多种分隔符，过滤空字符串
    parts = re.split(r'[、，,;\s]+', original_str.strip())
    return [p for p in parts if p]

def apply_replacements(text, originals, replace_target):
    """
    对 text 中的每个 original 执行字面替换（非正则）。
    按长度降序替换，避免短词干扰长词（如先换"广州市第一中学"，再换"中学"）。
    """
    if not originals or not replace_target:
        return text

    # 按长度降序排序，防止部分匹配（例如避免"学校"先被换掉）
    sorted_originals = sorted(originals, key=len, reverse=True)
    result = text
    for orig in sorted_originals:
        result = result.replace(orig, replace_target)
    return result

def check_single_text(text):
    # 检查text是否为None或空字符串
    if not text or not isinstance(text, str):
        return "重写文案"
    
    if not text.strip():
        return "重写文案"
    
    prompt = build_prompt(text)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150,
        )
        # 安全地获取响应内容
        content = ""
        if response and response.choices and len(response.choices) > 0:
            choice = response.choices[0]
            if choice and hasattr(choice, 'message'):
                message = choice.message
                if message and hasattr(message, 'content') and message.content is not None:
                    content = message.content
        raw = content.strip() if content else ""
        print("审核结果：", raw)
        result = json.loads(raw)
        
        # === 关键兜底逻辑：如果 AI 返回了空 replace，自动补一个随机学校 ===
        if "original" in result and "replace" in result:
            replace_value = result["replace"]
            # 检查replace_value是否为None或空字符串
            if not replace_value or (isinstance(replace_value, str) and not replace_value.strip()):
                result["replace"] = get_random_school()
                result["note"] = "AI 返回空 replace，已自动随机补全"
            
            # 应用替换并生成最终文案
            orig_str = result["original"]
            repl_str = result["replace"]
            if orig_str and repl_str:
                originals = parse_originals(orig_str)
                final_text = apply_replacements(text, originals, repl_str)
                return final_text
        
        # 如果返回"无学校相关内容"，则返回重写文案
        if result.get("status") == "无学校相关内容":
            return "重写文案"
        
        # 如果文案正常，返回原文案
        if result.get("status") == "文案正常，不用修改":
            return text
            
        return "重写文案"
    except Exception as e:
        # 确保raw变量已定义
        raw = locals().get('raw', '')
        print(f"AI 审核失败: {str(e)}")
        return "重写文案"
