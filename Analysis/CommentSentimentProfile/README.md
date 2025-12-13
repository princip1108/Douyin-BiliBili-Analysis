# 评论情感画像分析方案

## 一、项目概述

### 1.1 分析目标

通过 LDA 主题建模对 B站/抖音华为相关评论进行主题分组，结合 Transformers 情感分析，生成用户情感画像和词云可视化，对比两平台用户的关注点和情感差异。

### 1.2 数据源

| 平台 | 文件路径 | 数量 |
|-----|---------|------|
| B站 | `../DataCleaning/cleaned_data/bili/cleaned_search_comments_*.csv` | ~3000条 |
| 抖音 | `../DataCleaning/cleaned_data/dy/cleaned_search_comments_*.csv` | ~3000条 |

**关键字段**：
- `content`：评论内容（用于分析）
- `like_count`：点赞数（用于加权）
- `video_id` / `aweme_id`：关联视频ID

---

## 二、技术流程

```
原始评论 → 文本预处理 → LDA主题建模 → 情感分析 → 画像生成 → 词云可视化
    ↓           ↓            ↓            ↓           ↓           ↓
  6000条    分词+清洗     4个主题     0~1得分    主题×情感    平台词云
```

---

## 三、文本预处理

### 3.1 分词方案

使用 **jieba** 进行中文分词：

```python
import jieba

def tokenize(text):
    # 添加华为相关词汇到词典
    jieba.add_word("华为")
    jieba.add_word("麒麟")
    jieba.add_word("鸿蒙")
    jieba.add_word("Mate60")
    jieba.add_word("Mate80")
    return list(jieba.cut(text))
```

### 3.2 文本清洗

```python
import re

def clean_text(text):
    if pd.isna(text):
        return ""
    # 1. 去除表情符号 [xxx]
    text = re.sub(r'\[.*?\]', '', text)
    # 2. 去除 @用户
    text = re.sub(r'@\S+', '', text)
    # 3. 去除 URL
    text = re.sub(r'http\S+', '', text)
    # 4. 去除特殊符号，保留中英文和数字
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
    # 5. 去除多余空白
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
```

### 3.3 停用词过滤

- 使用中文停用词表（哈工大停用词 + 自定义）
- 过滤单字词（除特定词汇外）
- 过滤纯数字

### 3.4 短评论过滤

- 过滤分词后词数 < 3 的评论
- 这类评论信息量不足，影响 LDA 效果

---

## 四、LDA 主题建模

### 4.1 模型选择

使用 **gensim.LdaModel**：

```python
from gensim import corpora
from gensim.models import LdaModel

# 构建词典和语料库
dictionary = corpora.Dictionary(tokenized_texts)
dictionary.filter_extremes(no_below=5, no_above=0.5)  # 过滤极端词频
corpus = [dictionary.doc2bow(text) for text in tokenized_texts]

# 训练 LDA 模型
lda_model = LdaModel(
    corpus=corpus,
    id2word=dictionary,
    num_topics=4,        # 固定4个主题
    passes=15,           # 迭代次数
    alpha='auto',        # 文档-主题分布先验
    eta='auto',          # 主题-词分布先验
    random_state=42
)
```

### 4.2 主题数

**固定使用 4 个主题**，预期覆盖：
- 产品体验类
- 价格讨论类
- 品牌情感类
- 技术讨论类

### 4.3 主题命名（人工/半自动）

根据各主题 Top10 关键词进行命名，例如：
- **主题1**：产品体验（手机、系统、流畅、好用...）
- **主题2**：价格讨论（价格、贵、便宜、性价比...）
- **主题3**：品牌情感（华为、支持、国产、加油...）
- **主题4**：技术讨论（芯片、麒麟、5G、卫星...）

---

## 五、情感分析

### 5.1 模型

复用跨平台认可度分析的 Transformers 模型：

```python
model_name = "uer/roberta-base-finetuned-chinanews-chinese"
```

### 5.2 情感分类标准

| 分数范围 | 情感标签 | 说明 |
|---------|---------|------|
| [0.7, 1.0] | 正面 | 明确支持、赞扬 |
| [0.4, 0.7) | 中性 | 客观描述、无明显倾向 |
| [0, 0.4) | 负面 | 批评、不满、抱怨 |

---

## 六、情感画像生成

