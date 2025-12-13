"""
数据加载模块
加载B站和抖音的清洗后数据，统一字段命名
"""
import pandas as pd
from pathlib import Path
import glob


def load_bilibili_data(data_dir: str) -> pd.DataFrame:
    """
    加载B站视频数据
    
    Args:
        data_dir: 数据目录路径
    
    Returns:
        统一字段命名后的DataFrame
    """
    pattern = str(Path(data_dir) / "bili" / "cleaned_search_videos_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No bilibili data files found: {pattern}")
    
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    
    # 去重
    df = df.drop_duplicates(subset=['video_id'], keep='first')
    
    # 统一字段命名
    df_unified = pd.DataFrame({
        'id': df['video_id'],
        'title': df['title'],
        'desc': df['desc'],
        'likes': df['liked_count'].fillna(0),
        'favorites': df['video_favorite_count'].fillna(0),
        'comments': df['video_comment'].fillna(0),
        'shares': df['video_share_count'].fillna(0),
        'coins': df['video_coin_count'].fillna(0),
        'plays': df['video_play_count'].fillna(0),
        'danmaku': df['video_danmaku'].fillna(0),
        'create_time': df['create_time'],
        'nickname': df['nickname'],
        'platform': 'bilibili'
    })
    
    return df_unified


def load_douyin_data(data_dir: str) -> pd.DataFrame:
    """
    加载抖音内容数据
    
    Args:
        data_dir: 数据目录路径
    
    Returns:
        统一字段命名后的DataFrame
    """
    pattern = str(Path(data_dir) / "dy" / "cleaned_search_contents_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No douyin data files found: {pattern}")
    
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    
    # 去重
    df = df.drop_duplicates(subset=['aweme_id'], keep='first')
    
    # 统一字段命名（抖音title和desc常相同，优先使用title）
    df_unified = pd.DataFrame({
        'id': df['aweme_id'],
        'title': df['title'].fillna(df['desc']),
        'desc': df['desc'],
        'likes': df['liked_count'].fillna(0),
        'favorites': df['collected_count'].fillna(0),
        'comments': df['comment_count'].fillna(0),
        'shares': df['share_count'].fillna(0),
        'coins': 0,  # 抖音无投币
        'plays': 0,  # 抖音无播放量
        'danmaku': 0,  # 抖音无弹幕
        'create_time': df['create_time'],
        'nickname': df['nickname'],
        'platform': 'douyin'
    })
    
    return df_unified


def load_all_data(data_dir: str) -> tuple:
    """
    加载所有平台数据
    
    Args:
        data_dir: 数据目录路径
    
    Returns:
        (bilibili_df, douyin_df) 元组
    """
    bili_df = load_bilibili_data(data_dir)
    dy_df = load_douyin_data(data_dir)
    
    print(f"[Data Loader] B站数据: {len(bili_df)} 条")
    print(f"[Data Loader] 抖音数据: {len(dy_df)} 条")
    
    return bili_df, dy_df


if __name__ == "__main__":
    # 测试
    data_dir = "../../DataCleaning/cleaned_data"
    bili_df, dy_df = load_all_data(data_dir)
    print(bili_df.head())
    print(dy_df.head())
