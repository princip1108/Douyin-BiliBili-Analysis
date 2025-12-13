"""
互动得分计算模块
使用Engagement Rate计算互动率，百分位法归一化
"""
import pandas as pd
import numpy as np
from scipy.stats import percentileofscore


def calculate_total_interaction(df: pd.DataFrame) -> pd.Series:
    """计算总互动量"""
    return df['likes'] + df['favorites'] + df['comments'] + df['shares']


def calculate_bilibili_er(df: pd.DataFrame) -> pd.Series:
    """
    计算B站Engagement Rate
    ER = (likes + favorites + comments + shares + coins) / plays × 100%
    """
    total_engagement = (df['likes'] + df['favorites'] + df['comments'] + 
                        df['shares'] + df['coins'])
    
    # 避免除零
    plays = df['plays'].replace(0, np.nan)
    er = (total_engagement / plays) * 100
    
    # 播放量为0的视频，ER设为0
    er = er.fillna(0)
    
    # 限制ER上限为100%（某些极端情况可能超过）
    er = er.clip(upper=100)
    
    return er


def calculate_douyin_er(df: pd.DataFrame) -> pd.Series:
    """
    计算抖音Engagement Rate（优化方案）
    ER = total_interaction / max(total_interaction) × 100%
    使用平台内最大互动量作为基准
    """
    total_interaction = calculate_total_interaction(df)
    max_interaction = total_interaction.max()
    
    if max_interaction == 0:
        return pd.Series([0] * len(df), index=df.index)
    
    er = (total_interaction / max_interaction) * 100
    return er


def percentile_normalize(series: pd.Series) -> pd.Series:
    """
    百分位归一化，输出0~1
    
    Args:
        series: 待归一化的Series
    
    Returns:
        归一化后的Series (0~1)
    """
    if series.nunique() == 1:
        # 所有值相同时，返回0.5
        return pd.Series([0.5] * len(series), index=series.index)
    
    return series.apply(lambda x: percentileofscore(series.dropna(), x) / 100)


def calculate_interaction_score(df: pd.DataFrame, platform: str) -> pd.DataFrame:
    """
    计算互动得分
    
    Args:
        df: 数据DataFrame
        platform: 平台名称 ('bilibili' 或 'douyin')
    
    Returns:
        添加了互动得分列的DataFrame
    """
    df = df.copy()
    
    # 计算总互动量
    df['total_interaction'] = calculate_total_interaction(df)
    
    # 计算ER
    if platform == 'bilibili':
        df['er'] = calculate_bilibili_er(df)
    else:
        df['er'] = calculate_douyin_er(df)
    
    # 百分位归一化
    df['er_normalized'] = percentile_normalize(df['er'])
    
    print(f"[Interaction] {platform} ER统计:")
    print(f"  - 均值: {df['er'].mean():.2f}%")
    print(f"  - 中位数: {df['er'].median():.2f}%")
    print(f"  - 最大值: {df['er'].max():.2f}%")
    
    return df


if __name__ == "__main__":
    # 测试
    from data_loader import load_all_data
    
    data_dir = "../../DataCleaning/cleaned_data"
    bili_df, dy_df = load_all_data(data_dir)
    
    bili_df = calculate_interaction_score(bili_df, 'bilibili')
    dy_df = calculate_interaction_score(dy_df, 'douyin')
    
    print("\nB站互动得分分布:")
    print(bili_df['er_normalized'].describe())
    
    print("\n抖音互动得分分布:")
    print(dy_df['er_normalized'].describe())
