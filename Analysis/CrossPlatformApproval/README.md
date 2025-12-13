# 跨平台认可度分析方案

## 项目概述

本项目旨在分析用户对华为相关内容在 **B站** 和 **抖音** 两个平台的认可度差异。通过 Engagement Rate 互动率计算和 Transformers 情感分析，计算综合认可度指标，实现跨平台对比。

---

## 一、数据源

### 1.1 数据位置

| 平台 | 数据路径 |
|-----|---------|
| B站 | `../../DataCleaning/cleaned_data/bili/cleaned_search_videos_*.csv` |
| 抖音 | `../../DataCleaning/cleaned_data/dy/cleaned_search_contents_*.csv` |

### 1.2 可用字段对比

| 指标类型 | B站字段 | 抖音字段 | 跨平台可比 |
|---------|--------|---------|-----------|
| 点赞 | `liked_count` | `liked_count` | ✅ |
| 收藏 | `video_favorite_count` | `collected_count` | ✅ |
| 评论 | `video_comment` | `comment_count` | ✅ |
| 转发/分享 | `video_share_count` | `share_count` | ✅ |
| 播放量 | `video_play_count` | ❌ 无 | ❌ |
| 投币 | `video_coin_count` | ❌ 无 | ❌ |
| 弹幕 | `video_danmaku` | ❌ 无 | ❌ |
| 标题 | `title` | `title` / `desc` | ✅ |

---

## 二、Engagement Rate 互动率计算

### 2.1 B站 Engagement Rate

B站有播放量数据，使用标准 ER 公式：

```
ER_bilibili = (点赞 + 收藏 + 评论 + 分享 + 投币) / 播放量 × 100%
```

### 2.2 抖音 Engagement Rate（优化方案）

抖音缺少播放量，采用 **互动密度比** 替代：

```
ER_douyin = (点赞 + 收藏 + 评论 + 分享) / (点赞 + 收藏 + 评论 + 分享).max() × 100%
```

**优化说明**：
- 使用平台内最大互动量作为基准，计算相对互动密度
- 避免因缺少播放量导致的不可比问题
- 保持与B站ER相同的百分比量级

### 2.3 归一化处理（百分位法）

采用 **百分位排名** 进行平台内归一化：

```python
from scipy.stats import percentileofscore

def percentile_normalize(series):
    """百分位归一化，输出 0~1"""
    return series.apply(lambda x: percentileofscore(series, x) / 100)
```

**优点**：
- 消除极端值影响
- 保留数据分布特征
- 跨平台可比性强

---

## 三、情感分析方案（Transformers）

### 3.1 文本预处理

```python
import re

def preprocess_text(text):
    if pd.isna(text):
        return ""
    # 1. 去除 hashtag 符号但保留文字：#华为 → 华为
    text = re.sub(r'#(\S+)', r'\1', text)
    # 2. 去除 @用户
    text = re.sub(r'@\S+', '', text)
    # 3. 去除 URL
    text = re.sub(r'http\S+', '', text)
    # 4. 去除表情符号 [xxx]
    text = re.sub(r'\[.*?\]', '', text)
    # 5. 去除多余空白
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
```

### 3.2 Transformers 情感分析

使用中文预训练情感分析模型：

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# 模型选择：uer/roberta-base-finetuned-chinanews-chinese
model_name = "uer/roberta-base-finetuned-chinanews-chinese"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

