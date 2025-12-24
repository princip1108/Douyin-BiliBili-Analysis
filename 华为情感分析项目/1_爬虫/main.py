"""
主程序：
"""
import pandas as pd
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple
import os

from bilibili_spider import BilibiliSpider
# from xiaohongshu_spider import XiaohongshuSpider  # 暂时不使用小红书
# from douyin_spider import DouyinSpider  # 暂时不使用抖音


class DataCollector:
    def __init__(self, output_dir: str = "output", debug: bool = False):
        """
        初始化数据收集器
        :param output_dir: 输出目录
        :param debug: 是否开启调试模式
        """
        self.output_dir = output_dir
        self.debug = debug
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
    
        self.bilibili_spider = BilibiliSpider(debug=debug, api_limit=100)
        # self.xiaohongshu_spider = XiaohongshuSpider(debug=debug)  # 暂时不使用小红书
        # self.douyin_spider = DouyinSpider(debug=debug)  # 暂时不使用抖音
    
    def collect_bilibili(self, keyword: str = "华为", max_pages: int = 25, max_videos: int = 500, use_selenium: bool = True, get_comments: bool = True) -> List[Dict]:
        """
        收集B站数据
        :param get_comments: 是否爬取评论
        :return: 帖子数据列表（包含评论）
        """
        print("=" * 60)
        print("开始爬取B站数据...")
        api_limit = getattr(self.bilibili_spider, 'api_limit', 50)
        if api_limit > 0:
            print(f"策略：前 {api_limit} 个视频通过API获取详细数据，其余视频仅使用页面提取的数据")
        else:
            print("策略：所有视频仅使用页面提取的数据（不调用API）")
        print("=" * 60)
        data = self.bilibili_spider.crawl(keyword=keyword, max_pages=max_pages, max_videos=max_videos, use_selenium=use_selenium)
        
        if get_comments and data:
            print("\n开始爬取B站评论...")
            for i, post in enumerate(data, 1):
                post_id = post.get('Post_ID', '')
                if post_id:
                    print(f"  正在爬取第 {i}/{len(data)} 个视频的评论: {post_id}")
                    post_comments = self.bilibili_spider.get_comments(post_id, top_n=10)  # 修改为热度前10条评论
                    # 将评论添加到帖子数据中
                    post['Top_Comments'] = post_comments
                    time.sleep(1)  # 避免请求过快
            print(f"B站评论爬取完成")
        
        return data
    
    
    def save_to_excel(self, data: List[Dict], filename: str):
        """
        保存数据到Excel文件（包含评论）
        :param data: 数据列表
        :param filename: 文件名（不含扩展名）
        """
        if not data:
            print(f"没有数据可保存到 {filename}")
            return
        
        
        processed_data = []
        for item in data:
            processed_item = item.copy()
            
            # 如果有评论，将评论列表转换为格式化的字符串
            if 'Top_Comments' in processed_item and processed_item['Top_Comments']:
                comments = processed_item['Top_Comments']
                # 格式化为易读的字符串：评论内容 | 作者 | 点赞数
                comment_strings = []
                for i, comment in enumerate(comments, 1):
                    content = comment.get('Comment_Content', '')
                    author = comment.get('Comment_Author', '')
                    like_count = comment.get('Comment_Like_Count', 0)
                    comment_str = f"{i}. {content} | 作者: {author} | 点赞: {like_count}"
                    comment_strings.append(comment_str)
                processed_item['Top_Comments'] = '\n'.join(comment_strings)
            else:
                processed_item['Top_Comments'] = ''
            
            processed_data.append(processed_item)
        
        
        df = pd.DataFrame(processed_data)
        
        # 确保列的顺序符合要求
        expected_columns = [
            'Post_ID', 'Platform', 'Publish_Date', 'Post_URL', 
            'Author_ID', 'Author_Name', 'Title', 'Content', 
            'Tags', 'Like_Count', 'Comment_Count', 'Collect_Count', 
            'Share_Count', 'View_Count', 'Top_Comments'
        ]
        
        # 添加缺失的列
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ''
        
        # 重新排列列的顺序
        df = df[expected_columns]
        
        # 保存到Excel
        filepath = os.path.join(self.output_dir, f"{filename}.xlsx")
        df.to_excel(filepath, index=False, engine='openpyxl')
        print(f"数据已保存到: {filepath}")
        print(f"共保存 {len(df)} 条数据")
    
    def save_to_json(self, data: List[Dict], filename: str):
        """
        保存数据到JSON文件
        :param data: 数据列表
        :param filename: 文件名（不含扩展名）
        """
        if not data:
            print(f"没有数据可保存到 {filename}")
            return
        
        filepath = os.path.join(self.output_dir, f"{filename}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到: {filepath}")
        print(f"共保存 {len(data)} 条数据")
    
    
    def collect_all(self, keyword: str = "华为", max_pages: int = 25, max_videos: int = 500, 
                    platforms: List[str] = None, use_selenium: bool = True, get_comments: bool = True):
        """
        收集所有平台的数据
        :param keyword: 搜索关键词
        :param max_pages: 每个平台最大爬取页数
        :param max_videos: 每个平台最大爬取视频数量（默认500）
        :param platforms: 要爬取的平台列表，None表示爬取所有平台
        :param use_selenium: 是否使用selenium（适用于小红书和抖音）
        :param get_comments: 是否爬取评论
        """
        if platforms is None:
            platforms = ['bilibili']  # 默认只爬取B站
        
        all_data = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 收集各平台数据
        if 'bilibili' in platforms:
            bilibili_data = self.collect_bilibili(
                keyword=keyword, max_pages=max_pages, max_videos=max_videos, use_selenium=use_selenium, get_comments=get_comments
            )
            if bilibili_data:
                self.save_to_excel(bilibili_data, f"bilibili_{timestamp}")
                self.save_to_json(bilibili_data, f"bilibili_{timestamp}")
                all_data.extend(bilibili_data)
        

        if all_data:
            self.save_to_excel(all_data, f"all_platforms_{timestamp}")
            self.save_to_json(all_data, f"all_platforms_{timestamp}")
        
        # 统计评论数量
        total_comments = sum(len(post.get('Top_Comments', [])) if isinstance(post.get('Top_Comments'), list) else 0 for post in all_data)
        
        print("\n" + "=" * 60)
        print("所有平台数据收集完成！")
        print(f"总计: {len(all_data)} 条帖子数据")
        print(f"总计: {total_comments} 条评论数据（已整合到帖子数据中）")
        print("=" * 60)


def main():
    """
    主函数
    """
 
    keyword = "华为"  # 搜索
    max_pages = 25  
    max_videos = 500 
    use_selenium = True  
    debug = True 
    get_comments = True  
    

    platforms = ['bilibili'] 
  
    

    collector = DataCollector(output_dir="output", debug=debug)
    
    
    collector.collect_all(
        keyword=keyword,
        max_pages=max_pages,
        max_videos=max_videos,
        platforms=platforms,
        use_selenium=use_selenium,
        get_comments=get_comments
    )


if __name__ == "__main__":
    main()

