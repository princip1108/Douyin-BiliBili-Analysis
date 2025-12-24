"""
数据清洗程序
用于处理B站和抖音的CSV数据
包括：删除重复值、填充缺失值、转换互动数据为数值类型
"""

import pandas as pd
import numpy as np
import os
import re
from pathlib import Path


def convert_interaction_value(value):
    """
    将互动数据转换为数值
    处理格式如：'1.2万' -> 12000, '1000' -> 1000, '' -> 0
    """
    if pd.isna(value) or value == '' or value is None:
        return 0
    
    # 如果已经是数字类型，直接返回
    if isinstance(value, (int, float)):
        return float(value)
    
    # 转换为字符串处理
    value_str = str(value).strip()
    
    # 如果为空字符串，返回0
    if value_str == '' or value_str.lower() == 'nan':
        return 0
    
    # 尝试直接转换为数字
    try:
        return float(value_str)
    except ValueError:
        pass
    
    # 处理中文单位：万、千等
    # 匹配模式：数字.数字万、数字万、数字.数字千、数字千等
    patterns = [
        (r'(\d+\.?\d*)\s*万', 10000),  # 万
        (r'(\d+\.?\d*)\s*千', 1000),   # 千
        (r'(\d+\.?\d*)\s*百', 100),    # 百
        (r'(\d+\.?\d*)\s*亿', 100000000),  # 亿
    ]
    
    for pattern, multiplier in patterns:
        match = re.search(pattern, value_str, re.IGNORECASE)
        if match:
            num = float(match.group(1))
            return num * multiplier
    
    # 如果无法转换，返回0
    return 0


def clean_bilibili_videos(df):
   
    
    # 删除重复值
    if 'video_id' in df.columns:
        df = df.drop_duplicates(subset=['video_id'], keep='first').copy()
    else:
        print("未找到video_id列，跳过去重")
        df = df.copy()
    print(f"删除重复后行数: {len(df)}")
    
    # 互动数据
    interaction_cols = [
        'liked_count', 'disliked_count', 'video_play_count',
        'video_favorite_count', 'video_share_count', 'video_coin_count',
        'video_danmaku', 'video_comment'
    ]
    
    # 转换互动数据为数值
    for col in interaction_cols:
        if col in df.columns:
            df[col] = df[col].apply(convert_interaction_value)
            df[col] = df[col].fillna(0)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 其他缺失
    df = df.fillna('')
    
    return df


def clean_bilibili_comments(df):
    """清洗B站评论数据"""
    print(f"原始数据行数: {len(df)}")
    
    # 检查并清理列名（去除BOM等）
    df.columns = df.columns.str.strip()
    df.columns = df.columns.str.replace('\ufeff', '')  # 去除BOM
    
    # 删除重复值（基于comment_id）
    if 'comment_id' in df.columns:
        df = df.drop_duplicates(subset=['comment_id'], keep='first').copy()
    else:
        print("警告: 未找到comment_id列，跳过去重")
        df = df.copy()
    print(f"删除重复后行数: {len(df)}")
    
    # 需要转换的互动数据列
    interaction_cols = ['sub_comment_count', 'like_count']
    
    # 转换互动数据为数值
    for col in interaction_cols:
        if col in df.columns:
            df[col] = df[col].apply(convert_interaction_value)
            df[col] = df[col].fillna(0)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 填充其他缺失值
    df = df.fillna('')
    
    return df


def clean_bilibili_creators(df):
    """清洗B站创作者数据"""
    print(f"原始数据行数: {len(df)}")
    
    # 删除重复值（基于user_id）
    if 'user_id' in df.columns:
        df = df.drop_duplicates(subset=['user_id'], keep='first').copy()
    else:
        print("警告: 未找到user_id列，跳过去重")
        df = df.copy()
    print(f"删除重复后行数: {len(df)}")
    
    # 需要转换的互动数据列
    interaction_cols = ['total_fans', 'total_liked']
    
    # 转换互动数据为数值
    for col in interaction_cols:
        if col in df.columns:
            df[col] = df[col].apply(convert_interaction_value)
            df[col] = df[col].fillna(0)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 填充其他缺失值
    df = df.fillna('')
    
    return df


def clean_douyin_contents(df):
    """清洗抖音内容数据"""
    print(f"原始数据行数: {len(df)}")
    
    # 删除重复值（基于aweme_id）
    if 'aweme_id' in df.columns:
        df = df.drop_duplicates(subset=['aweme_id'], keep='first').copy()
    else:
        print("警告: 未找到aweme_id列，跳过去重")
        df = df.copy()
    print(f"删除重复后行数: {len(df)}")
    
    # 需要转换的互动数据列
    interaction_cols = ['liked_count', 'collected_count', 'comment_count', 'share_count']
    
    # 转换互动数据为数值
    for col in interaction_cols:
        if col in df.columns:
            df[col] = df[col].apply(convert_interaction_value)
            df[col] = df[col].fillna(0)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 填充其他缺失值
    df = df.fillna('')
    
    return df


