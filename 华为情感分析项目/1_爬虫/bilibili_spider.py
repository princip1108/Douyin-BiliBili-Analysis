"""
B站（Bilibili）爬虫
用于爬取华为相关视频数据
"""
import requests
import json
import time
import re
from datetime import datetime
from typing import List, Dict
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BilibiliSpider:
    def __init__(self, timeout: int = 30, max_retries: int = 3, debug: bool = False, api_limit: int = 100):
        """
        初始化爬虫
        :param timeout: 请求超时时间（秒）
        :param max_retries: 最大重试次数
        :param debug: 是否开启调试模式
        :param api_limit: 只对前N个视频调用API获取详细数据（默认100，设置为0表示不使用API）
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.debug = debug
        self.api_limit = api_limit  # 只对前N个视频调用API
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/',
            'Origin': 'https://www.bilibili.com',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        # 创建session并配置重试策略
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 先访问主页获取cookie，避免412错误
        try:
            print("正在初始化B站连接...")
            self.session.get('https://www.bilibili.com/', timeout=10)
            time.sleep(1)
        except:
            pass
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _make_request(self, url: str, params: dict = None, retries: int = None) -> requests.Response:
        """
        发送HTTP请求，带重试机制
        """
        if retries is None:
            retries = self.max_retries
        
        for attempt in range(retries + 1):
            try:
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=self.timeout,
                    stream=False
                )
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout:
                if attempt < retries:
                    wait_time = (attempt + 1) * 2  # 指数退避
                    print(f"请求超时，{wait_time}秒后重试 (第{attempt + 1}/{retries}次)...")
                    time.sleep(wait_time)
                else:
                    print(f"请求超时，已重试{retries}次，放弃")
                    raise
            except requests.exceptions.RequestException as e:
                if attempt < retries:
                    wait_time = (attempt + 1) * 2
                    print(f"请求失败: {e}，{wait_time}秒后重试 (第{attempt + 1}/{retries}次)...")
                    time.sleep(wait_time)
                else:
                    print(f"请求失败，已重试{retries}次: {e}")
                    raise
        
        raise requests.exceptions.RequestException("请求失败")
    
    def get_comments(self, bvid: str, top_n: int = 10) -> List[Dict]:  # 修改为默认获取前10条评论
        """
        获取视频的热门评论（按点赞数排序，取前N条）
        :param bvid: 视频BVID
        :param top_n: 获取前N条评论
        :return: 评论列表
        """
        comments = []
        try:
            # B站评论API
            comment_url = "https://api.bilibili.com/x/v2/reply/main"
            params = {
                'type': 1,  # 1表示视频
                'oid': '',  # 需要先获取oid
                'mode': 3,  # 3表示按热度排序
                'next': 0,
                'ps': 20  # 每页20条
            }
            
            # 先获取视频信息以获取oid（aid）
            video_info_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            try:
                response = self._make_request(video_info_url)
                video_data = response.json()
                if video_data.get('code') == 0:
                    oid = video_data.get('data', {}).get('aid', '')
                    if oid:
                        params['oid'] = oid
                    else:
                        if self.debug:
                            print(f"[DEBUG] 无法获取aid，跳过评论爬取")
                        return comments
                else:
                    if self.debug:
                        print(f"[DEBUG] 获取视频信息失败: {video_data.get('message', '未知错误')}")
                    return comments
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 获取视频信息异常: {e}")
                return comments
            
            if not params['oid']:
                return comments
            
            # 获取评论
            try:
                response = self._make_request(comment_url, params=params)
                data = response.json()
                
                if data.get('code') == 0:
                    replies = data.get('data', {}).get('replies', [])
                    
                    # 按点赞数排序
                    sorted_replies = sorted(
                        replies,
                        key=lambda x: x.get('like', 0),
                        reverse=True
                    )
                    
                    # 取前N条
                    for reply in sorted_replies[:top_n]:
                        comment_info = {
                            'Post_ID': bvid,
                            'Comment_ID': str(reply.get('rpid', '')),
                            'Comment_Content': reply.get('content', {}).get('message', ''),
                            'Comment_Author': reply.get('member', {}).get('uname', ''),
                            'Comment_Like_Count': reply.get('like', 0),
                            'Comment_Time': datetime.fromtimestamp(reply.get('ctime', 0)).strftime('%Y-%m-%d %H:%M:%S') if reply.get('ctime') else '',
                            'Platform': 'BiliBili'
                        }
                        comments.append(comment_info)
                        
                    if self.debug:
                        print(f"[DEBUG] ✓ 获取到 {len(comments)} 条B站评论")
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 获取B站评论失败: {e}")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] B站评论爬取出错: {e}")
        
        return comments
    
    def search_videos(self, keyword: str = "华为", page: int = 1, page_size: int = 20) -> List[Dict]:
        """
        搜索视频
        :param keyword: 搜索关键词
        :param page: 页码
        :param page_size: 每页数量
        :return: 视频列表
        """
        # 使用新的搜索API端点
        url = "https://api.bilibili.com/x/web-interface/wbi/search/type"
        params = {
            'search_type': 'video',
            'keyword': keyword,
            'page': page,
            'page_size': page_size,
            'order': 'totalrank',  # 综合排序
            'duration': 0,  # 全部时长
            'tids_1': 0,  # 全部分区
        }
        
        # 如果新API失败，尝试旧API
        try:
            response = self._make_request(url, params=params)
            data = response.json()
        except:
            # 回退到旧API
            url = "https://api.bilibili.com/x/web-interface/search/type"
            params = {
                'search_type': 'video',
                'keyword': keyword,
                'page': page,
                'pagesize': page_size,
                'order': 'totalrank',
                'duration': 0,
                'tids_1': 0,
            }
            try:
                response = self._make_request(url, params=params)
                data = response.json()
            except Exception as e:
                print(f"搜索视频时出错: {e}")
                return []
        
        if data.get('code') == 0:
            videos = []
            result_list = data.get('data', {}).get('result', [])
            print(f"  搜索到 {len(result_list)} 个视频")
            
            for idx, item in enumerate(result_list, 1):
                print(f"  正在处理第 {idx}/{len(result_list)} 个视频...", end='\r')
                video_info = self._parse_video_info(item)
                if video_info:
                    videos.append(video_info)
                # 添加小延迟，避免请求过快
                if idx < len(result_list):
                    time.sleep(random.uniform(0.3, 0.6))
            print()  # 换行
            return videos
        else:
            print(f"搜索失败: {data.get('message', '未知错误')}")
            return []
    
    def search_videos_with_selenium(self, keyword: str = "华为", max_pages: int = 25, max_videos: int = 500) -> List[Dict]:
        """
        使用Selenium方式搜索视频（推荐，避免412错误）
        :param keyword: 搜索关键词
        :param max_pages: 最大爬取页数（默认25页，约500个视频）
        :param max_videos: 最大爬取视频数量（默认500）
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
            from urllib.parse import quote
        except ImportError:
            print("请安装selenium: pip install selenium")
            return []
        
        all_videos = []
        driver = None
        
        try:
            # 配置Chrome选项
            chrome_options = Options()
            # chrome_options.add_argument('--headless')  # 可以开启无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 尝试使用webdriver-manager
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except ImportError:
                driver = webdriver.Chrome(options=chrome_options)
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 访问搜索页面
            search_url = f"https://search.bilibili.com/all?keyword={quote(keyword)}"
            print(f"正在访问: {search_url}")
            driver.get(search_url)
            time.sleep(3)
            
            for page in range(1, max_pages + 1):
                print(f"正在爬取B站第 {page} 页...")
                
                # 等待视频列表加载（翻页后需要更长的等待时间）
                wait_time = 5 if page == 1 else 8  # 第一页5秒，后续页面8秒
                try:
                    WebDriverWait(driver, wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".video-item, .bili-video-card"))
                    )
                    # 额外等待，确保页面完全加载（特别是翻页后）
                    if page > 1:
                        time.sleep(2)  # 翻页后额外等待2秒
                except TimeoutException:
                    print(f"  页面加载超时（等待了{wait_time}秒），尝试继续...")
                    time.sleep(3)  # 超时后等待3秒再继续
                
                # 获取视频元素 - 使用更多选择器
                video_elements = []
                selectors = [
                    ".video-item",
                    ".bili-video-card",
                    "li[class*='video']",
                    "[class*='bili-video-card']",
                    "a[href*='/video/BV']"
                ]
                for selector in selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        video_elements = elements
                        print(f"  使用选择器 '{selector}' 找到 {len(video_elements)} 个视频")
                        break
                
                if not video_elements:
                    print("  未找到视频元素，尝试等待...")
                    time.sleep(3)
                    video_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/video/BV']")
                    print(f"  再次尝试找到 {len(video_elements)} 个视频")
                
                page_videos = []
                # 限制每页处理的视频数量，避免处理过多导致超时
                # 但如果还没达到目标数量，继续处理
                elements_to_process = video_elements
                if len(all_videos) < max_videos:
                    # 如果当前累计数量 + 本页元素数 > 目标数量，只处理需要的部分
                    remaining_needed = max_videos - len(all_videos)
                    if len(video_elements) > remaining_needed:
                        elements_to_process = video_elements[:remaining_needed]
                        if self.debug:
                            print(f"[DEBUG] 本页有 {len(video_elements)} 个视频，但只需要 {remaining_needed} 个，只处理前 {remaining_needed} 个")
                
                for idx, element in enumerate(elements_to_process, 1):
                    # 如果已经达到目标数量，提前停止
                    if len(all_videos) >= max_videos:
                        if self.debug:
                            print(f"[DEBUG] 已达到目标数量 {max_videos}，停止处理本页剩余元素")
                        break
                    
                    try:
                        # 判断是否应该调用API：只对前api_limit个视频调用API
                        current_count = len(all_videos)
                        use_api = (self.api_limit > 0) and (current_count < self.api_limit)
                        api_status = "[API]" if use_api else "[页面]"
                        
                        video_info = self._parse_selenium_element(element, use_api=use_api)
                        if video_info and video_info.get('Post_ID'):
                            # 检查是否已存在
                            existing_ids = [v['Post_ID'] for v in all_videos]
                            if video_info['Post_ID'] not in existing_ids:
                                all_videos.append(video_info)
                                page_videos.append(video_info)
                        elif self.debug and idx <= 3:  # 只对前3个失败的元素输出详细信息
                            print(f"\n[DEBUG] 视频解析失败: element={element.tag_name}, text={element.text[:50] if element.text else 'N/A'}")
                        
                        # 显示处理进度和API使用情况
                        progress_info = f"  已处理 {idx}/{len(elements_to_process)} 个视频（成功 {len(page_videos)} 个，累计 {len(all_videos)}/{max_videos}）{api_status if video_info else ''}"
                        print(progress_info, end='\r')
                        # 添加延迟，避免API请求过快（处理大量视频时增加延迟）
                        # 前50个视频延迟较短，之后增加延迟避免限流
                        if len(all_videos) < 50:
                            time.sleep(random.uniform(0.3, 0.6))
                        else:
                            time.sleep(random.uniform(0.8, 1.2))  # 处理更多视频时增加延迟
                    except Exception as e:
                        # 输出错误信息以便调试
                        if self.debug and idx <= 3:
                            print(f"\n[DEBUG] 处理视频元素时出错: {e}")
                        continue
                print()  # 换行
                print(f"  第 {page} 页成功解析 {len(page_videos)} 条数据（累计 {len(all_videos)} 条）")
                
                # 如果已经获取足够多的视频，可以提前停止
                if len(all_videos) >= max_videos:  # 如果达到目标数量，可以提前停止
                    print(f"  已获取 {len(all_videos)} 个视频，达到目标数量 {max_videos}，停止爬取")
                    break
                
                # 如果已经达到目标数量，不需要翻页
                if len(all_videos) >= max_videos:
                    print(f"  已达到目标数量 {max_videos}，停止翻页")
                    break
                
                # 尝试翻页
                if page < max_pages:
                    try:
                        # 尝试多种翻页选择器
                        next_selectors = [
                            ".pager .next",
                            ".pagination .next",
                            "button.next",
                            "[class*='next']",
                            ".page-item.next",
                            "a[aria-label='下一页']",
                            "button[aria-label='下一页']",
                            ".be-pager-next",
                            ".bili-pagination-item-next"
                        ]
                        next_button = None
                        for selector in next_selectors:
                            try:
                                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                for elem in elements:
                                    if elem.is_enabled() and elem.is_displayed():
                                        next_button = elem
                                        break
                                if next_button:
                                    break
                            except:
                                continue
                        
                        if next_button:
                            # 滚动到按钮位置
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                            time.sleep(1)
                            next_button.click()
                            time.sleep(5)  # 增加等待时间，确保新页面完全加载
                            # 等待页面稳定
                            try:
                                WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, ".video-item, .bili-video-card"))
                                )
                            except:
                                pass
                            print(f"  ✓ 成功翻页到第 {page + 1} 页")
                        else:
                            # 尝试使用JavaScript直接修改URL翻页
                            try:
                                current_url = driver.current_url
                                if 'page=' in current_url:
                                    # 替换页码
                                    import re
                                    new_url = re.sub(r'page=\d+', f'page={page + 1}', current_url)
                                else:
                                    # 添加页码参数
                                    separator = '&' if '?' in current_url else '?'
                                    new_url = f"{current_url}{separator}page={page + 1}"
                                driver.get(new_url)
                                time.sleep(5)  # 增加等待时间
                                # 等待页面稳定
                                try:
                                    WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, ".video-item, .bili-video-card"))
                                    )
                                except:
                                    pass
                                print(f"  ✓ 使用URL方式翻页到第 {page + 1} 页")
                            except Exception as e2:
                                if self.debug:
                                    print(f"  URL翻页也失败: {e2}")
                                print("  ⚠ 无法翻页，停止爬取")
                                break
                    except Exception as e:
                        if self.debug:
                            print(f"  翻页失败: {e}")
                        # 尝试使用URL方式翻页
                        try:
                            current_url = driver.current_url
                            if 'page=' in current_url:
                                import re
                                new_url = re.sub(r'page=\d+', f'page={page + 1}', current_url)
                            else:
                                separator = '&' if '?' in current_url else '?'
                                new_url = f"{current_url}{separator}page={page + 1}"
                                driver.get(new_url)
                                time.sleep(5)  # 增加等待时间
                                # 等待页面稳定
                                try:
                                    WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, ".video-item, .bili-video-card"))
                                    )
                                except:
                                    pass
                                print(f"  ✓ 使用URL方式翻页到第 {page + 1} 页")
                        except Exception as e2:
                            if self.debug:
                                print(f"  URL翻页也失败: {e2}")
                            print("  ⚠ 无法翻页，停止爬取")
                            break
                
                time.sleep(random.uniform(2, 3))
        
        except Exception as e:
            print(f"Selenium爬取时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                driver.quit()
        
        return all_videos
    
    def _parse_selenium_element(self, element, use_api: bool = True) -> Dict:
        """
        解析Selenium获取的视频元素，可选地通过API获取详细信息
        :param element: Selenium元素对象
        :param use_api: 是否调用API获取详细信息（False时只使用页面提取的数据）
        """
        try:
            if self.debug:
                print(f"\n[DEBUG] 开始解析元素...")
            
            # 获取视频链接
            href = ''
            title = ''
            
            # 优化：优先使用HTML提取（最可靠的方法）
            # 方法1: 直接从HTML中提取（最快最可靠）
            try:
                html = element.get_attribute('outerHTML')
                if html:
                    # 尝试多种模式匹配
                    patterns = [
                        r'href="([^"]*\/video\/BV[^"]*)"',  # 标准格式
                        r'href="([^"]*\/video\/BV[^"]*)"',  # 带转义的
                        r'href=([^\s>]*\/video\/BV[^\s>]*)',  # 无引号
                        r'/video/(BV[a-zA-Z0-9]+)',  # 直接匹配BVID
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, html)
                        if match:
                            href_candidate = match.group(1) if match.lastindex else match.group(0)
                            # 如果是相对路径，补全
                            if href_candidate.startswith('//'):
                                href = 'https:' + href_candidate
                            elif href_candidate.startswith('/'):
                                href = 'https://www.bilibili.com' + href_candidate
                            elif '/video/BV' in href_candidate:
                                href = href_candidate if href_candidate.startswith('http') else 'https://www.bilibili.com' + href_candidate
                            else:
                                # 只提取了BVID
                                bvid_only = re.search(r'(BV[a-zA-Z0-9]+)', href_candidate)
                                if bvid_only:
                                    href = f"https://www.bilibili.com/video/{bvid_only.group(1)}"
                            if href:
                                if self.debug:
                                    print(f"[DEBUG] ✓ 从HTML中提取到链接: {href}")
                                break
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] HTML提取失败: {e}")
                pass
            
            # 方法2: 如果HTML提取失败，尝试CSS选择器（按优先级）
            if not href:
                link_selectors = [
                    ".bili-video-card__info--tit a",  # 最可能的选择器
                    ".bili-video-card__info a",
                    "a[href*='/video/BV']",
                    "a[href*='/video/']", 
                ]
                for selector in link_selectors:
                    try:
                        link_element = element.find_element(By.CSS_SELECTOR, selector)
                        href = link_element.get_attribute('href')
                        if href and '/video/' in href:
                            if self.debug:
                                print(f"[DEBUG] ✓ 使用选择器 '{selector}' 获取到链接: {href}")
                            break
                    except:
                        continue
            
            # 方法3: 查找所有a标签
            if not href:
                try:
                    all_links = element.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        href_candidate = link.get_attribute('href')
                        if href_candidate and '/video/BV' in href_candidate:
                            href = href_candidate
                            if self.debug:
                                print(f"[DEBUG] ✓ 从所有a标签中找到链接: {href}")
                            break
                except:
                    pass
            
            # 方法4: 从元素本身获取
            if not href:
                try:
                    href = element.get_attribute('href')
                    if href and '/video/' in href:
                        if self.debug:
                            print(f"[DEBUG] ✓ 从元素本身获取到链接: {href}")
                except:
                    pass
            
            # 单独获取标题 - 使用更准确的选择器
            title_selectors = [
                ".bili-video-card__info--tit",
                ".bili-video-card__info--tit a",
                "[class*='video-card__info--tit']",
                ".title",
                "[class*='title']",
                "a[href*='/video/']"
            ]
            for selector in title_selectors:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip() or title_elem.get_attribute('title')
                    if title and len(title) > 5:  # 确保标题有意义
                        break
                except:
                    continue
            
            # 从链接中提取BVID（必须是BV开头的）
            bvid = ''
            if href:
                # 尝试多种模式提取BVID
                patterns = [
                    r'/video/(BV[a-zA-Z0-9]+)',  # 标准格式
                    r'video/(BV[a-zA-Z0-9]+)',   # 无前导斜杠
                    r'(BV[a-zA-Z0-9]+)',         # 直接匹配
                ]
                for pattern in patterns:
                    match = re.search(pattern, href)
                    if match:
                        bvid = match.group(1)
                        if self.debug:
                            print(f"[DEBUG] 提取到BVID: {bvid}")
                        break
            
            # 如果没有有效的BVID，跳过这条数据
            if not bvid or not bvid.startswith('BV'):
                if self.debug:
                    print(f"[DEBUG] ✗ 无效的BVID: '{bvid}', href: {href}")
                    # 显示元素的部分信息用于调试
                    try:
                        print(f"[DEBUG]   元素文本前100字符: {element.text[:100]}")
                        print(f"[DEBUG]   元素标签: {element.tag_name}")
                    except:
                        pass
                return None
            
            # 尝试通过API获取详细信息（仅当use_api=True时）
            video_detail = {}
            if use_api:
                if self.debug:
                    print(f"[DEBUG] 调用API获取视频详情: {bvid}")
                video_detail = self.get_video_detail(bvid)
            else:
                if self.debug:
                    print(f"[DEBUG] 跳过API调用，仅使用页面提取的数据: {bvid}")
            
            # 如果API获取成功，使用API数据并检查关键词
            if video_detail:
                api_title = video_detail.get('title', '')
                stat = video_detail.get('stat', {})
                owner = video_detail.get('owner', {})
                pubdate = video_detail.get('pubdate', 0)
                
                # 由于搜索结果已经包含关键词，这里不再严格过滤
                # 只做简单的验证，确保标题存在
                if not api_title:
                    if self.debug:
                        print(f"[DEBUG] ⚠ API返回的标题为空")
                    # 即使标题为空，也继续处理（使用其他数据）
                elif self.debug:
                    api_title_lower = api_title.lower()
                    keywords = ['华为', 'huawei', '鸿蒙', 'harmony', 'mate', 'p系列', 'nova', 'honor', '荣耀']
                    matched_keywords = [kw for kw in keywords if kw in api_title_lower]
                    if matched_keywords:
                        print(f"[DEBUG] ✓ 关键词匹配: {matched_keywords}, 标题: {api_title[:50]}")
                    else:
                        print(f"[DEBUG] ⚠ 标题不完全匹配关键词，但保留（搜索已过滤）: {api_title[:50]}")
                
                return {
                    'Post_ID': bvid,
                    'Platform': 'BiliBili',
                    'Publish_Date': datetime.fromtimestamp(pubdate).strftime('%Y-%m-%d %H:%M:%S') if pubdate else '',
                    'Post_URL': href or f"https://www.bilibili.com/video/{bvid}",
                    'Author_ID': str(owner.get('mid', '')),
                    'Author_Name': owner.get('name', ''),
                    'Title': api_title,
                    'Content': video_detail.get('desc', ''),
                    'Tags': ','.join([tag.get('tag_name', '') for tag in video_detail.get('tags', [])]),
                    'Like_Count': stat.get('like', 0),
                    'Comment_Count': stat.get('reply', 0),
                    'Collect_Count': stat.get('favorite', 0),
                    'Share_Count': stat.get('share', 0),
                    'View_Count': stat.get('view', 0)
                }
            
            # 如果API失败，使用页面提取的数据
            # 注意：API失败可能是因为限流，需要增加延迟
            if not video_detail and self.debug:
                print(f"[DEBUG] ⚠ API获取视频详情失败，使用页面提取的数据")
            
            # 如果还没有标题，尝试从元素文本中提取
            if not title:
                try:
                    all_text = element.text.strip()
                    lines = all_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        # 跳过数字、时间等
                        if (line and len(line) > 5 and 
                            not line.isdigit() and 
                            not re.match(r'^\d{2}:\d{2}:\d{2}$', line) and
                            not re.match(r'^\d+分钟前$', line) and
                            not re.match(r'^\d+小时前$', line) and
                            '播放' not in line and '点赞' not in line):
                            title = line
                            break
                except:
                    pass
            
            # 清理标题，移除时间戳等无关信息
            if title:
                lines = title.split('\n')
                for line in lines:
                    line = line.strip()
                    # 跳过纯数字、时间格式等
                    if (line and len(line) > 5 and 
                        not line.isdigit() and 
                        not re.match(r'^\d{2}:\d{2}:\d{2}$', line) and
                        not re.match(r'^\d+分钟前$', line) and
                        not re.match(r'^\d+小时前$', line)):
                        title = line
                        break
            
            # 由于搜索结果已经包含关键词，这里不再严格过滤
            # 只做简单的验证，确保有基本数据（BVID必须有）
            if not bvid or not bvid.startswith('BV'):
                if self.debug:
                    print(f"[DEBUG] ✗ 无效的BVID，跳过")
                return None
            
            # 如果标题存在，检查关键词（但不强制要求，因为搜索已过滤）
            if title and self.debug:
                title_lower = title.lower()
                keywords = ['华为', 'huawei', '鸿蒙', 'harmony', 'mate', 'p系列', 'nova', 'honor', '荣耀']
                matched_keywords = [kw for kw in keywords if kw in title_lower]
                if matched_keywords:
                    print(f"[DEBUG] ✓ 关键词匹配: {matched_keywords}, 标题: {title[:50]}")
                else:
                    print(f"[DEBUG] ⚠ 标题不完全匹配关键词，但保留（搜索已过滤）: {title[:50]}")
            
            # 获取作者信息
            author_name = ''
            author_selectors = [
                ".up-name", 
                ".up", 
                "[class*='up-name']", 
                "[class*='up']", 
                ".username",
                ".bili-video-card__info--author"
            ]
            for selector in author_selectors:
                try:
                    author_element = element.find_element(By.CSS_SELECTOR, selector)
                    author_name = author_element.text.strip()
                    if author_name:
                        break
                except:
                    continue
            
            # 获取所有文本信息用于解析数据
            info_text = element.text
            
            # 解析播放量
            view_count = 0
            view_patterns = [
                r'(\d+\.?\d*)[万]?播放',
                r'(\d+\.?\d*)[万]?次播放',
                r'播放[：:]\s*(\d+\.?\d*)[万]?',
                r'(\d+\.?\d*)[万]?次'
            ]
            for pattern in view_patterns:
                view_match = re.search(pattern, info_text)
                if view_match:
                    view_count = self._parse_count(view_match)
                    break
            
            return {
                'Post_ID': bvid,
                'Platform': 'BiliBili',
                'Publish_Date': '',
                'Post_URL': href or f"https://www.bilibili.com/video/{bvid}",
                'Author_ID': '',
                'Author_Name': author_name,
                'Title': title or f"视频 {bvid}",
                'Content': title,
                'Tags': '',
                'Like_Count': 0,  # 页面通常不显示点赞数
                'Comment_Count': 0,
                'Collect_Count': 0,
                'Share_Count': 0,
                'View_Count': view_count
            }
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] ✗ 解析出错: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def _parse_count(self, match) -> int:
        """解析数量（支持万单位）"""
        if not match:
            return 0
        count_str = match.group(1)
        try:
            count = float(count_str)
            if '万' in match.group(0):
                count = int(count * 10000)
            return int(count)
        except:
            return 0
    
    def _parse_video_info(self, item: Dict) -> Dict:
        """
        解析视频信息
        """
        try:
            # 获取视频基本信息
            bvid = item.get('bvid', '')
            if not bvid:
                return None
            
            # 解析发布时间
            pubdate = item.get('pubdate', 0)
            publish_date = datetime.fromtimestamp(pubdate).strftime('%Y-%m-%d %H:%M:%S') if pubdate else ''
            
            # 解析标签
            tags = item.get('tag', '')
            if isinstance(tags, list):
                tags = ','.join([t.get('tag_name', '') for t in tags if isinstance(t, dict)])
            
            # 从搜索结果中获取基础数据
            title = item.get('title', '').replace('<em class="keyword">', '').replace('</em>', '')
            author = item.get('author', '')
            mid = item.get('mid', '')
            
            # 检查标题是否包含关键词（放宽条件）
            title_lower = title.lower() if title else ''
            # 由于搜索结果已经包含关键词，这里不再严格过滤
            # 只做简单的验证，确保标题存在
            if not title:
                if self.debug:
                    print(f"[DEBUG] ⚠ 未提取到标题，但保留（搜索已过滤）")
                # 不返回None，继续处理（因为搜索已经过滤过了）
            elif self.debug:
                keywords = ['华为', 'huawei', '鸿蒙', 'harmony', 'mate', 'p系列', 'nova', 'honor', '荣耀']
                matched_keywords = [kw for kw in keywords if kw in title_lower]
                if matched_keywords:
                    print(f"[DEBUG] ✓ 关键词匹配: {matched_keywords}, 标题: {title[:50]}")
                else:
                    print(f"[DEBUG] ⚠ 标题不完全匹配关键词，但保留（搜索已过滤）: {title[:50]}")
            
            # 尝试获取视频详细信息（如果失败，使用搜索结果中的数据）
            video_detail = self.get_video_detail(bvid)
            
            # 如果获取详情失败，使用搜索结果中的基础数据
            if not video_detail:
                # 从搜索结果中提取数据
                return {
                    'Post_ID': bvid,
                    'Platform': 'BiliBili',
                    'Publish_Date': publish_date,
                    'Post_URL': f"https://www.bilibili.com/video/{bvid}",
                    'Author_ID': str(mid),
                    'Author_Name': author,
                    'Title': title,
                    'Content': item.get('description', ''),
                    'Tags': tags,
                    'Like_Count': item.get('like', 0) or 0,
                    'Comment_Count': item.get('video_review', 0) or 0,
                    'Collect_Count': 0,  # 搜索结果中没有收藏数
                    'Share_Count': 0,  # 搜索结果中没有分享数
                    'View_Count': item.get('play', 0) or 0
                }
            
            # 使用详细数据
            return {
                'Post_ID': bvid,
                'Platform': 'BiliBili',
                'Publish_Date': publish_date,
                'Post_URL': f"https://www.bilibili.com/video/{bvid}",
                'Author_ID': str(mid),
                'Author_Name': author,
                'Title': title,
                'Content': video_detail.get('desc', ''),
                'Tags': tags,
                'Like_Count': video_detail.get('stat', {}).get('like', 0),
                'Comment_Count': video_detail.get('stat', {}).get('reply', 0),
                'Collect_Count': video_detail.get('stat', {}).get('favorite', 0),
                'Share_Count': video_detail.get('stat', {}).get('share', 0),
                'View_Count': video_detail.get('stat', {}).get('view', 0)
            }
        except Exception as e:
            print(f"\n解析视频信息时出错: {e}")
            return None
    
    def get_video_detail(self, bvid: str) -> Dict:
        """
        获取视频详细信息
        """
        url = f"https://api.bilibili.com/x/web-interface/view"
        params = {'bvid': bvid}
        
        try:
            # 增加延迟，避免API请求过快导致限流（特别是处理大量视频时）
            time.sleep(random.uniform(0.8, 1.5))  # 增加延迟范围，避免请求过快
            response = self._make_request(url, params=params, retries=3)  # 增加重试次数
            data = response.json()
            
            if data.get('code') == 0:
                return data.get('data', {})
            elif self.debug:
                print(f"[DEBUG] API返回错误: code={data.get('code')}, message={data.get('message', '未知错误')}")
            return {}
        except requests.exceptions.HTTPError as e:
            # HTTP错误（如429限流），增加等待时间
            if e.response and e.response.status_code == 429:
                if self.debug:
                    print(f"[DEBUG] ⚠ API限流（429），等待更长时间...")
                time.sleep(random.uniform(3, 5))  # 限流时等待更长时间
            elif self.debug:
                print(f"[DEBUG] API请求HTTP错误: {e}")
            return {}
        except Exception as e:
            # 其他错误，静默失败，返回空字典，使用搜索结果中的数据
            if self.debug:
                print(f"[DEBUG] API请求异常: {e}")
            return {}
    
    def crawl(self, keyword: str = "华为", max_pages: int = 25, max_videos: int = 500, use_selenium: bool = True) -> List[Dict]:
        """
        爬取多页数据
        :param keyword: 搜索关键词
        :param max_pages: 最大爬取页数（如果设置了max_videos，会自动计算）
        :param max_videos: 最大爬取视频数量（默认500，会自动计算需要的页数）
        :param use_selenium: 是否使用selenium（推荐，避免412错误）
        :return: 所有视频数据
        """
        # 如果设置了max_videos，自动计算需要的页数（每页约20个视频）
        if max_videos > 0:
            calculated_pages = (max_videos // 20) + 1  # 向上取整
            if calculated_pages > max_pages:
                max_pages = calculated_pages
                if self.debug:
                    print(f"[DEBUG] 根据max_videos={max_videos}，自动设置max_pages={max_pages}")
        if use_selenium:
            print(f"使用Selenium方式爬取（推荐）...目标：最多 {max_videos} 个视频")
            all_videos = self.search_videos_with_selenium(keyword, max_pages, max_videos)
            # 如果达到目标数量，提前停止
            if len(all_videos) >= max_videos:
                all_videos = all_videos[:max_videos]
                print(f"已达到目标数量 {max_videos}，停止爬取")
            print(f"B站爬取完成，共获取 {len(all_videos)} 条数据")
            return all_videos
        
        # API方式（可能被限制）
        all_videos = []
        
        for page in range(1, max_pages + 1):
            print(f"正在爬取B站第 {page} 页...")
            try:
                videos = self.search_videos(keyword, page=page)
                
                if not videos:
                    print(f"第 {page} 页没有数据，停止爬取")
                    break
                
                all_videos.extend(videos)
                print(f"第 {page} 页获取到 {len(videos)} 条数据")
                
                # 延迟，避免请求过快
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"第 {page} 页爬取失败: {e}")
                # 如果连续失败，可以选择停止或继续
                if page == 1:
                    print("第一页就失败，建议使用Selenium方式（use_selenium=True）")
                    break
                else:
                    print("继续尝试下一页...")
                    time.sleep(5)  # 失败后等待更长时间
        
        print(f"B站爬取完成，共获取 {len(all_videos)} 条数据")
        return all_videos


if __name__ == "__main__":
    spider = BilibiliSpider()
    # 测试爬取
    results = spider.crawl(keyword="华为", max_pages=2)
    print(f"\n测试结果: 共获取 {len(results)} 条数据")
    if results:
        print("\n第一条数据示例:")
        print(json.dumps(results[0], ensure_ascii=False, indent=2))

