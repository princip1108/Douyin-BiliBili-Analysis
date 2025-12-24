# -*- coding: utf-8 -*-
"""
文本预处理模块
功能：清洗文本、中文分词、去停用词
作者：XXX
日期：2024年12月
"""

import pandas as pd
import re
import jieba

# ============ 自定义词典 ============
# 添加华为相关专有名词，让分词更准确
自定义词汇 = [
    "华为", "麒麟", "鸿蒙", "HarmonyOS", "EMUI",
    "Mate60", "Mate70", "P60", "P70", "nova",
    "遥遥领先", "5G", "卫星通信", "北斗",
    "任正非", "余承东"
]

for 词 in 自定义词汇:
    jieba.add_word(词)


# ============ 停用词表 ============
停用词 = set([
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "他", "她", "它", "们", "这个", "那个", "什么", "怎么",
    "可以", "没", "把", "被", "让", "给", "但", "还", "吗", "呢", "啊", "吧",
    "哈哈", "哈哈哈", "啦", "呀", "哦", "嗯", "额",
    "真的", "感觉", "觉得", "知道", "应该", "可能", "因为", "所以", "如果",
    "比较", "非常", "特别", "已经", "还是", "或者", "但是", "然后", "其实"
])


def 清洗文本(文本):
    """
    清洗评论文本
    去除表情、@用户、链接等无用信息
    """
    if pd.isna(文本) or 文本 is None:
        return ""
    
    文本 = str(文本)
    
    # 去除表情 [xxx]
    文本 = re.sub(r'\[.*?\]', '', 文本)
    # 去除@用户
    文本 = re.sub(r'@\S+', '', 文本)
    # 去除网址
    文本 = re.sub(r'http\S+', '', 文本)
    # 只保留中英文和数字
    文本 = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', 文本)
    # 去除多余空格
    文本 = re.sub(r'\s+', ' ', 文本)
    
    return 文本.strip()


def 分词(文本):
    """
    对文本进行中文分词
    返回词语列表
    """
    if not 文本:
        return []
    
    # jieba分词
    词列表 = list(jieba.cut(文本))
    
    # 过滤
    结果 = []
    for 词 in 词列表:
        词 = 词.strip()
        # 跳过空词
        if not 词:
            continue
        # 跳过停用词
        if 词 in 停用词:
            continue
        # 跳过单个字（专有名词除外）
        if len(词) == 1 and 词 not in 自定义词汇:
            continue
        # 跳过纯数字
        if 词.isdigit():
            continue
        结果.append(词)
    
    return 结果


def 处理评论(df, 最少词数=3):
    """
    处理评论数据
    添加清洗后文本和分词结果
    """
    df = df.copy()
    
    print("开始文本预处理...")
    
    # 清洗文本
    df['cleaned_content'] = df['content'].apply(清洗文本)
    
    # 分词
    df['tokens'] = df['cleaned_content'].apply(分词)
    
    # 计算词数
    df['token_count'] = df['tokens'].apply(len)
    
    # 过滤太短的评论
    原始数量 = len(df)
    df = df[df['token_count'] >= 最少词数].reset_index(drop=True)
    过滤数量 = 原始数量 - len(df)
    
    print(f"原始评论: {原始数量} 条")
    print(f"过滤短评论: {过滤数量} 条")
    print(f"有效评论: {len(df)} 条")
    
    return df


def 获取所有词语(df):
    """获取所有分词结果，用于LDA"""
    return df['tokens'].tolist()


def 统计词频(df, 前N个=100):
    """统计高频词"""
    from collections import Counter
    
    所有词 = []
    for tokens in df['tokens']:
        所有词.extend(tokens)
    
    词频 = Counter(所有词)
    return dict(词频.most_common(前N个))


# ============ 兼容旧接口 ============
def clean_text(text):
    return 清洗文本(text)

def tokenize(text):
    return 分词(text)

def process_comments(df, min_words=3):
    return 处理评论(df, min_words)

def get_all_tokens(df):
    return 获取所有词语(df)

def get_word_frequency(df, top_n=100):
    return 统计词频(df, top_n)


# ============ 测试 ============
if __name__ == "__main__":
    测试文本 = [
        "华为Mate60真的太好用了！支持国产[赞][赞]",
        "这个手机太贵了@用户 不值得买",
        "麒麟芯片遥遥领先 http://example.com"
    ]
    
    print("测试文本预处理：\n")
    for 文本 in 测试文本:
        清洗后 = 清洗文本(文本)
        词列表 = 分词(清洗后)
        print(f"原文: {文本}")
        print(f"清洗: {清洗后}")
        print(f"分词: {词列表}\n")