def clean_douyin_comments(df):
    """清洗抖音评论数据"""
    print(f"原始数据行数: {len(df)}")
    
    # 删除重复值（基于comment_id）
    if 'comment_id' in df.columns:
        df = df.drop_duplicates(subset=['comment_id'], keep='first').copy()
    else:
        print("警告: 未找到comment_id列，跳过去重")
        df = df.copy()
    print(f"删除重复后行数: {len(df)}")
    
    # 需要转换的互动数据列
    interaction_cols = ['sub_comment_count', 'like_count']
    
    # 转换互动数据为数值
    for col in interaction_cols:
        if col in df.columns:
            df[col] = df[col].apply(convert_interaction_value)
            df[col] = df[col].fillna(0)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 填充其他缺失值
    df = df.fillna('')
    
    return df


def read_csv_with_encoding(file_path):
    """尝试多种编码方式读取CSV文件"""
    import io
    
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb18030', 'latin-1', 'cp936']
    
    # 首先尝试直接读取（适用于正常编码的文件）
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            # 检查是否成功读取
            if len(df) > 0 or len(df.columns) > 0:
                # 验证数据质量：检查列名是否正常（不包含乱码字符）
                if len(df.columns) > 0:
                    # 检查是否有明显的乱码（包含替换字符）
                    has_replacement = any('\ufffd' in str(col) for col in df.columns)
                    if not has_replacement:
                        return df
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            continue
    
    # 如果直接读取失败，使用错误处理模式（适用于有编码错误的文件）
    # 优先使用utf-8，因为大多数文件应该是utf-8编码
    for encoding in ['utf-8', 'utf-8-sig'] + [e for e in encodings if e not in ['utf-8', 'utf-8-sig']]:
        try:
            # 使用io.open处理编码错误，读取完整文件
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()  # 读取完整文件内容
            # 使用StringIO传递给pandas
            df = pd.read_csv(io.StringIO(content))
            if len(df) > 0 or len(df.columns) > 0:
                # 清理列名（去除BOM等）
                df.columns = df.columns.str.strip()
                df.columns = df.columns.str.replace('\ufeff', '')
                # 验证数据质量：检查是否有预期的列
                if 'comment_id' in df.columns or 'video_id' in df.columns or 'aweme_id' in df.columns or len(df.columns) > 5:
                    if encoding not in ['utf-8', 'utf-8-sig']:
                        print(f"警告: 使用错误替换模式读取文件 {file_path} (编码: {encoding})")
                    return df
        except Exception as e:
            continue
    
    # 最后尝试：使用utf-8和错误处理（不验证列名）
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        df = pd.read_csv(io.StringIO(content))
        # 清理列名
        df.columns = df.columns.str.strip()
        df.columns = df.columns.str.replace('\ufeff', '')
        print(f"警告: 使用UTF-8错误替换模式读取文件 {file_path}")
        return df
    except Exception as e:
        print(f"无法读取文件 {file_path}: {e}")
        raise


def process_all_files():
    """处理所有CSV文件"""
    # 定义数据目录
    base_dir = Path('../data')
    
    # 创建分类输出目录
    output_base_dir = Path('./cleaned_data')
    bili_output_dir = output_base_dir / 'bili'
    dy_output_dir = output_base_dir / 'dy'
    
    bili_output_dir.mkdir(parents=True, exist_ok=True)
    dy_output_dir.mkdir(parents=True, exist_ok=True)
    
    # B站数据处理
    bili_dir = base_dir / 'bili' / 'csv'
    if bili_dir.exists():
        print("=" * 50)
        print("处理B站数据")
        print("=" * 50)
        
        # 处理视频数据
        for file in bili_dir.glob('search_videos_*.csv'):
            print(f"\n处理文件: {file.name}")
            df = read_csv_with_encoding(file)
            df_cleaned = clean_bilibili_videos(df)
            output_path = bili_output_dir / f'cleaned_{file.name}'
            # 使用utf-8-sig确保Excel可以正确打开，但先确保数据正确
            df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"已保存到: {output_path}")
        
        # 处理评论数据
        for file in bili_dir.glob('search_comments_*.csv'):
            print(f"\n处理文件: {file.name}")
            df = read_csv_with_encoding(file)
            df_cleaned = clean_bilibili_comments(df)
            output_path = bili_output_dir / f'cleaned_{file.name}'
            df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"已保存到: {output_path}")
        
        # 处理创作者数据
        for file in bili_dir.glob('search_creators_*.csv'):
            print(f"\n处理文件: {file.name}")
            df = read_csv_with_encoding(file)
            df_cleaned = clean_bilibili_creators(df)
            output_path = bili_output_dir / f'cleaned_{file.name}'
            df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"已保存到: {output_path}")
    
    # 抖音数据处理
    dy_dir = base_dir / 'dy' / 'csv'
    if dy_dir.exists():
        print("\n" + "=" * 50)
        print("处理抖音数据")
        print("=" * 50)
        
        # 处理内容数据
        for file in dy_dir.glob('search_contents_*.csv'):
            print(f"\n处理文件: {file.name}")
            df = read_csv_with_encoding(file)
            df_cleaned = clean_douyin_contents(df)
            output_path = dy_output_dir / f'cleaned_{file.name}'
            df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"已保存到: {output_path}")
        
        # 处理评论数据
        for file in dy_dir.glob('search_comments_*.csv'):
            print(f"\n处理文件: {file.name}")
            df = read_csv_with_encoding(file)
            df_cleaned = clean_douyin_comments(df)
            output_path = dy_output_dir / f'cleaned_{file.name}'
            df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"已保存到: {output_path}")
    
    print("\n" + "=" * 50)
    print("所有文件处理完成！")
    print("=" * 50)


if __name__ == '__main__':
    process_all_files()

