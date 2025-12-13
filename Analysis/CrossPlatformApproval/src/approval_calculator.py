"""
认可度计算模块
综合互动得分和情感得分计算认可度
"""
import pandas as pd
import numpy as np


# 默认权重
INTERACTION_WEIGHT = 0.6  # α
SENTIMENT_WEIGHT = 0.4    # β


def calculate_single_approval(er_normalized: float, sentiment_score: float,
                              alpha: float = INTERACTION_WEIGHT,
                              beta: float = SENTIMENT_WEIGHT) -> float:
    """
    计算单条内容认可度
    
    公式: 认可度 = α × 互动得分(归一化) + β × 情感得分
    """
    return alpha * er_normalized + beta * sentiment_score


def calculate_platform_approval(df: pd.DataFrame) -> float:
    """
    计算平台整体认可度（加权平均）
    
    公式: 平台认可度 = Σ(认可度_i × 互动量_i) / Σ(互动量_i)
    """
    total_interaction = df['total_interaction'].sum()
    
    if total_interaction == 0:
        return df['approval_score'].mean()
    
    weighted_sum = (df['approval_score'] * df['total_interaction']).sum()
    weighted_approval = weighted_sum / total_interaction
    
    return weighted_approval


def calculate_approval_scores(df: pd.DataFrame, platform: str,
                              alpha: float = INTERACTION_WEIGHT,
                              beta: float = SENTIMENT_WEIGHT) -> tuple:
    """
    计算所有内容的认可度
    
    Returns:
        (DataFrame, platform_approval_score)
    """
    df = df.copy()
    
    # 计算单条认可度
    df['approval_score'] = df.apply(
        lambda row: calculate_single_approval(
            row['er_normalized'], 
            row['sentiment_score'],
            alpha, 
            beta
        ),
        axis=1
    )
    
    # 计算平台整体认可度
    platform_approval = calculate_platform_approval(df)
    
    print(f"\n[Approval] {platform} 认可度统计:")
    print(f"  - 平台加权认可度: {platform_approval:.4f}")
    print(f"  - 单条认可度均值: {df['approval_score'].mean():.4f}")
    print(f"  - 单条认可度中位数: {df['approval_score'].median():.4f}")
    print(f"  - 单条认可度标准差: {df['approval_score'].std():.4f}")
    
    return df, platform_approval


def compare_platforms(bili_approval: float, dy_approval: float) -> dict:
    """对比两平台认可度"""
    diff = bili_approval - dy_approval
    diff_pct = (diff / dy_approval) * 100 if dy_approval != 0 else 0
    
    if diff > 0.05:
        conclusion = "B站用户认可度显著更高"
    elif diff < -0.05:
        conclusion = "抖音用户认可度显著更高"
    else:
        conclusion = "两平台用户认可度相近"
    
    result = {
        'bilibili_approval': bili_approval,
        'douyin_approval': dy_approval,
        'difference': diff,
        'difference_pct': diff_pct,
        'conclusion': conclusion
    }
    
    print("\n" + "="*50)
    print("跨平台认可度对比结果")
    print("="*50)
    print(f"B站平台认可度:   {bili_approval:.4f}")
    print(f"抖音平台认可度:  {dy_approval:.4f}")
    print(f"差异:            {diff:+.4f} ({diff_pct:+.2f}%)")
    print(f"结论:            {conclusion}")
    print("="*50)
    
    return result
