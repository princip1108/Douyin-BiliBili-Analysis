# -*- coding: utf-8 -*-
"""
互动率计算模块
功能：计算视频的互动率（Engagement Rate）
作者：XXX
日期：2024年12月
"""

import pandas as pd
import numpy as np
from scipy.stats import percentileofscore


def 计算总互动量(df):
    """计算总互动量 = 点赞 + 收藏 + 评论 + 分享"""
    return df['likes'] + df['favorites'] + df['comments'] + df['shares']


def 计算B站互动率(df):
    """
    计算B站的互动率
    公式：ER = (点赞 + 收藏 + 评论 + 分享 + 投币) / 播放量 × 100%
    """
    总互动 = df['likes'] + df['favorites'] + df['comments'] + df['shares'] + df['coins']
    
    # 避免除以0
    播放量 = df['plays'].replace(0, np.nan)
    互动率 = (总互动 / 播放量) * 100
    
    # 播放量为0的设为0
    互动率 = 互动率.fillna(0)
    
    # 限制最大值为100%
    互动率 = 互动率.clip(upper=100)
    
    return 互动率


def 计算抖音互动率(df):
    """
    计算抖音的互动率
    由于抖音没有播放量，使用相对互动量
    公式：ER = 总互动量 / 最大互动量 × 100%
    """
    总互动 = 计算总互动量(df)
    最大互动 = 总互动.max()
    
    if 最大互动 == 0:
        return pd.Series([0] * len(df), index=df.index)
    
    互动率 = (总互动 / 最大互动) * 100
    return 互动率


def 百分位归一化(数据):
    """
    使用百分位法归一化到0-1
    """
    if 数据.nunique() == 1:
        return pd.Series([0.5] * len(数据), index=数据.index)
    
    return 数据.apply(lambda x: percentileofscore(数据.dropna(), x) / 100)


def 计算互动分数(df, 平台):
    """
    计算互动分数
    参数：
        df: 数据
        平台: 'bilibili' 或 'douyin'
    返回：添加了互动分数列的df
    """
    df = df.copy()
    
    # 计算总互动量
    df['total_interaction'] = 计算总互动量(df)
    
    # 计算互动率
    if 平台 == 'bilibili':
        df['er'] = 计算B站互动率(df)
    else:
        df['er'] = 计算抖音互动率(df)
    
    # 归一化
    df['er_normalized'] = 百分位归一化(df['er'])
    
    # 打印统计
    print(f"\n{平台} 互动率统计:")
    print(f"  均值: {df['er'].mean():.2f}%")
    print(f"  中位数: {df['er'].median():.2f}%")
    print(f"  最大值: {df['er'].max():.2f}%")
    
    return df


# ============ 兼容旧接口 ============
def calculate_interaction_score(df, platform):
    return 计算互动分数(df, platform)
