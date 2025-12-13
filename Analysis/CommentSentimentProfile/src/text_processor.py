"""
文本预处理模块
清洗、分词、停用词过滤
"""
import pandas as pd
import numpy as np
import re
import jieba
from pathlib import Path


# 添加华为相关词汇到词典
CUSTOM_WORDS = [
    "华为", "麒麟", "鸿蒙", "HarmonyOS", "EMUI",
    "Mate60", "Mate70", "Mate80", "MateX",
    "P60", "P70", "P80", "nova",
    "FreeBuds", "MatePad", "MateBook",
    "遥遥领先", "5G", "卫星通信", "北斗",
    "任正非", "余承东", "大嘴"
]

for word in CUSTOM_WORDS:
    jieba.add_word(word)

# 停用词（基础版，可扩展）
STOPWORDS = set([
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "他", "她", "它", "们", "这个", "那个", "什么", "怎么",
    "可以", "没", "把", "被", "让", "给", "但", "还", "吗", "呢", "啊", "吧",
    "哈哈", "哈哈哈", "啦", "呀", "哦", "嗯", "额", "emmm", "emm",
    "真的", "感觉", "觉得", "知道", "应该", "可能", "因为", "所以", "如果",
    "比较", "非常", "特别", "已经", "还是", "或者", "但是", "然后", "其实"
])


def clean_text(text) -> str:
    """
    清洗文本
    
    Args:
        text: 原始文本
    
    Returns:
        清洗后的文本
    """
    if pd.isna(text) or text is None:
        return ""
    
    text = str(text)
    
    # 去除表情符号 [xxx]
    text = re.sub(r'\[.*?\]', '', text)
    # 去除 @用户
    text = re.sub(r'@\S+', '', text)
    # 去除 URL
    text = re.sub(r'http\S+', '', text)
    # 去除特殊符号，保留中英文和数字
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def tokenize(text: str) -> list:
    """
    分词
    
    Args:
        text: 清洗后的文本
    
    Returns:
        分词结果列表
    """
    if not text:
        return []
    
    words = list(jieba.cut(text))
    
    # 过滤停用词、单字、纯数字
    filtered = []
    for word in words:
        word = word.strip()
        if not word:
            continue
        if word in STOPWORDS:
            continue
        if len(word) == 1 and word not in CUSTOM_WORDS:
            continue
        if word.isdigit():
            continue
        filtered.append(word)
    
    return filtered


def process_comments(df: pd.DataFrame, min_words: int = 3) -> pd.DataFrame:
    """
    处理评论数据
    
    Args:
        df: 评论DataFrame
        min_words: 最少词数（过滤短评论）
    
    Returns:
        添加了清洗和分词结果的DataFrame
    """
    df = df.copy()
    
    # 清洗文本
    df['cleaned_content'] = df['content'].apply(clean_text)
    
    # 分词
    df['tokens'] = df['cleaned_content'].apply(tokenize)
    
    # 词数
    df['token_count'] = df['tokens'].apply(len)
    
    # 过滤短评论
    original_count = len(df)
    df = df[df['token_count'] >= min_words].reset_index(drop=True)
    filtered_count = original_count - len(df)
    
    print(f"[Text Processor] 原始评论: {original_count} 条")
    print(f"[Text Processor] 过滤短评论: {filtered_count} 条")
    print(f"[Text Processor] 有效评论: {len(df)} 条")
    
    return df


def get_all_tokens(df: pd.DataFrame) -> list:
    """获取所有分词结果（用于LDA）"""
    return df['tokens'].tolist()


def get_word_frequency(df: pd.DataFrame, top_n: int = 100) -> dict:
    """
    统计词频
    
    Args:
        df: 处理后的DataFrame
        top_n: 返回前N个高频词
    
    Returns:
        词频字典
    """
    from collections import Counter
    
    all_words = []
    for tokens in df['tokens']:
        all_words.extend(tokens)
    
    word_counts = Counter(all_words)
    return dict(word_counts.most_common(top_n))


if __name__ == "__main__":
    # 测试
    test_texts = [
        "华为Mate60真的太好用了！支持国产[赞][赞]",
        "这个手机太贵了@用户 不值得买",
        "麒麟芯片遥遥领先 http://example.com",
        "好",
        "666"
    ]
    
    for text in test_texts:
        cleaned = clean_text(text)
        tokens = tokenize(cleaned)
        print(f"原文: {text}")
        print(f"清洗: {cleaned}")
        print(f"分词: {tokens}\n")
