# 华为品牌社交媒体数据爬虫

本项目用于爬取华为品牌在B站、小红书、抖音三个平台的用户关注与口碑数据。

## 功能特点

- **B站爬虫**：爬取视频标题、作者、播放量、点赞、评论等数据
- **小红书爬虫**：爬取笔记内容、作者、互动数据等
- **抖音爬虫**：爬取视频信息、作者、互动数据等
- **统一数据格式**：所有平台数据统一保存为Excel和JSON格式
- **字段完整**：包含Post_ID、Platform、Publish_Date、Post_URL、Author_ID、Author_Name、Title、Content、Tags、Like_Count、Comment_Count、Collect_Count、Share_Count、View_Count等14个字段

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用说明

### 1. 基本使用

直接运行主程序：

```bash
python main.py
```

### 2. 单独使用某个平台爬虫

#### B站爬虫
```python
from bilibili_spider import BilibiliSpider

spider = BilibiliSpider()
results = spider.crawl(keyword="华为", max_pages=10)
```

#### 小红书爬虫
```python
from xiaohongshu_spider import XiaohongshuSpider

spider = XiaohongshuSpider()
# 使用selenium方式（推荐）
results = spider.crawl(keyword="华为", max_pages=10, use_selenium=True)
```

#### 抖音爬虫
```python
from douyin_spider import DouyinSpider

spider = DouyinSpider()
# 使用selenium方式（推荐）
results = spider.crawl(keyword="华为", max_pages=10, use_selenium=True)
```

### 3. 自定义配置

编辑 `main.py` 中的参数：

```python
keyword = "华为"  # 搜索关键词
max_pages = 10  # 每个平台最大爬取页数
use_selenium = True  # 是否使用selenium
platforms = ['bilibili', 'xiaohongshu', 'douyin']  # 要爬取的平台
```

## 注意事项

### B站
- B站API相对开放，可以直接使用requests爬取
- 建议控制请求频率，避免被封IP

### 小红书
- 小红书有较强的反爬机制，**强烈推荐使用selenium方式**
- 使用selenium需要安装Chrome浏览器和ChromeDriver
- ChromeDriver版本需要与Chrome浏览器版本匹配

### 抖音
- 抖音也有较强的反爬机制，**强烈推荐使用selenium方式**
- 使用selenium需要安装Chrome浏览器和ChromeDriver
- 可能需要处理登录弹窗

### Selenium配置

1. 安装Chrome浏览器
2. 下载对应版本的ChromeDriver：https://chromedriver.chromium.org/
3. 将ChromeDriver放到系统PATH中，或放在项目目录下

或者使用webdriver-manager自动管理：

```bash
pip install webdriver-manager
```

然后在代码中使用：

```python
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
```

## 输出文件

所有数据保存在 `output/` 目录下：

- `bilibili_YYYYMMDD_HHMMSS.xlsx` - B站数据（Excel格式）
- `bilibili_YYYYMMDD_HHMMSS.json` - B站数据（JSON格式）
- `xiaohongshu_YYYYMMDD_HHMMSS.xlsx` - 小红书数据（Excel格式）
- `xiaohongshu_YYYYMMDD_HHMMSS.json` - 小红书数据（JSON格式）
- `douyin_YYYYMMDD_HHMMSS.xlsx` - 抖音数据（Excel格式）
- `douyin_YYYYMMDD_HHMMSS.json` - 抖音数据（JSON格式）
- `all_platforms_YYYYMMDD_HHMMSS.xlsx` - 所有平台合并数据（Excel格式）
- `all_platforms_YYYYMMDD_HHMMSS.json` - 所有平台合并数据（JSON格式）

## 关键词过滤

所有爬虫都会自动过滤数据，确保只保存与搜索关键词（如"华为"）相关的内容：
- **B站**：检查标题是否包含"华为"或"huawei"
- **小红书**：检查标题是否包含关键词
- **抖音**：检查标题是否包含关键词

如果标题不包含关键词，该条数据将被跳过，确保数据相关性。

## 数据字段说明

根据 `posts.xlsx` 文件定义的字段：

| 字段名 | 英文字段名 | 说明 |
|--------|-----------|------|
| 帖子ID | Post_ID | 唯一标识符 |
| 平台 | Platform | 数据来源（BiliBili/XiaoHongShu/Douyin） |
| 发布时间 | Publish_Date | 发布时间戳 |
| 帖子URL | Post_URL | 原始数据链接 |
| 作者ID | Author_ID | 发布者身份 |
| 作者昵称 | Author_Name | 发布者名称 |
| 标题 | Title | 帖子标题 |
| 正文/简介 | Content | 帖子内容 |
| 标签/话题 | Tags | 平台标签 |
| 点赞数 | Like_Count | 互动量指标 |
| 评论数 | Comment_Count | 互动量指标 |
| 收藏数 | Collect_Count | 互动量指标 |
| 转发数 | Share_Count | 互动量指标 |
| 播放/阅读数 | View_Count | 内容触达范围指标 |

## 免责声明

本工具仅供学习和研究使用，请遵守各平台的使用条款和robots.txt协议。使用本工具时请注意：

1. 控制爬取频率，避免对服务器造成压力
2. 不要用于商业用途
3. 尊重平台的反爬机制
4. 遵守相关法律法规

## 常见问题

### Q: 为什么小红书和抖音爬取不到数据？
A: 这两个平台有较强的反爬机制，需要使用selenium方式，并且可能需要登录。建议使用selenium + 手动登录的方式。

### Q: 如何提高爬取成功率？
A: 
1. 使用selenium方式（小红书和抖音）
2. 增加请求延迟时间
3. 使用代理IP
4. 模拟真实用户行为

### Q: ChromeDriver版本不匹配怎么办？
A: 使用webdriver-manager可以自动下载匹配的ChromeDriver版本。

## 更新日志

- 2024-01-XX: 初始版本，支持B站、小红书、抖音三个平台

