"""
可视化模块
生成情感分析相关图表
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def plot_sentiment_distribution(bili_df: pd.DataFrame, dy_df: pd.DataFrame, 
                                 output_path: str):
    """绘制情感分布对比图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # 情感得分分布
    ax1 = axes[0]
    ax1.hist(bili_df['sentiment_score'], bins=30, alpha=0.6, label='B站', color='#00A1D6')
    ax1.hist(dy_df['sentiment_score'], bins=30, alpha=0.6, label='抖音', color='#FE2C55')
    ax1.set_xlabel('情感得分')
    ax1.set_ylabel('频数')
    ax1.set_title('情感得分分布对比')
    ax1.legend()
    
    # 情感标签分布
    ax2 = axes[1]
    bili_counts = bili_df['sentiment_label'].value_counts()
    dy_counts = dy_df['sentiment_label'].value_counts()
    
    labels = ['正面', '中性', '负面']
    x = np.arange(len(labels))
    width = 0.35
    
    bili_vals = [bili_counts.get(l, 0) / len(bili_df) * 100 for l in labels]
    dy_vals = [dy_counts.get(l, 0) / len(dy_df) * 100 for l in labels]
    
    ax2.bar(x - width/2, bili_vals, width, label='B站', color='#00A1D6')
    ax2.bar(x + width/2, dy_vals, width, label='抖音', color='#FE2C55')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel('占比 (%)')
    ax2.set_title('情感标签分布对比')
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] 保存: {output_path}")


def plot_topic_distribution(bili_df: pd.DataFrame, dy_df: pd.DataFrame,
                            output_path: str):
    """绘制主题分布对比图"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bili_counts = bili_df['topic_name'].value_counts()
    dy_counts = dy_df['topic_name'].value_counts()
    
    topics = sorted(bili_df['topic_name'].unique())
    x = np.arange(len(topics))
    width = 0.35
    
    bili_vals = [bili_counts.get(t, 0) / len(bili_df) * 100 for t in topics]
    dy_vals = [dy_counts.get(t, 0) / len(dy_df) * 100 for t in topics]
    
    ax.bar(x - width/2, bili_vals, width, label='B站', color='#00A1D6')
    ax.bar(x + width/2, dy_vals, width, label='抖音', color='#FE2C55')
    ax.set_xticks(x)
    ax.set_xticklabels(topics)
    ax.set_ylabel('占比 (%)')
    ax.set_title('主题分布对比')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] 保存: {output_path}")


def plot_topic_sentiment_heatmap(bili_df: pd.DataFrame, dy_df: pd.DataFrame,
                                  output_path: str):
    """绘制主题-情感热力图"""
    from profile_generator import generate_topic_sentiment_matrix
    
    bili_matrix = generate_topic_sentiment_matrix(bili_df)
    dy_matrix = generate_topic_sentiment_matrix(dy_df)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # B站热力图
    bili_data = bili_matrix[['positive_pct', 'neutral_pct', 'negative_pct']].values
    sns.heatmap(bili_data, ax=axes[0], annot=True, fmt='.1f', cmap='RdYlGn',
                xticklabels=['正面%', '中性%', '负面%'],
                yticklabels=bili_matrix['topic_name'].tolist())
    axes[0].set_title('B站 主题-情感分布')
    
    # 抖音热力图
    dy_data = dy_matrix[['positive_pct', 'neutral_pct', 'negative_pct']].values
    sns.heatmap(dy_data, ax=axes[1], annot=True, fmt='.1f', cmap='RdYlGn',
                xticklabels=['正面%', '中性%', '负面%'],
                yticklabels=dy_matrix['topic_name'].tolist())
    axes[1].set_title('抖音 主题-情感分布')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] 保存: {output_path}")


def plot_platform_comparison(bili_df: pd.DataFrame, dy_df: pd.DataFrame,
                              output_path: str):
    """绘制平台整体对比图"""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # 整体情感对比
    ax1 = axes[0]
    platforms = ['B站', '抖音']
    sentiments = [bili_df['sentiment_score'].mean(), dy_df['sentiment_score'].mean()]
    colors = ['#00A1D6', '#FE2C55']
    bars = ax1.bar(platforms, sentiments, color=colors, width=0.5)
    for bar, val in zip(bars, sentiments):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                 f'{val:.3f}', ha='center', va='bottom')
    ax1.set_ylabel('平均情感得分')
    ax1.set_title('整体情感对比')
    ax1.set_ylim(0, 1)
    
    # 正面率对比
    ax2 = axes[1]
    bili_positive = (bili_df['sentiment_label'] == '正面').mean() * 100
    dy_positive = (dy_df['sentiment_label'] == '正面').mean() * 100
    rates = [bili_positive, dy_positive]
    bars = ax2.bar(platforms, rates, color=colors, width=0.5)
    for bar, val in zip(bars, rates):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f'{val:.1f}%', ha='center', va='bottom')
    ax2.set_ylabel('正面评论占比 (%)')
    ax2.set_title('正面率对比')
    ax2.set_ylim(0, 100)
    
    # 评论数量对比
    ax3 = axes[2]
    counts = [len(bili_df), len(dy_df)]
    bars = ax3.bar(platforms, counts, color=colors, width=0.5)
    for bar, val in zip(bars, counts):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                 f'{val}', ha='center', va='bottom')
    ax3.set_ylabel('评论数量')
    ax3.set_title('数据量对比')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] 保存: {output_path}")


def generate_all_plots(bili_df: pd.DataFrame, dy_df: pd.DataFrame, output_dir: str):
    """生成所有可视化图表"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n[Visualizer] 生成可视化图表...")
    
    plot_sentiment_distribution(bili_df, dy_df, output_dir / 'sentiment_distribution.png')
    plot_topic_distribution(bili_df, dy_df, output_dir / 'topic_distribution.png')
    plot_topic_sentiment_heatmap(bili_df, dy_df, output_dir / 'topic_sentiment_heatmap.png')
    plot_platform_comparison(bili_df, dy_df, output_dir / 'platform_comparison.png')
    
    print(f"\n[Visualizer] 所有图表已保存至: {output_dir}")