def analyze_sentiment(text):
    """返回情感得分 0~1，越高越正面"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.softmax(outputs.logits, dim=1)
    # 假设 label 0=负面, 1=正面
    positive_score = probs[0][1].item()
    return positive_score
```

### 3.3 情感分类标准

| 分数范围 | 情感标签 | 说明 |
|---------|---------|------|
| [0.7, 1.0] | 正面 | 明确正向情感 |
| [0.4, 0.7) | 中性 | 无明显倾向 |
| [0, 0.4) | 负面 | 明确负向情感 |

---

## 四、综合认可度计算

### 4.1 单条内容认可度

```
认可度 = α × 互动得分(归一化) + β × 情感得分

其中：α = 0.6, β = 0.4
```

**参数说明**：
- `α = 0.6`：互动数据权重，反映用户实际行为
- `β = 0.4`：情感得分权重，反映内容倾向性

### 4.2 平台整体认可度（加权平均）

采用 **互动量加权平均**，热门内容权重更大：

```python
def calculate_platform_approval(df):
    """计算平台整体认可度（加权平均）"""
    # 原始互动量作为权重
    total_interaction = df['total_interaction'].sum()
    if total_interaction == 0:
        return df['approval_score'].mean()
    
    weighted_approval = (df['approval_score'] * df['total_interaction']).sum() / total_interaction
    return weighted_approval
```

**公式**：
```
平台认可度 = Σ(认可度_i × 互动量_i) / Σ(互动量_i)
```

---

## 五、实施步骤

```
Step 1: 数据加载与清洗
    ├── 加载 B站 videos CSV
    ├── 加载 抖音 contents CSV
    ├── 统一字段命名（likes, favorites, comments, shares）
    └── 处理缺失值（fillna(0)）

Step 2: Engagement Rate 计算
    ├── B站：ER = (likes + favorites + comments + shares + coins) / plays
    ├── 抖音：ER = total_interaction / max(total_interaction)
    ├── 百分位归一化（0~1）
    └── 输出 er_normalized

Step 3: Transformers 情感分析
    ├── 文本预处理（去除#、@、URL等）
    ├── 加载 uer/roberta-base-finetuned-chinanews-chinese
    ├── 批量推理情感得分
    └── 输出 sentiment_score (0~1)

Step 4: 认可度计算
    ├── 单条认可度 = 0.6 × ER归一化 + 0.4 × 情感得分
    ├── 平台加权认可度 = Σ(认可度 × 互动量) / Σ(互动量)
    └── 输出对比结果

Step 5: 可视化与报告
    ├── 两平台认可度分布对比
    ├── 情感倾向分布对比
    └── 生成分析报告
```

---

## 六、预期输出

### 6.1 数据输出

| 文件名 | 说明 |
|-------|------|
| `bili_approval_scores.csv` | B站内容认可度明细 |
| `dy_approval_scores.csv` | 抖音内容认可度明细 |
| `platform_comparison.csv` | 平台对比汇总 |

### 6.2 可视化输出

| 图表 | 说明 |
|-----|------|
| `approval_distribution.png` | 认可度分布对比 |
| `sentiment_distribution.png` | 情感倾向分布对比 |
| `top10_comparison.png` | 热门内容对比 |

### 6.3 分析报告

- 两平台整体认可度对比
- 情感倾向差异分析
- 关键发现与结论

---

## 七、依赖库

```txt
pandas>=1.5.0
numpy>=1.21.0
scipy>=1.9.0
matplotlib>=3.5.0
seaborn>=0.12.0
transformers>=4.30.0
torch>=2.0.0
tqdm>=4.65.0
```

---

## 八、目录结构

```
CrossPlatformApproval/
├── README.md                 # 本文档
├── requirements.txt          # 依赖库
├── src/
│   ├── data_loader.py       # 数据加载模块
│   ├── interaction_score.py # 互动得分计算
│   ├── sentiment_analysis.py# 情感分析模块
│   ├── approval_calculator.py# 认可度计算
│   └── visualization.py     # 可视化模块
├── output/
│   ├── data/                # 输出数据
│   └── figures/             # 输出图表
└── main.py                  # 主程序入口
```

---

## 九、使用方法

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行分析
python main.py

# 3. 查看结果
# 输出文件在 output/ 目录下
```

---

## 十、注意事项

1. **数据量级差异**：抖音单条内容互动量通常远高于B站，通过百分位归一化消除差异
2. **ER计算差异**：B站使用播放量作为分母，抖音使用最大互动量作为基准
3. **Transformers模型**：首次运行会自动下载模型（约500MB），需要网络连接
4. **GPU加速**：如有CUDA支持的GPU，情感分析速度会显著提升
5. **时间范围**：建议对比相同时间段的数据，避免时效性偏差
