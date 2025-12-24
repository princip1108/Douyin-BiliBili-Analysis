"""
跨平台认可度分析 - 主程序
分析华为相关内容在B站和抖音的用户认可度
"""
import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
from data_loader import load_all_data
from interaction_score import calculate_interaction_score
from sentiment_analysis import SentimentAnalyzer, analyze_dataframe
from approval_calculator import calculate_approval_scores, compare_platforms
from visualizer import generate_all_plots


def main():
    # 配置路径
    DATA_DIR = Path(__file__).parent.parent.parent / "DataCleaning" / "cleaned_data"
    OUTPUT_DIR = Path(__file__).parent / "output"
    
    print("="*60)
    print("跨平台认可度分析 - 华为内容")
    print("="*60)
    
    # Step 1: 加载数据
    print("\n[Step 1] 加载数据...")
    bili_df, dy_df = load_all_data(str(DATA_DIR))
    
    # Step 2: 计算互动率
    print("\n[Step 2] 计算Engagement Rate...")
    bili_df = calculate_interaction_score(bili_df, 'bilibili')
    dy_df = calculate_interaction_score(dy_df, 'douyin')
    
    # Step 3: 情感分析
    print("\n[Step 3] Transformers情感分析...")
    analyzer = SentimentAnalyzer()
    bili_df = analyze_dataframe(bili_df, analyzer)
    dy_df = analyze_dataframe(dy_df, analyzer)
    
    # Step 4: 计算认可度
    print("\n[Step 4] 计算认可度...")
    bili_df, bili_approval = calculate_approval_scores(bili_df, 'bilibili')
    dy_df, dy_approval = calculate_approval_scores(dy_df, 'douyin')
    
    # Step 5: 平台对比
    print("\n[Step 5] 平台对比...")
    comparison = compare_platforms(bili_approval, dy_approval)
    
    # Step 6: 保存结果
    print("\n[Step 6] 保存结果...")
    data_output = OUTPUT_DIR / "data"
    data_output.mkdir(parents=True, exist_ok=True)
    
    # 保存详细数据
    bili_output_cols = ['id', 'title', 'er', 'er_normalized', 'sentiment_score', 
                        'sentiment_label', 'approval_score', 'total_interaction']
    dy_output_cols = bili_output_cols.copy()
    
    bili_df[bili_output_cols].to_csv(data_output / "bili_approval_scores.csv", 
                                      index=False, encoding='utf-8-sig')
    dy_df[dy_output_cols].to_csv(data_output / "dy_approval_scores.csv", 
                                  index=False, encoding='utf-8-sig')
    
    # 保存对比结果
    comparison_df = pd.DataFrame([comparison])
    comparison_df.to_csv(data_output / "platform_comparison.csv", 
                         index=False, encoding='utf-8-sig')
    
    print(f"  - 保存: {data_output / 'bili_approval_scores.csv'}")
    print(f"  - 保存: {data_output / 'dy_approval_scores.csv'}")
    print(f"  - 保存: {data_output / 'platform_comparison.csv'}")
    
    # Step 7: 生成可视化
    print("\n[Step 7] 生成可视化...")
    figures_output = OUTPUT_DIR / "figures"
    generate_all_plots(bili_df, dy_df, bili_approval, dy_approval, str(figures_output))
    
    print("\n" + "="*60)
    print("分析完成!")
    print("="*60)
    
    return bili_df, dy_df, comparison


if __name__ == "__main__":
    main()
