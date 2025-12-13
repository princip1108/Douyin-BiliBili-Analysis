"""
LDA主题建模模块
"""
import pandas as pd
import numpy as np
from gensim import corpora
from gensim.models import LdaModel
from collections import defaultdict


class TopicModeler:
    def __init__(self, num_topics: int = 4):
        """
        初始化主题建模器
        
        Args:
            num_topics: 主题数量
        """
        self.num_topics = num_topics
        self.dictionary = None
        self.corpus = None
        self.model = None
        self.topic_names = {
            0: "主题1",
            1: "主题2", 
            2: "主题3",
            3: "主题4"
        }
    
    def build_corpus(self, tokenized_texts: list):
        """
        构建词典和语料库
        
        Args:
            tokenized_texts: 分词后的文本列表
        """
        # 创建词典
        self.dictionary = corpora.Dictionary(tokenized_texts)
        
        # 过滤极端词频
        self.dictionary.filter_extremes(no_below=5, no_above=0.5)
        
        # 创建语料库
        self.corpus = [self.dictionary.doc2bow(text) for text in tokenized_texts]
        
        print(f"[LDA] 词典大小: {len(self.dictionary)} 词")
        print(f"[LDA] 语料库大小: {len(self.corpus)} 文档")
    
    def train(self, passes: int = 15, random_state: int = 42):
        """
        训练LDA模型
        
        Args:
            passes: 迭代次数
            random_state: 随机种子
        """
        if self.corpus is None:
            raise ValueError("请先调用 build_corpus() 构建语料库")
        
        print(f"[LDA] 开始训练，主题数: {self.num_topics}")
        
        self.model = LdaModel(
            corpus=self.corpus,
            id2word=self.dictionary,
            num_topics=self.num_topics,
            passes=passes,
            alpha='auto',
            eta='auto',
            random_state=random_state
        )
        
        print("[LDA] 训练完成")
    
    def get_topic_keywords(self, top_n: int = 20) -> dict:
        """
        获取各主题关键词
        
        Args:
            top_n: 每个主题的关键词数量
        
        Returns:
            {topic_id: [(word, weight), ...]}
        """
        if self.model is None:
            raise ValueError("请先训练模型")
        
        topics = {}
        for topic_id in range(self.num_topics):
            words = self.model.show_topic(topic_id, topn=top_n)
            topics[topic_id] = words
        
        return topics
    
    def get_document_topic(self, tokens: list) -> tuple:
        """
        获取单个文档的主题分布
        
        Args:
            tokens: 分词后的词列表
        
        Returns:
            (主题ID, 概率)
        """
        if self.model is None:
            raise ValueError("请先训练模型")
        
        bow = self.dictionary.doc2bow(tokens)
        topic_dist = self.model.get_document_topics(bow)
        
        if not topic_dist:
            return (0, 0.0)
        
        # 返回概率最高的主题
        best_topic = max(topic_dist, key=lambda x: x[1])
        return best_topic
    
    def assign_topics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        为DataFrame中的每条评论分配主题
        
        Args:
            df: 包含tokens列的DataFrame
        
        Returns:
            添加了topic和topic_prob列的DataFrame
        """
        df = df.copy()
        
        topics = []
        probs = []
        
        for tokens in df['tokens']:
            topic_id, prob = self.get_document_topic(tokens)
            topics.append(topic_id)
            probs.append(prob)
        
        df['topic'] = topics
        df['topic_prob'] = probs
        df['topic_name'] = df['topic'].map(self.topic_names)
        
        # 统计主题分布
        topic_counts = df['topic'].value_counts().sort_index()
        print("\n[LDA] 主题分布:")
        for topic_id, count in topic_counts.items():
            pct = count / len(df) * 100
            print(f"  - {self.topic_names[topic_id]}: {count} ({pct:.1f}%)")
        
        return df
    
    def print_topics(self, top_n: int = 10):
        """打印各主题关键词"""
        topics = self.get_topic_keywords(top_n)
        
        print("\n" + "="*50)
        print("LDA 主题关键词")
        print("="*50)
        
        for topic_id, words in topics.items():
            word_str = ", ".join([f"{w}({p:.3f})" for w, p in words[:10]])
            print(f"\n{self.topic_names[topic_id]}:")
            print(f"  {word_str}")
    
    def update_topic_names(self, names: dict):
        """
        更新主题名称
        
        Args:
            names: {topic_id: name}
        """
        self.topic_names.update(names)


def save_topic_keywords(modeler: TopicModeler, output_path: str):
    """
    保存主题关键词到CSV
    
    Args:
        modeler: 训练好的TopicModeler
        output_path: 输出路径
    """
    topics = modeler.get_topic_keywords(top_n=20)
    
    rows = []
    for topic_id, words in topics.items():
        for rank, (word, weight) in enumerate(words, 1):
            rows.append({
                'topic_id': topic_id,
                'topic_name': modeler.topic_names[topic_id],
                'rank': rank,
                'keyword': word,
                'weight': weight
            })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"[LDA] 主题关键词已保存: {output_path}")


if __name__ == "__main__":
    # 测试
    test_texts = [
        ["华为", "手机", "好用", "流畅"],
        ["价格", "贵", "不值"],
        ["支持", "国产", "加油", "华为"],
        ["麒麟", "芯片", "5G", "技术"],
        ["手机", "系统", "好", "推荐"]
    ]
    
    modeler = TopicModeler(num_topics=2)
    modeler.build_corpus(test_texts)
    modeler.train()
    modeler.print_topics()
