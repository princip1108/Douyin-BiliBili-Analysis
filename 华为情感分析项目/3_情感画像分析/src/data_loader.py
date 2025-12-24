# -*- coding: utf-8 -*-
"""
数据加载模块
功能：加载B站和抖音的评论数据
作者：XXX
日期：2024年12月
"""

import pandas as pd
import os
import glob


def 加载B站评论(数据目录):
    """
    加载B站评论数据
    返回统一格式的DataFrame
    """
    # 查找文件
    文件模式 = os.path.join(数据目录, "bili", "cleaned_search_comments_*.csv")
    文件列表 = glob.glob(文件模式)
    
    if not 文件列表:
        print(f"未找到B站评论文件: {文件模式}")
        return pd.DataFrame()
    
    # 读取所有文件
    数据列表 = []
    for 文件 in 文件列表:
        df = pd.read_csv(文件)
        数据列表.append(df)
    
    # 合并
    df = pd.concat(数据列表, ignore_index=True)
    
    # 去重
    if 'comment_id' in df.columns:
        df = df.drop_duplicates(subset=['comment_id'])
    
    # 统一字段格式
    结果 = pd.DataFrame()
    结果['comment_id'] = df['comment_id']
    结果['content'] = df['content']
    结果['like_count'] = df['like_count'].fillna(0).astype(int)
    结果['video_id'] = df['video_id']
    结果['user_id'] = df['user_id'] if 'user_id' in df.columns else ''
    结果['nickname'] = df['nickname'] if 'nickname' in df.columns else ''
    结果['create_time'] = df['create_time'] if 'create_time' in df.columns else ''
    结果['platform'] = 'bilibili'
    
    print(f"加载B站评论: {len(结果)} 条")
    return 结果


def 加载抖音评论(数据目录):
    """
    加载抖音评论数据
    返回统一格式的DataFrame
    """
    # 查找文件
    文件模式 = os.path.join(数据目录, "dy", "cleaned_search_comments_*.csv")
    文件列表 = glob.glob(文件模式)
    
    if not 文件列表:
        print(f"未找到抖音评论文件: {文件模式}")
        return pd.DataFrame()
    
    # 读取所有文件
    数据列表 = []
    for 文件 in 文件列表:
        df = pd.read_csv(文件)
        数据列表.append(df)
    
    # 合并
    df = pd.concat(数据列表, ignore_index=True)
    
    # 去重
    if 'comment_id' in df.columns:
        df = df.drop_duplicates(subset=['comment_id'])
    
    # 统一字段格式
    结果 = pd.DataFrame()
    结果['comment_id'] = df['comment_id']
    结果['content'] = df['content']
    结果['like_count'] = df['like_count'].fillna(0).astype(int)
    结果['video_id'] = df['aweme_id'] if 'aweme_id' in df.columns else ''
    结果['user_id'] = df['user_id'] if 'user_id' in df.columns else ''
    结果['nickname'] = df['nickname'] if 'nickname' in df.columns else ''
    结果['create_time'] = df['create_time'] if 'create_time' in df.columns else ''
    结果['platform'] = 'douyin'
    
    print(f"加载抖音评论: {len(结果)} 条")
    return 结果


def 加载全部评论(数据目录):
    """
    加载所有平台的评论数据
    返回 (B站df, 抖音df) 元组
    """
    print("=" * 40)
    print("加载评论数据")
    print("=" * 40)
    
    bili_df = 加载B站评论(数据目录)
    dy_df = 加载抖音评论(数据目录)
    
    print(f"\n总计: B站 {len(bili_df)} 条, 抖音 {len(dy_df)} 条")
    
    return bili_df, dy_df


# ============ 兼容旧接口 ============
def load_bilibili_comments(data_dir):
    return 加载B站评论(data_dir)

def load_douyin_comments(data_dir):
    return 加载抖音评论(data_dir)

def load_all_comments(data_dir):
    return 加载全部评论(data_dir)


# ============ 测试 ============
if __name__ == "__main__":
    数据目录 = "../../2_数据清洗/cleaned_data"
    bili_df, dy_df = 加载全部评论(数据目录)
    
    if len(bili_df) > 0:
        print("\nB站数据示例:")
        print(bili_df.head())
    
    if len(dy_df) > 0:
        print("\n抖音数据示例:")
        print(dy_df.head())
