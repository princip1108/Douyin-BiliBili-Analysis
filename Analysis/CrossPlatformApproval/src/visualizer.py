"""
可视化模块
生成认可度分析相关图表
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def plot_approval_distribution(bili_df: pd.DataFrame, dy_df: pd.DataFrame, 
                               output_path: str):
    """绘制认可度分布对比图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # 直方图对比
    ax1 = axes[0]
    ax1.hist(bili_df['approval_score'], bins=30, alpha=0.6, label='B站', color='#00A1D6')
    ax1.hist(dy_df['approval_score'], bins=30, alpha=0.6, label='抖音', color='#FE2C55')
    ax1.set_xlabel('认可度得分')
    ax1.set_ylabel('频数')
    ax1.set_title('认可度分布对比')
    ax1.legend()
    
    # 箱线图对比
    ax2 = axes[1]
    data = pd.DataFrame({
        '认可度': pd.concat([bili_df['approval_score'], dy_df['approval_score']]),
        '平台': ['B站'] * len(bili_df) + ['抖音'] * len(dy_df)
    })
    sns.boxplot(x='平台', y='认可度', data=data, ax=ax2, palette=['#00A1D6', '#FE2C55'])
    ax2.set_title('认可度箱线图对比')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] 保存: {output_path}")


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


def plot_top10_comparison(bili_df: pd.DataFrame, dy_df: pd.DataFrame,
                          output_path: str):
    """绘制Top10内容认可度对比"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # B站Top10
    bili_top = bili_df.nlargest(10, 'approval_score')[['title', 'approval_score']]
    bili_top['title'] = bili_top['title'].str[:20] + '...'
    ax1 = axes[0]
    ax1.barh(range(len(bili_top)), bili_top['approval_score'], color='#00A1D6')
    ax1.set_yticks(range(len(bili_top)))
    ax1.set_yticklabels(bili_top['title'])
    ax1.set_xlabel('认可度')
    ax1.set_title('B站 Top10 认可度内容')
    ax1.invert_yaxis()
    
    # 抖音Top10
    dy_top = dy_df.nlargest(10, 'approval_score')[['title', 'approval_score']]
    dy_top['title'] = dy_top['title'].str[:20] + '...'
    ax2 = axes[1]
    ax2.barh(range(len(dy_top)), dy_top['approval_score'], color='#FE2C55')
    ax2.set_yticks(range(len(dy_top)))
    ax2.set_yticklabels(dy_top['title'])
    ax2.set_xlabel('认可度')
    ax2.set_title('抖音 Top10 认可度内容')
    ax2.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] 保存: {output_path}")


def plot_platform_summary(bili_approval: float, dy_approval: float,
                          output_path: str):
    """绘制平台认可度对比汇总图"""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    platforms = ['B站', '抖音']
    approvals = [bili_approval, dy_approval]
    colors = ['#00A1D6', '#FE2C55']
    
    bars = ax.bar(platforms, approvals, color=colors, width=0.5)
    
    # 添加数值标签
    for bar, val in zip(bars, approvals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{val:.4f}', ha='center', va='bottom', fontsize=12)
    
    ax.set_ylabel('加权平均认可度')
    ax.set_title('跨平台华为内容认可度对比')
    ax.set_ylim(0, max(approvals) * 1.2)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Visualizer] 保存: {output_path}")


def generate_all_plots(bili_df: pd.DataFrame, dy_df: pd.DataFrame,
                       bili_approval: float, dy_approval: float,
                       output_dir: str):
    """生成所有可视化图表"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plot_approval_distribution(bili_df, dy_df, output_dir / 'approval_distribution.png')
    plot_sentiment_distribution(bili_df, dy_df, output_dir / 'sentiment_distribution.png')
    plot_top10_comparison(bili_df, dy_df, output_dir / 'top10_comparison.png')
    plot_platform_summary(bili_approval, dy_approval, output_dir / 'platform_summary.png')
    
    print(f"\n[Visualizer] 所有图表已保存至: {output_dir}")
