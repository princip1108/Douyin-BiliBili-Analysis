# -*- coding: utf-8 -*-
"""
情感分析模块
使用预训练模型对评论进行情感分类
作者：XXX
日期：2024年12月
"""

import pandas as pd
from tqdm import tqdm
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


# ============ 全局变量 ============
模型名称 = "uer/roberta-base-finetuned-jd-binary-chinese"
分词器 = None
模型 = None
设备 = None


def 加载模型():
    """加载预训练的情感分析模型"""
    global 分词器, 模型, 设备
    
    print("正在加载情感分析模型...")
    print(f"模型: {模型名称}")
    
    # 加载分词器和模型
    分词器 = AutoTokenizer.from_pretrained(模型名称)
    模型 = AutoModelForSequenceClassification.from_pretrained(模型名称)
    
    # 选择设备（GPU或CPU）
    if torch.cuda.is_available():
        设备 = torch.device("cuda")
        print("使用GPU加速")
    else:
        设备 = torch.device("cpu")
        print("使用CPU")
    
    模型.to(设备)
    模型.eval()
    print("模型加载完成！")


def 分析单条文本(文本):
    """
    分析单条文本的情感
    返回0-1之间的分数，越高越正面
    """
    global 分词器, 模型, 设备
    
    # 如果模型没加载，先加载
    if 模型 is None:
        加载模型()
    
    # 空文本返回中性
    if not 文本 or len(str(文本)) < 2:
        return 0.5
    
    try:
        # 分词
        inputs = 分词器(
            str(文本),
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )
        
        # 移到设备上
        inputs = {k: v.to(设备) for k, v in inputs.items()}
        
        # 预测
        with torch.no_grad():
            outputs = 模型(**inputs)
        
        # 计算概率
        probs = torch.softmax(outputs.logits, dim=1)
        正面概率 = probs[0][1].item()
        
        return 正面概率
        
    except Exception as e:
        print(f"分析出错: {e}")
        return 0.5


def 批量分析(文本列表, 批大小=16):
    """
    批量分析多条文本的情感
    返回分数列表
    """
    global 分词器, 模型, 设备
    
    if 模型 is None:
        加载模型()
    
    结果 = []
    
    # 分批处理
    for i in tqdm(range(0, len(文本列表), 批大小), desc="情感分析中"):
        批次 = 文本列表[i:i+批大小]
        
        # 过滤有效文本
        有效索引 = []
        有效文本 = []
        for j, 文本 in enumerate(批次):
            if 文本 and len(str(文本)) >= 2:
                有效索引.append(j)
                有效文本.append(str(文本))
        
        # 如果没有有效文本
        if not 有效文本:
            结果.extend([0.5] * len(批次))
            continue
        
        try:
            # 分词
            inputs = 分词器(
                有效文本,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            inputs = {k: v.to(设备) for k, v in inputs.items()}
            
            # 预测
            with torch.no_grad():
                outputs = 模型(**inputs)
            
            probs = torch.softmax(outputs.logits, dim=1)
            批次分数 = probs[:, 1].cpu().numpy().tolist()
            
            # 填充结果
            批次结果 = [0.5] * len(批次)
            for idx, 分数 in zip(有效索引, 批次分数):
                批次结果[idx] = 分数
            
            结果.extend(批次结果)
            
        except Exception as e:
            print(f"批处理出错: {e}")
            结果.extend([0.5] * len(批次))
    
    return 结果


def 获取情感标签(分数):
    """根据分数返回情感标签"""
    if 分数 >= 0.7:
        return "正面"
    elif 分数 >= 0.4:
        return "中性"
    else:
        return "负面"


def 分析评论数据(df):
    """
    对评论DataFrame进行情感分析
    添加sentiment_score和sentiment_label列
    """
    df = df.copy()
    
    # 获取评论内容
    if 'cleaned_content' in df.columns:
        文本列表 = df['cleaned_content'].tolist()
    else:
        文本列表 = df['content'].tolist()
    
    print(f"开始分析 {len(文本列表)} 条评论...")
    
    # 批量分析
    分数列表 = 批量分析(文本列表)
    
    # 添加结果列
    df['sentiment_score'] = 分数列表
    df['sentiment_label'] = df['sentiment_score'].apply(获取情感标签)
    
    # 统计结果
    print("\n情感分布统计:")
    统计 = df['sentiment_label'].value_counts()
    for 标签 in ['正面', '中性', '负面']:
        数量 = 统计.get(标签, 0)
        比例 = 数量 / len(df) * 100
        print(f"  {标签}: {数量} 条 ({比例:.1f}%)")
    
    return df


# ============ 测试代码 ============
if __name__ == "__main__":
    # 测试
    测试文本 = [
        "华为手机真的很好用！",
        "价格太贵了，不值得",
        "还行吧，一般般"
    ]
    
    for 文本 in 测试文本:
        分数 = 分析单条文本(文本)
        标签 = 获取情感标签(分数)
        print(f"文本: {文本}")
        print(f"分数: {分数:.3f}, 标签: {标签}\n")
