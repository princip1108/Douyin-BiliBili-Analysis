"""
情感分析模块
使用Transformers预训练模型进行中文情感分析
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
        
        # 使用GPU（如果可用）
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        
        print(f"[Sentiment] 使用设备: {self.device}")
    
    def preprocess_text(self, text) -> str:
        """
        文本预处理
        
        Args:
            text: 原始文本
        
        Returns:
            清洗后的文本
        """
        if pd.isna(text) or text is None:
            return ""
        
        text = str(text)
        
        # 去除hashtag符号但保留文字
        text = re.sub(r'#(\S+)', r'\1', text)
        # 去除@用户
        text = re.sub(r'@\S+', '', text)
        # 去除URL
        text = re.sub(r'http\S+', '', text)
        # 去除表情符号 [xxx]
        text = re.sub(r'\[.*?\]', '', text)
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def analyze_single(self, text: str) -> float:
        """
        分析单条文本的情感
        
        Args:
            text: 预处理后的文本
        
        Returns:
            情感得分 (0~1, 越高越正面)
        """
        if not text or len(text) < 2:
            return 0.5  # 空文本返回中性
        
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
            
            # 模型输出: 0=负面, 1=正面 (或相反，取决于模型)
            # 大多数情感模型: index 1 = positive
            positive_score = probs[0][1].item()
            
            return positive_score
            
        except Exception as e:
            print(f"[Sentiment] 分析错误: {e}, 文本: {text[:50]}...")
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
            
            # 预处理
            processed = [self.preprocess_text(t) for t in batch_texts]
            
            # 过滤空文本
            valid_indices = [j for j, t in enumerate(processed) if t and len(t) >= 2]
            valid_texts = [processed[j] for j in valid_indices]
            
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
                
                # 将得分填回原位置
                result = [0.5] * len(batch_texts)
                for idx, score in zip(valid_indices, batch_scores):
                    result[idx] = score
                
                scores.extend(result)
                
            except Exception as e:
                print(f"[Sentiment] 批处理错误: {e}")
                scores.extend([0.5] * len(batch_texts))
        
        return scores


def get_sentiment_label(score: float) -> str:
    """
    根据情感得分返回标签
    
    Args:
        score: 情感得分 (0~1)
    
    Returns:
        情感标签
    """
    if score >= 0.7:
        return "正面"
    elif score >= 0.4:
        return "中性"
    else:
        return "负面"


def analyze_dataframe(df: pd.DataFrame, analyzer: SentimentAnalyzer = None) -> pd.DataFrame:
    """
    对DataFrame进行情感分析
    
    Args:
        df: 包含title列的DataFrame
        analyzer: 情感分析器实例（可选）
    
    Returns:
        添加了情感得分列的DataFrame
    """
    df = df.copy()
    
    if analyzer is None:
        analyzer = SentimentAnalyzer()
    
    # 使用title进行情感分析
    texts = df['title'].tolist()
    
    print(f"[Sentiment] 开始分析 {len(texts)} 条文本...")
    scores = analyzer.analyze_batch(texts)
    
    df['sentiment_score'] = scores
    df['sentiment_label'] = df['sentiment_score'].apply(get_sentiment_label)
    
    # 统计
    label_counts = df['sentiment_label'].value_counts()
    print(f"[Sentiment] 情感分布:")
    for label, count in label_counts.items():
        pct = count / len(df) * 100
        print(f"  - {label}: {count} ({pct:.1f}%)")
    
    return df


if __name__ == "__main__":
    # 测试
    analyzer = SentimentAnalyzer()
    
    test_texts = [
        "华为Mate80真的太好用了！强烈推荐",
        "这个手机太贵了，不值得买",
        "华为发布新品",
        "垃圾手机，后悔购买",
        "华为加油，支持国产"
    ]
    
    for text in test_texts:
        processed = analyzer.preprocess_text(text)
        score = analyzer.analyze_single(processed)
        label = get_sentiment_label(score)
        print(f"文本: {text}")
        print(f"得分: {score:.3f}, 标签: {label}\n")
