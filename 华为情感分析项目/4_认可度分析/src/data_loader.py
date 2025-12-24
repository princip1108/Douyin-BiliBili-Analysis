# -*- coding: utf-8 -*-
"""
数据加载模块
功能：加载B站和抖音的视频数据
作者：XXX
日期：2024年12月
"""

import pandas as pd
import os
import glob


def 加载B站数据(数据目录):
    """
    加载B站视频数据
    统一字段名称
    """
    # 查找文件
    文件模式 = os.path.join(数据目录, "bili", "cleaned_search_videos_*.csv")
    文件列表 = glob.glob(文件模式)
    
    if not 文件列表:
        print(f"未找到B站数据文件: {文件模式}")
        return pd.DataFrame()
    
    # 读取并合并
    数据列表 = [pd.read_csv(f) for f in 文件列表]
    df = pd.concat(数据列表, ignore_index=True)
    
    # 去重
    if 'video_id' in df.columns:
        df = df.drop_duplicates(subset=['video_id'])
    
    # 统一字段名
    结果 = pd.DataFrame()
    结果['id'] = df['video_id']
    结果['title'] = df['title']
    结果['desc'] = df['desc'] if 'desc' in df.columns else ''
    结果['likes'] = df['liked_count'].fillna(0)
    结果['favorites'] = df['video_favorite_count'].fillna(0)
    结果['comments'] = df['video_comment'].fillna(0)
    结果['shares'] = df['video_share_count'].fillna(0)
    结果['coins'] = df['video_coin_count'].fillna(0)
    结果['plays'] = df['video_play_count'].fillna(0)
    结果['create_time'] = df['create_time'] if 'create_time' in df.columns else ''
    结果['nickname'] = df['nickname'] if 'nickname' in df.columns else ''
    结果['platform'] = 'bilibili'
    
    print(f"加载B站数据: {len(结果)} 条")
    return 结果


def 加载抖音数据(数据目录):
    """
    加载抖音视频数据
    统一字段名称
    """
    # 查找文件
    文件模式 = os.path.join(数据目录, "dy", "cleaned_search_contents_*.csv")
    文件列表 = glob.glob(文件模式)
    
    if not 文件列表:
        print(f"未找到抖音数据文件: {文件模式}")
        return pd.DataFrame()
    
    # 读取并合并
    数据列表 = [pd.read_csv(f) for f in 文件列表]
    df = pd.concat(数据列表, ignore_index=True)
    
    # 去重
    if 'aweme_id' in df.columns:
        df = df.drop_duplicates(subset=['aweme_id'])
    
    # 统一字段名
    结果 = pd.DataFrame()
    结果['id'] = df['aweme_id']
    结果['title'] = df['title'].fillna(df['desc'] if 'desc' in df.columns else '')
    结果['desc'] = df['desc'] if 'desc' in df.columns else ''
    结果['likes'] = df['liked_count'].fillna(0)
    结果['favorites'] = df['collected_count'].fillna(0)
    结果['comments'] = df['comment_count'].fillna(0)
    结果['shares'] = df['share_count'].fillna(0)
    结果['coins'] = 0  # 抖音没有投币功能
    结果['plays'] = 0  # 抖音爬不到播放量
    结果['create_time'] = df['create_time'] if 'create_time' in df.columns else ''
    结果['nickname'] = df['nickname'] if 'nickname' in df.columns else ''
    结果['platform'] = 'douyin'
    
    print(f"加载抖音数据: {len(结果)} 条")
    return 结果


def 加载全部数据(数据目录):
    """
    加载所有平台数据
    返回：(B站df, 抖音df)
    """
    print("=" * 40)
    print("加载视频数据")
    print("=" * 40)
    
    bili_df = 加载B站数据(数据目录)
    dy_df = 加载抖音数据(数据目录)
    
    print(f"\n总计: B站 {len(bili_df)} 条, 抖音 {len(dy_df)} 条")
    
    return bili_df, dy_df


# ============ 兼容旧接口 ============
def load_bilibili_data(data_dir):
    return 加载B站数据(data_dir)

def load_douyin_data(data_dir):
    return 加载抖音数据(data_dir)

def load_all_data(data_dir):
    return 加载全部数据(data_dir)
