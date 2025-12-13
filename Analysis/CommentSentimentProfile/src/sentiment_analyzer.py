"""
情感分析模块
复用Transformers模型进行评论情感分析
"""
import pandas as pd
import numpy as np
import re
from tqdm import tqdm
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


class SentimentAnalyzer:
    def __init__(self, model_name: str = "uer/roberta-base-finetuned-jd-binary-chinese"):
        """
        初始化情感分析器
        
        Args:
            model_name: Huggingface模型名称
        """
        print(f"[Sentiment] 加载模型: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        
        print(f"[Sentiment] 使用设备: {self.device}")
    
    def analyze_single(self, text: str) -> float:
        """
        分析单条文本的情感
        
        Args:
            text: 文本
        
        Returns:
            情感得分 (0~1, 越高越正面)
        """
        if not text or len(text) < 2:
            return 0.5
        
        try:
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=512,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            probs = torch.softmax(outputs.logits, dim=1)
            positive_score = probs[0][1].item()
            
            return positive_score
            
        except Exception as e:
            print(f"[Sentiment] 分析错误: {e}")
            return 0.5
    
    def analyze_batch(self, texts: list, batch_size: int = 16) -> list:
        """
        批量分析文本情感
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
        
        Returns:
            情感得分列表
        """
        scores = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="情感分析"):
            batch_texts = texts[i:i+batch_size]
            
            # 过滤空文本
            valid_indices = [j for j, t in enumerate(batch_texts) if t and len(str(t)) >= 2]
            valid_texts = [str(batch_texts[j]) for j in valid_indices]
            
            if not valid_texts:
                scores.extend([0.5] * len(batch_texts))
                continue
            
            try:
                inputs = self.tokenizer(
                    valid_texts,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                    padding=True
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    outputs = self.model(**inputs)
                
                probs = torch.softmax(outputs.logits, dim=1)
                batch_scores = probs[:, 1].cpu().numpy().tolist()
                
                result = [0.5] * len(batch_texts)
                for idx, score in zip(valid_indices, batch_scores):
                    result[idx] = score
                
                scores.extend(result)
                
            except Exception as e:
                print(f"[Sentiment] 批处理错误: {e}")
                scores.extend([0.5] * len(batch_texts))
        
        return scores


def get_sentiment_label(score: float) -> str:
    """根据情感得分返回标签"""
    if score >= 0.7:
        return "正面"
    elif score >= 0.4:
        return "中性"
    else:
        return "负面"


def analyze_comments(df: pd.DataFrame, analyzer: SentimentAnalyzer = None) -> pd.DataFrame:
    """
    对评论进行情感分析
    
    Args:
        df: 包含content或cleaned_content列的DataFrame
        analyzer: 情感分析器实例（可选）
    
    Returns:
        添加了情感得分列的DataFrame
    """
    df = df.copy()
    
    if analyzer is None:
        analyzer = SentimentAnalyzer()
    
    # 使用清洗后的内容或原始内容
    if 'cleaned_content' in df.columns:
        texts = df['cleaned_content'].tolist()
    else:
        texts = df['content'].tolist()
    
    print(f"[Sentiment] 开始分析 {len(texts)} 条评论...")
    scores = analyzer.analyze_batch(texts)
    
    df['sentiment_score'] = scores
    df['sentiment_label'] = df['sentiment_score'].apply(get_sentiment_label)
    
    # 统计
    label_counts = df['sentiment_label'].value_counts()
    print(f"\n[Sentiment] 情感分布:")
    for label in ['正面', '中性', '负面']:
        count = label_counts.get(label, 0)
        pct = count / len(df) * 100
        print(f"  - {label}: {count} ({pct:.1f}%)")
    
    return df
