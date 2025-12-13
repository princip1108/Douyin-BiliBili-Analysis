"""
数据加载模块
加载B站和抖音评论数据
"""
import pandas as pd
from pathlib import Path
import glob


def load_bilibili_comments(data_dir: str) -> pd.DataFrame:
    """
    加载B站评论数据
    
    Args:
        data_dir: 数据目录路径
    
    Returns:
        统一字段命名后的DataFrame
    """
    pattern = str(Path(data_dir) / "bili" / "cleaned_search_comments_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No bilibili comment files found: {pattern}")
    
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    
    # 去重
    df = df.drop_duplicates(subset=['comment_id'], keep='first')
    
    # 统一字段命名
    df_unified = pd.DataFrame({
        'comment_id': df['comment_id'],
        'content': df['content'],
        'like_count': df['like_count'].fillna(0).astype(int),
        'video_id': df['video_id'],
        'user_id': df['user_id'],
        'nickname': df['nickname'],
        'create_time': df['create_time'],
        'platform': 'bilibili'
    })
    
    return df_unified


def load_douyin_comments(data_dir: str) -> pd.DataFrame:
    """
    加载抖音评论数据
    
    Args:
        data_dir: 数据目录路径
    
    Returns:
        统一字段命名后的DataFrame
    """
    pattern = str(Path(data_dir) / "dy" / "cleaned_search_comments_*.csv")
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No douyin comment files found: {pattern}")
    
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    
    # 去重
    df = df.drop_duplicates(subset=['comment_id'], keep='first')
    
    # 统一字段命名
    df_unified = pd.DataFrame({
        'comment_id': df['comment_id'],
        'content': df['content'],
        'like_count': df['like_count'].fillna(0).astype(int),
        'video_id': df['aweme_id'],
        'user_id': df['user_id'],
        'nickname': df['nickname'],
        'create_time': df['create_time'],
        'platform': 'douyin'
    })
    
    return df_unified


def load_all_comments(data_dir: str) -> tuple:
    """
    加载所有平台评论数据
    
    Args:
        data_dir: 数据目录路径
    
    Returns:
        (bilibili_df, douyin_df) 元组
    """
    bili_df = load_bilibili_comments(data_dir)
    dy_df = load_douyin_comments(data_dir)
    
    print(f"[Data Loader] B站评论: {len(bili_df)} 条")
    print(f"[Data Loader] 抖音评论: {len(dy_df)} 条")
    
    return bili_df, dy_df


if __name__ == "__main__":
    data_dir = "../../DataCleaning/cleaned_data"
    bili_df, dy_df = load_all_comments(data_dir)
    print(bili_df.head())
    print(dy_df.head())
