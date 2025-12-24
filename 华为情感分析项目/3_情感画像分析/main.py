"""
评论情感画像分析 - 主程序
分析华为相关内容在B站和抖音的用户评论情感画像
"""
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
from data_loader import load_all_comments
from text_processor import process_comments, get_all_tokens
from lda_model import TopicModeler, save_topic_keywords
from sentiment_analyzer import SentimentAnalyzer, analyze_comments
from profile_generator import print_profile_summary, save_profile_data
from wordcloud_generator import generate_all_wordclouds
from visualizer import generate_all_plots


def main():
    # 配置路径
    DATA_DIR = Path(__file__).parent.parent.parent / "DataCleaning" / "cleaned_data"
    OUTPUT_DIR = Path(__file__).parent / "output"
    
    print("="*60)
    print("评论情感画像分析 - 华为内容")
    print("="*60)
    
    # Step 1: 加载数据
    print("\n[Step 1] 加载评论数据...")
    bili_df, dy_df = load_all_comments(str(DATA_DIR))
    
    # Step 2: 文本预处理
    print("\n[Step 2] 文本预处理...")
    bili_df = process_comments(bili_df, min_words=3)
    dy_df = process_comments(dy_df, min_words=3)
    
    # Step 3: LDA主题建模（合并两平台数据训练统一模型）
    print("\n[Step 3] LDA主题建模...")
    all_tokens = get_all_tokens(bili_df) + get_all_tokens(dy_df)
    
    modeler = TopicModeler(num_topics=4)
    modeler.build_corpus(all_tokens)
    modeler.train(passes=15)
    modeler.print_topics()
    
    # 为每条评论分配主题
    bili_df = modeler.assign_topics(bili_df)
    dy_df = modeler.assign_topics(dy_df)
    
    # Step 4: 情感分析
    print("\n[Step 4] 情感分析...")
    analyzer = SentimentAnalyzer()
    bili_df = analyze_comments(bili_df, analyzer)
    dy_df = analyze_comments(dy_df, analyzer)
    
    # Step 5: 生成画像
    print("\n[Step 5] 生成情感画像...")
    print_profile_summary(bili_df, dy_df)
    
    # Step 6: 保存结果
    print("\n[Step 6] 保存结果...")
    data_output = OUTPUT_DIR / "data"
    data_output.mkdir(parents=True, exist_ok=True)
    
    # 保存详细数据
    output_cols = ['comment_id', 'content', 'like_count', 'topic', 'topic_name',
                   'sentiment_score', 'sentiment_label', 'platform']
    
    bili_df[output_cols].to_csv(data_output / "bili_comment_analysis.csv",
                                 index=False, encoding='utf-8-sig')
    dy_df[output_cols].to_csv(data_output / "dy_comment_analysis.csv",
                               index=False, encoding='utf-8-sig')
    
    # 保存主题关键词
    save_topic_keywords(modeler, data_output / "topic_keywords.csv")
    
    # 保存画像数据
    save_profile_data(bili_df, dy_df, data_output)
    
    print(f"  - 保存: {data_output / 'bili_comment_analysis.csv'}")
    print(f"  - 保存: {data_output / 'dy_comment_analysis.csv'}")
    
    # Step 7: 生成可视化
    print("\n[Step 7] 生成可视化...")
    figures_output = OUTPUT_DIR / "figures"
    
    generate_all_plots(bili_df, dy_df, str(figures_output))
    generate_all_wordclouds(bili_df, dy_df, str(figures_output))
    
    print("\n" + "="*60)
    print("分析完成!")
    print("="*60)
    
    return bili_df, dy_df, modeler


if __name__ == "__main__":
    main()
