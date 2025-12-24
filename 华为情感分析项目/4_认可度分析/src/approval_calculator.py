# -*- coding: utf-8 -*-
"""
认可度计算模块
功能：综合互动率和情感分数计算认可度
作者：XXX
日期：2024年12月
"""

import pandas as pd

# ============ 权重设置 ============
互动权重 = 0.6  # alpha
情感权重 = 0.4  # beta


def 计算单条认可度(互动分数, 情感分数):
    """
    计算单条内容的认可度
    公式：认可度 = α × 互动分数 + β × 情感分数
    """
    return 互动权重 * 互动分数 + 情感权重 * 情感分数


def 计算平台认可度(df):
    """
    计算平台整体认可度（加权平均）
    权重为总互动量
    """
    总互动 = df['total_interaction'].sum()
    
    if 总互动 == 0:
        return df['approval_score'].mean()
    
    加权和 = (df['approval_score'] * df['total_interaction']).sum()
    加权认可度 = 加权和 / 总互动
    
    return 加权认可度


def 计算认可度(df, 平台名称):
    """
    计算所有内容的认可度
    返回：(处理后的df, 平台认可度)
    """
    df = df.copy()
    
    # 计算每条内容的认可度
    df['approval_score'] = df.apply(
        lambda row: 计算单条认可度(row['er_normalized'], row['sentiment_score']),
        axis=1
    )
    
    # 计算平台整体认可度
    平台认可度 = 计算平台认可度(df)
    
    # 打印统计信息
    print(f"\n{平台名称} 认可度统计:")
    print(f"  平台加权认可度: {平台认可度:.4f}")
    print(f"  认可度均值: {df['approval_score'].mean():.4f}")
    print(f"  认可度中位数: {df['approval_score'].median():.4f}")
    print(f"  认可度标准差: {df['approval_score'].std():.4f}")
    
    return df, 平台认可度


def 对比平台(bili认可度, dy认可度):
    """对比两个平台的认可度"""
    差值 = bili认可度 - dy认可度
    差值百分比 = (差值 / dy认可度) * 100 if dy认可度 != 0 else 0
    
    # 得出结论
    if 差值 > 0.05:
        结论 = "B站用户认可度显著更高"
    elif 差值 < -0.05:
        结论 = "抖音用户认可度显著更高"
    else:
        结论 = "两平台用户认可度相近"
    
    # 打印结果
    print("\n" + "=" * 50)
    print("跨平台认可度对比结果")
    print("=" * 50)
    print(f"B站平台认可度:  {bili认可度:.4f}")
    print(f"抖音平台认可度: {dy认可度:.4f}")
    print(f"差异:           {差值:+.4f} ({差值百分比:+.2f}%)")
    print(f"结论:           {结论}")
    print("=" * 50)
    
    结果 = {
        'bilibili_approval': bili认可度,
        'douyin_approval': dy认可度,
        'difference': 差值,
        'difference_pct': 差值百分比,
        'conclusion': 结论
    }
    
    return 结果


# ============ 兼容旧接口 ============
def calculate_single_approval(er_normalized, sentiment_score, alpha=0.6, beta=0.4):
    return alpha * er_normalized + beta * sentiment_score

def calculate_approval_scores(df, platform, alpha=0.6, beta=0.4):
    return 计算认可度(df, platform)

def compare_platforms(bili_approval, dy_approval):
    return 对比平台(bili_approval, dy_approval)
