# -*- coding: utf-8 -*-
"""
LDA主题建模模块
功能：使用LDA算法提取评论主题
作者：XXX
日期：2024年12月
"""

import pandas as pd
from gensim import corpora
from gensim.models import LdaModel


# ============ 全局变量 ============
主题数量 = 4
词典 = None
语料库 = None
lda模型 = None

# 主题名称（可以根据结果手动修改）
主题名称 = {
    0: "主题1",
    1: "主题2",
    2: "主题3",
    3: "主题4"
}


def 构建语料库(分词列表):
    """
    根据分词结果构建词典和语料库
    分词列表: [[词1, 词2, ...], [词1, 词2, ...], ...]
    """
    global 词典, 语料库
    
    print("构建词典和语料库...")
    
    # 创建词典
    词典 = corpora.Dictionary(分词列表)
    
    # 过滤极端词频的词
    # no_below: 至少出现5次
    # no_above: 最多出现在50%的文档中
    词典.filter_extremes(no_below=5, no_above=0.5)
    
    # 创建语料库（词袋模型）
    语料库 = [词典.doc2bow(文本) for 文本 in 分词列表]
    
    print(f"词典大小: {len(词典)} 个词")
    print(f"文档数量: {len(语料库)} 篇")


def 训练模型(迭代次数=15):
    """训练LDA模型"""
    global lda模型
    
    if 语料库 is None:
        print("错误：请先调用 构建语料库()")
        return
    
    print(f"开始训练LDA模型，主题数: {主题数量}")
    
    lda模型 = LdaModel(
        corpus=语料库,
        id2word=词典,
        num_topics=主题数量,
        passes=迭代次数,
        alpha='auto',
        eta='auto',
        random_state=42
    )
    
    print("训练完成！")


def 获取主题关键词(每个主题词数=10):
    """获取每个主题的关键词"""
    if lda模型 is None:
        print("错误：请先训练模型")
        return {}
    
    结果 = {}
    for 主题id in range(主题数量):
        词列表 = lda模型.show_topic(主题id, topn=每个主题词数)
        结果[主题id] = 词列表
    
    return 结果


def 打印主题(每个主题词数=10):
    """打印各主题的关键词"""
    主题词 = 获取主题关键词(每个主题词数)
    
    print("\n" + "=" * 50)
    print("LDA主题建模结果")
    print("=" * 50)
    
    for 主题id, 词列表 in 主题词.items():
        词字符串 = ", ".join([f"{词}({权重:.3f})" for 词, 权重 in 词列表])
        print(f"\n{主题名称[主题id]}:")
        print(f"  {词字符串}")


def 预测单条(分词结果):
    """
    预测单条文本的主题
    返回 (主题ID, 概率)
    """
    if lda模型 is None:
        return (0, 0.0)
    
    词袋 = 词典.doc2bow(分词结果)
    主题分布 = lda模型.get_document_topics(词袋)
    
    if not 主题分布:
        return (0, 0.0)
    
    # 返回概率最高的主题
    最佳主题 = max(主题分布, key=lambda x: x[1])
    return 最佳主题


def 为评论分配主题(df):
    """
    为DataFrame中的每条评论分配主题
    需要df中有tokens列
    """
    df = df.copy()
    
    主题列表 = []
    概率列表 = []
    
    for tokens in df['tokens']:
        主题id, 概率 = 预测单条(tokens)
        主题列表.append(主题id)
        概率列表.append(概率)
    
    df['topic'] = 主题列表
    df['topic_prob'] = 概率列表
    df['topic_name'] = df['topic'].map(主题名称)
    
    # 打印统计
    print("\n主题分布统计:")
    统计 = df['topic'].value_counts().sort_index()
    for 主题id, 数量 in 统计.items():
        比例 = 数量 / len(df) * 100
        print(f"  {主题名称[主题id]}: {数量} 条 ({比例:.1f}%)")
    
    return df


def 保存主题关键词(输出路径):
    """保存主题关键词到CSV"""
    主题词 = 获取主题关键词(20)
    
    数据 = []
    for 主题id, 词列表 in 主题词.items():
        for 排名, (词, 权重) in enumerate(词列表, 1):
            数据.append({
                'topic_id': 主题id,
                'topic_name': 主题名称[主题id],
                'rank': 排名,
                'keyword': 词,
                'weight': 权重
            })
    
    df = pd.DataFrame(数据)
    df.to_csv(输出路径, index=False, encoding='utf-8-sig')
    print(f"主题关键词已保存: {输出路径}")


# ============ 兼容旧接口的类 ============
class TopicModeler:
    def __init__(self, num_topics=4):
        global 主题数量
        主题数量 = num_topics
        self.num_topics = num_topics
        self.topic_names = 主题名称
    
    def build_corpus(self, tokenized_texts):
        构建语料库(tokenized_texts)
    
    def train(self, passes=15):
        训练模型(passes)
    
    def print_topics(self, top_n=10):
        打印主题(top_n)
    
    def assign_topics(self, df):
        return 为评论分配主题(df)
    
    def get_topic_keywords(self, top_n=20):
        return 获取主题关键词(top_n)


def save_topic_keywords(modeler, output_path):
    保存主题关键词(str(output_path))


# ============ 测试 ============
if __name__ == "__main__":
    # 测试数据
    测试文本 = [
        ["华为", "手机", "好用", "流畅"],
        ["价格", "贵", "不值"],
        ["支持", "国产", "加油", "华为"],
        ["麒麟", "芯片", "5G", "技术"],
        ["手机", "系统", "好", "推荐"]
    ]
    
    构建语料库(测试文本)
    训练模型()
    打印主题()