### 6.1 主题-情感矩阵

```
            正面    中性    负面    平均情感得分
主题1(产品)  45%    35%    20%      0.62
主题2(价格)  20%    30%    50%      0.38
主题3(品牌)  70%    20%    10%      0.78
主题4(技术)  55%    35%    10%      0.68
```

### 6.2 平台对比画像

```python
def generate_profile(df, platform):
    profile = df.groupby('topic').agg({
        'sentiment_score': ['mean', 'std', 'count'],
        'sentiment_label': lambda x: x.value_counts(normalize=True).to_dict(),
        'like_count': 'sum'
    })
    return profile
```

### 6.3 代表性评论提取

每个主题提取：
- 情感得分最高的3条评论
- 情感得分最低的3条评论
- 点赞数最高的3条评论

---

## 七、词云可视化

### 7.1 整体词云

按平台生成整体词云，展示高频词分布。

### 7.2 主题词云

按主题分别生成词云，使用不同配色区分。

### 7.3 情感词云

- **正面词云**：仅包含正面评论的词汇
- **负面词云**：仅包含负面评论的词汇

### 7.4 词云配置

```python
from wordcloud import WordCloud

def generate_wordcloud(word_freq, output_path, color='blue'):
    wc = WordCloud(
        font_path='simhei.ttf',      # 中文字体
        width=1200,
        height=800,
        background_color='white',
        max_words=200,
        colormap=color               # 配色方案
    )
    wc.generate_from_frequencies(word_freq)
    wc.to_file(output_path)
```

---

## 八、输出结果

### 8.1 数据文件

| 文件名 | 说明 |
|-------|------|
| `bili_comment_analysis.csv` | B站评论分析结果（含主题、情感） |
| `dy_comment_analysis.csv` | 抖音评论分析结果 |
| `topic_keywords.csv` | 各主题 Top20 关键词 |
| `sentiment_profile.csv` | 主题×情感×平台 汇总表 |

### 8.2 可视化文件

| 文件名 | 说明 |
|-------|------|
| `bili_wordcloud.png` | B站整体词云 |
| `dy_wordcloud.png` | 抖音整体词云 |
| `topic_wordclouds.png` | 各主题词云（2×2子图） |
| `sentiment_comparison.png` | 平台情感分布对比图 |
| `topic_sentiment_heatmap.png` | 主题-情感热力图 |

---

## 九、依赖库

```txt
pandas>=1.5.0
numpy>=1.21.0
jieba>=0.42.0
gensim>=4.3.0
wordcloud>=1.9.0
matplotlib>=3.5.0
seaborn>=0.12.0
transformers>=4.30.0
torch>=2.0.0
tqdm>=4.65.0
```

---

## 十、实施步骤

```
Step 1: 数据加载
    ├── 合并 B站评论 CSV（2个文件）
    ├── 加载 抖音评论 CSV
    └── 统一字段命名

Step 2: 文本预处理
    ├── 清洗文本（去除表情、@、URL）
    ├── jieba 分词
    ├── 停用词过滤
    └── 过滤短评论

Step 3: LDA 主题建模
    ├── 构建词典和语料库
    ├── 选择最优主题数（一致性评估）
    ├── 训练 LDA 模型
    └── 提取主题关键词

Step 4: 情感分析
    ├── 加载 Transformers 模型
    ├── 批量分析评论情感
    └── 情感分类（正面/中性/负面）

Step 5: 画像生成
    ├── 计算主题-情感矩阵
    ├── 生成平台对比数据
    └── 提取代表性评论

Step 6: 词云生成
    ├── 平台整体词云
    ├── 主题词云
    └── 情感词云（可选）

Step 7: 输出与报告
    ├── 保存数据文件
    ├── 保存可视化图表
    └── 生成分析摘要
```

---

## 十一、确认配置

| 配置项 | 确认值 |
|-------|-------|
| 主题数 | 4 个（固定） |
| 点赞加权 | 是 |
| 词云形状 | 默认矩形 |
| 时间维度 | 不启用 |
| 情感阈值 | 0.4 / 0.7 |

---

## 十二、预期成果

1. **定量结论**：两平台用户在各主题下的情感倾向差异
2. **定性洞察**：用户关注的核心话题及典型观点
3. **可视化报告**：词云、热力图、分布图等直观展示
