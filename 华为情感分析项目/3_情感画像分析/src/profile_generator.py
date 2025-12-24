"""
情感画像生成模块
生成主题-情感矩阵和平台对比画像
"""
import pandas as pd
import numpy as np


def generate_topic_sentiment_matrix(df: pd.DataFrame, use_weight: bool = True) -> pd.DataFrame:
    """
    生成主题-情感矩阵
    
    Args:
        df: 包含topic和sentiment_score列的DataFrame
        use_weight: 是否使用点赞数加权
    
    Returns:
        主题-情感矩阵DataFrame
    """
    results = []
    
    for topic in sorted(df['topic'].unique()):
        topic_df = df[df['topic'] == topic]
        topic_name = topic_df['topic_name'].iloc[0] if 'topic_name' in topic_df.columns else f"主题{topic+1}"
        
        # 情感分布
        label_counts = topic_df['sentiment_label'].value_counts(normalize=True)
        positive_pct = label_counts.get('正面', 0) * 100
        neutral_pct = label_counts.get('中性', 0) * 100
        negative_pct = label_counts.get('负面', 0) * 100
        
        # 平均情感得分
        if use_weight and 'like_count' in topic_df.columns:
            total_likes = topic_df['like_count'].sum()
            if total_likes > 0:
                avg_sentiment = (topic_df['sentiment_score'] * topic_df['like_count']).sum() / total_likes
            else:
                avg_sentiment = topic_df['sentiment_score'].mean()
        else:
            avg_sentiment = topic_df['sentiment_score'].mean()
        
        results.append({
            'topic_id': topic,
            'topic_name': topic_name,
            'count': len(topic_df),
            'positive_pct': positive_pct,
            'neutral_pct': neutral_pct,
            'negative_pct': negative_pct,
            'avg_sentiment': avg_sentiment,
            'total_likes': topic_df['like_count'].sum() if 'like_count' in topic_df.columns else 0
        })
    
    return pd.DataFrame(results)


def generate_platform_profile(bili_df: pd.DataFrame, dy_df: pd.DataFrame, 
                              use_weight: bool = True) -> pd.DataFrame:
    """
    生成平台对比画像
    
    Args:
        bili_df: B站数据
        dy_df: 抖音数据
        use_weight: 是否使用点赞数加权
    
    Returns:
        平台对比DataFrame
    """
    bili_matrix = generate_topic_sentiment_matrix(bili_df, use_weight)
    dy_matrix = generate_topic_sentiment_matrix(dy_df, use_weight)
    
    # 合并对比
    comparison = []
    
    for topic_id in range(4):
        bili_row = bili_matrix[bili_matrix['topic_id'] == topic_id]
        dy_row = dy_matrix[dy_matrix['topic_id'] == topic_id]
        
        if len(bili_row) == 0 or len(dy_row) == 0:
            continue
        
        bili_row = bili_row.iloc[0]
        dy_row = dy_row.iloc[0]
        
        comparison.append({
            'topic_id': topic_id,
            'topic_name': bili_row['topic_name'],
            'bili_count': bili_row['count'],
            'bili_positive_pct': bili_row['positive_pct'],
            'bili_avg_sentiment': bili_row['avg_sentiment'],
            'dy_count': dy_row['count'],
            'dy_positive_pct': dy_row['positive_pct'],
            'dy_avg_sentiment': dy_row['avg_sentiment'],
            'sentiment_diff': bili_row['avg_sentiment'] - dy_row['avg_sentiment']
        })
    
    return pd.DataFrame(comparison)


def extract_representative_comments(df: pd.DataFrame, topic: int, top_n: int = 3) -> dict:
    """
    提取代表性评论
    
    Args:
        df: 评论数据
        topic: 主题ID
        top_n: 每类提取数量
    
    Returns:
        {类型: [评论列表]}
    """
    topic_df = df[df['topic'] == topic].copy()
    
    if len(topic_df) == 0:
        return {}
    
    result = {
        'most_positive': topic_df.nlargest(top_n, 'sentiment_score')[['content', 'sentiment_score', 'like_count']].to_dict('records'),
        'most_negative': topic_df.nsmallest(top_n, 'sentiment_score')[['content', 'sentiment_score', 'like_count']].to_dict('records'),
        'most_liked': topic_df.nlargest(top_n, 'like_count')[['content', 'sentiment_score', 'like_count']].to_dict('records')
    }
    
    return result


def print_profile_summary(bili_df: pd.DataFrame, dy_df: pd.DataFrame):
    """打印画像摘要"""
    print("\n" + "="*60)
    print("情感画像摘要")
    print("="*60)
    
    # 整体对比
    bili_avg = bili_df['sentiment_score'].mean()
    dy_avg = dy_df['sentiment_score'].mean()
    
    print(f"\n整体情感得分:")
    print(f"  - B站:  {bili_avg:.4f}")
    print(f"  - 抖音: {dy_avg:.4f}")
    print(f"  - 差异: {bili_avg - dy_avg:+.4f}")
    
    # 主题对比
    comparison = generate_platform_profile(bili_df, dy_df)
    
    print(f"\n主题情感对比:")
    for _, row in comparison.iterrows():
        print(f"\n  {row['topic_name']}:")
        print(f"    B站: {row['bili_avg_sentiment']:.3f} (正面{row['bili_positive_pct']:.1f}%)")
        print(f"    抖音: {row['dy_avg_sentiment']:.3f} (正面{row['dy_positive_pct']:.1f}%)")
        
        diff = row['sentiment_diff']
        if diff > 0.05:
            print(f"    → B站情感更正面 (+{diff:.3f})")
        elif diff < -0.05:
            print(f"    → 抖音情感更正面 ({diff:.3f})")
        else:
            print(f"    → 两平台相近")


def save_profile_data(bili_df: pd.DataFrame, dy_df: pd.DataFrame, output_dir: str):
    """保存画像数据"""
    from pathlib import Path
    output_dir = Path(output_dir)
    
    # 保存主题-情感矩阵
    bili_matrix = generate_topic_sentiment_matrix(bili_df)
    dy_matrix = generate_topic_sentiment_matrix(dy_df)
    
    bili_matrix['platform'] = 'bilibili'
    dy_matrix['platform'] = 'douyin'
    
    combined = pd.concat([bili_matrix, dy_matrix], ignore_index=True)
    combined.to_csv(output_dir / 'sentiment_profile.csv', index=False, encoding='utf-8-sig')
    
    # 保存平台对比
    comparison = generate_platform_profile(bili_df, dy_df)
    comparison.to_csv(output_dir / 'platform_comparison.csv', index=False, encoding='utf-8-sig')
    
    print(f"[Profile] 画像数据已保存至: {output_dir}")
