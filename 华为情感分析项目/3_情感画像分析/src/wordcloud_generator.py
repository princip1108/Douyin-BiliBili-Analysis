"""
词云可视化模块
生成平台词云和主题词云
"""
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 中文字体路径（Windows）
FONT_PATH = 'C:/Windows/Fonts/simhei.ttf'


def get_word_frequency(df: pd.DataFrame) -> dict:
    """
    统计词频
    
    Args:
        df: 包含tokens列的DataFrame
    
    Returns:
        词频字典
    """
    all_words = []
    for tokens in df['tokens']:
        if isinstance(tokens, list):
            all_words.extend(tokens)
    
    return dict(Counter(all_words))


def generate_wordcloud(word_freq: dict, output_path: str, 
                       colormap: str = 'viridis', title: str = None):
    """
    生成词云图
    
    Args:
        word_freq: 词频字典
        output_path: 输出路径
        colormap: 配色方案
        title: 图表标题
    """
    if not word_freq:
        print(f"[WordCloud] 警告: 词频为空，跳过生成")
        return
    
    wc = WordCloud(
        font_path=FONT_PATH,
        width=1200,
        height=800,
        background_color='white',
        max_words=200,
        colormap=colormap,
        max_font_size=150,
        random_state=42
    )
    
    wc.generate_from_frequencies(word_freq)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold', pad=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[WordCloud] 保存: {output_path}")


def generate_platform_wordclouds(bili_df: pd.DataFrame, dy_df: pd.DataFrame, 
                                  output_dir: str):
    """
    生成两平台词云对比图
    
    Args:
        bili_df: B站数据
        dy_df: 抖音数据
        output_dir: 输出目录
    """
    output_dir = Path(output_dir)
    
    # B站词云
    bili_freq = get_word_frequency(bili_df)
    generate_wordcloud(bili_freq, output_dir / 'bili_wordcloud.png', 
                       colormap='Blues', title='B站评论词云')
    
    # 抖音词云
    dy_freq = get_word_frequency(dy_df)
    generate_wordcloud(dy_freq, output_dir / 'dy_wordcloud.png',
                       colormap='Reds', title='抖音评论词云')
    
    # 对比图（两图并排）
    fig, axes = plt.subplots(1, 2, figsize=(20, 8))
    
    wc_bili = WordCloud(font_path=FONT_PATH, width=1000, height=600,
                        background_color='white', max_words=150,
                        colormap='Blues', random_state=42)
    wc_bili.generate_from_frequencies(bili_freq)
    
    wc_dy = WordCloud(font_path=FONT_PATH, width=1000, height=600,
                      background_color='white', max_words=150,
                      colormap='Reds', random_state=42)
    wc_dy.generate_from_frequencies(dy_freq)
    
    axes[0].imshow(wc_bili, interpolation='bilinear')
    axes[0].set_title('B站评论词云', fontsize=14, fontweight='bold')
    axes[0].axis('off')
    
    axes[1].imshow(wc_dy, interpolation='bilinear')
    axes[1].set_title('抖音评论词云', fontsize=14, fontweight='bold')
    axes[1].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'platform_wordcloud_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[WordCloud] 保存: {output_dir / 'platform_wordcloud_comparison.png'}")


def generate_topic_wordclouds(df: pd.DataFrame, output_path: str, 
                               num_topics: int = 4):
    """
    生成主题词云（2×2子图）
    
    Args:
        df: 包含tokens和topic列的DataFrame
        output_path: 输出路径
        num_topics: 主题数
    """
    colormaps = ['Blues', 'Greens', 'Oranges', 'Purples']
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    for topic_id in range(num_topics):
        topic_df = df[df['topic'] == topic_id]
        topic_name = topic_df['topic_name'].iloc[0] if len(topic_df) > 0 and 'topic_name' in topic_df.columns else f"主题{topic_id+1}"
        
        word_freq = get_word_frequency(topic_df)
        
        if word_freq:
            wc = WordCloud(
                font_path=FONT_PATH,
                width=800,
                height=600,
                background_color='white',
                max_words=100,
                colormap=colormaps[topic_id % len(colormaps)],
                random_state=42
            )
            wc.generate_from_frequencies(word_freq)
            axes[topic_id].imshow(wc, interpolation='bilinear')
        
        axes[topic_id].set_title(f'{topic_name} (n={len(topic_df)})', 
                                  fontsize=12, fontweight='bold')
        axes[topic_id].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"[WordCloud] 保存: {output_path}")


def generate_sentiment_wordclouds(df: pd.DataFrame, output_dir: str):
    """
    生成情感词云（正面/负面）
    
    Args:
        df: 包含tokens和sentiment_label列的DataFrame
        output_dir: 输出目录
    """
    output_dir = Path(output_dir)
    
    # 正面评论词云
    positive_df = df[df['sentiment_label'] == '正面']
    positive_freq = get_word_frequency(positive_df)
    if positive_freq:
        generate_wordcloud(positive_freq, output_dir / 'positive_wordcloud.png',
                           colormap='Greens', title='正面评论词云')
    
    # 负面评论词云
    negative_df = df[df['sentiment_label'] == '负面']
    negative_freq = get_word_frequency(negative_df)
    if negative_freq:
        generate_wordcloud(negative_freq, output_dir / 'negative_wordcloud.png',
                           colormap='Reds', title='负面评论词云')


def generate_all_wordclouds(bili_df: pd.DataFrame, dy_df: pd.DataFrame, 
                            output_dir: str):
    """
    生成所有词云图
    
    Args:
        bili_df: B站数据
        dy_df: 抖音数据
        output_dir: 输出目录
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n[WordCloud] 生成词云图...")
    
    # 平台词云
    generate_platform_wordclouds(bili_df, dy_df, output_dir)
    
    # 主题词云
    generate_topic_wordclouds(bili_df, output_dir / 'bili_topic_wordclouds.png')
    generate_topic_wordclouds(dy_df, output_dir / 'dy_topic_wordclouds.png')
    
    print(f"\n[WordCloud] 所有词云已保存至: {output_dir}")
