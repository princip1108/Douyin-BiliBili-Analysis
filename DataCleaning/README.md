# 数据清洗程序

## 功能说明

本程序用于清洗B站和抖音的CSV数据，主要功能包括：

1. **删除重复值**：根据唯一标识符（如video_id、comment_id等）删除重复记录
2. **填充缺失值**：将缺失的互动数据填充为0，其他字段填充为空字符串
3. **数据类型转换**：将点赞、播放、收藏、转发等互动数据转换为可进行数值运算的格式
   - 支持处理中文单位（如"1.2万"转换为12000）
   - 支持处理纯数字字符串
   - 自动处理空值和异常值

## 使用方法

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行程序

```bash
python data_cleaning.py
```

### 3. 输出结果

清洗后的数据将保存在 `cleaned_data` 文件夹中，按平台分类：
- **B站数据**：保存在 `cleaned_data/bili/` 文件夹中
- **抖音数据**：保存在 `cleaned_data/dy/` 文件夹中

文件名格式为 `cleaned_原文件名.csv`

## 处理的数据类型

### B站数据
- **视频数据** (search_videos_*.csv)
  - 处理字段：liked_count, disliked_count, video_play_count, video_favorite_count, video_share_count, video_coin_count, video_danmaku, video_comment
- **评论数据** (search_comments_*.csv)
  - 处理字段：sub_comment_count, like_count
- **创作者数据** (search_creators_*.csv)
  - 处理字段：total_fans, total_liked

### 抖音数据
- **内容数据** (search_contents_*.csv)
  - 处理字段：liked_count, collected_count, comment_count, share_count
- **评论数据** (search_comments_*.csv)
  - 处理字段：sub_comment_count, like_count

## 注意事项

- 程序会自动识别并处理data文件夹下的所有CSV文件
- 重复值删除基于唯一标识符（video_id、comment_id、user_id、aweme_id等）
- 所有互动数据最终都会转换为数值类型，缺失值填充为0
- 输出文件使用UTF-8-BOM编码，确保Excel可以正确打开中文

