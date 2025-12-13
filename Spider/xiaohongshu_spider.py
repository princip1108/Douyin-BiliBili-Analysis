"""
小红书（XiaoHongShu）爬虫
用于爬取华为相关笔记数据
注意：小红书有较强的反爬机制，可能需要使用selenium或API
"""
import requests
import json
import time
import re
from datetime import datetime
from typing import List, Dict
import random
from urllib.parse import quote


class XiaohongshuSpider:
    def __init__(self, debug: bool = False, cookie_file: str = 'xhs_cookies.pkl'):
        """
        初始化爬虫
        :param debug: 是否开启调试模式
        :param cookie_file: Cookie保存文件路径
        """
        self.debug = debug
        self.cookie_file = cookie_file
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.xiaohongshu.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://www.xiaohongshu.com'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.base_url = "https://edith.xiaohongshu.com"
    
    def search_notes(self, keyword: str = "华为", page: int = 1, page_size: int = 20) -> List[Dict]:
        """
        搜索笔记
        注意：小红书API需要登录token，这里提供基础框架
        """
        # 小红书搜索API（需要登录）
        url = f"{self.base_url}/api/sns/web/v1/search/notes"
        params = {
            'keyword': keyword,
            'page': page,
            'page_size': page_size,
            'sort': 'general',  # 综合排序
            'note_type': 0  # 0-全部，1-视频，2-图文
        }
        
        # 注意：实际使用时需要添加cookie或token
        # cookies = {
        #     'web_session': 'your_session_token',
        #     # 其他必要的cookies
        # }
        # self.session.cookies.update(cookies)
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('success', False):
                notes = []
                for item in data.get('data', {}).get('items', []):
                    note_info = self._parse_note_info(item)
                    if note_info:
                        notes.append(note_info)
                return notes
            else:
                print(f"搜索失败: {data.get('msg', '未知错误')}")
                return []
        except Exception as e:
            print(f"搜索笔记时出错: {e}")
            print("提示：小红书需要登录token，请使用selenium方式或配置cookie")
            return []
    
    def _parse_note_info(self, item: Dict) -> Dict:
        """
        解析笔记信息
        """
        try:
            note_card = item.get('note_card', {})
            if not note_card:
                return None
            
            note_id = note_card.get('note_id', '')
            user_info = note_card.get('user', {})
            
            # 解析时间戳
            time_ms = note_card.get('time', 0)
            publish_date = datetime.fromtimestamp(time_ms / 1000).strftime('%Y-%m-%d %H:%M:%S') if time_ms else ''
            
            # 解析标签
            tag_list = note_card.get('tag_list', [])
            tags = ','.join([tag.get('name', '') for tag in tag_list if isinstance(tag, dict)])
            
            # 获取互动数据
            interact_info = note_card.get('interact_info', {})
            
            return {
                'Post_ID': note_id,
                'Platform': 'XiaoHongShu',
                'Publish_Date': publish_date,
                'Post_URL': f"https://www.xiaohongshu.com/explore/{note_id}",
                'Author_ID': str(user_info.get('user_id', '')),
                'Author_Name': user_info.get('nickname', ''),
                'Title': note_card.get('title', ''),
                'Content': note_card.get('desc', ''),
                'Tags': tags,
                'Like_Count': interact_info.get('liked_count', 0),
                'Comment_Count': interact_info.get('comment_count', 0),
                'Collect_Count': interact_info.get('collected_count', 0),
                'Share_Count': interact_info.get('share_count', 0),
                'View_Count': interact_info.get('viewed_count', 0)
            }
        except Exception as e:
            print(f"解析笔记信息时出错: {e}")
            return None
    
    def crawl_with_selenium(self, keyword: str = "华为", max_pages: int = 10) -> List[Dict]:
        """
        使用Selenium方式爬取（推荐）
        需要安装selenium和webdriver
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            from selenium.common.exceptions import TimeoutException
        except ImportError:
            print("请安装selenium: pip install selenium")
            return []
        
        all_notes = []
        
        # 配置Chrome选项
        chrome_options = Options()
        # 暂时关闭无头模式，便于调试
        # chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-gpu')
        
        driver = None
        try:
            # 尝试使用webdriver-manager自动管理ChromeDriver
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except ImportError:
                # 如果没有webdriver-manager，使用系统PATH中的ChromeDriver
                driver = webdriver.Chrome(options=chrome_options)
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 先访问主页，尝试加载保存的Cookie
            print("正在加载Cookie...")
            driver.get("https://www.xiaohongshu.com")
            time.sleep(2)
            
            # 尝试加载保存的Cookie
            cookies_loaded = self._load_cookies(driver)
            if cookies_loaded:
                print("✓ Cookie加载成功，刷新页面...")
                driver.refresh()
                time.sleep(2)
            else:
                print("未找到保存的Cookie，需要手动登录")
            
            # 访问搜索页面
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}"
            print(f"正在访问: {search_url}")
            driver.get(search_url)
            time.sleep(3)
            
            # 检查是否需要登录
            need_login = False
            try:
                # 检查是否有登录提示或登录按钮
                login_indicators = [
                    ".login-container",
                    "[class*='login']",
                    ".login-btn",
                    "button:contains('登录')",
                    "a[href*='login']"
                ]
                for indicator in login_indicators:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, indicator)
                        if elements:
                            need_login = True
                            break
                    except:
                        continue
                
                # 检查是否能看到搜索结果（如果没有结果可能是需要登录）
                try:
                    note_elements = driver.find_elements(By.CSS_SELECTOR, ".note-item, [class*='note']")
                    if not note_elements:
                        # 检查是否有"请登录"提示
                        page_text = driver.page_source
                        if '登录' in page_text or 'login' in page_text.lower():
                            need_login = True
                except:
                    pass
                
                if need_login:
                    print("\n" + "="*60)
                    print("⚠️  检测到需要登录！")
                    print("="*60)
                    print("请在浏览器中手动登录账号")
                    print("登录步骤：")
                    print("  1. 在打开的浏览器窗口中点击登录按钮")
                    print("  2. 输入你的小红书账号和密码")
                    print("  3. 完成登录后，爬虫将自动继续...")
                    print("="*60)
                    print("等待60秒，请完成登录...")
                    
                    # 等待用户登录
                    for i in range(60, 0, -10):
                        print(f"  还剩 {i} 秒...", end='\r')
                        time.sleep(10)
                    print("\n")
                    
                    # 登录后刷新页面
                    driver.refresh()
                    time.sleep(3)
                    
                    # 保存Cookie
                    self._save_cookies(driver)
                    print("✓ Cookie已保存，下次运行可自动登录")
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 检查登录状态时出错: {e}")
            
            # 尝试关闭登录弹窗（如果有）
            try:
                close_selectors = [
                    ".close-btn", 
                    ".login-close", 
                    "[class*='close']",
                    "[aria-label*='关闭']",
                    "[aria-label*='Close']"
                ]
                for selector in close_selectors:
                    try:
                        close_btn = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        close_btn.click()
                        time.sleep(1)
                        break
                    except:
                        continue
            except:
                pass
            
            # 等待页面加载 - 使用更通用的选择器
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".feeds-page, .note-item, [class*='note'], [class*='feed']"))
                )
            except TimeoutException:
                print("页面加载超时，尝试继续...")
                time.sleep(3)
            
            # 滚动加载更多
            for page in range(max_pages):
                print(f"正在爬取小红书第 {page + 1} 页...")
                
                # 滚动页面
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # 获取笔记元素 - 使用多种选择器尝试
                note_elements = []
                selectors = [
                    ".note-item",
                    "[class*='note']",
                    "[class*='feed']",
                    ".feeds-page > div",
                    "a[href*='/explore/']"
                ]
                for selector in selectors:
                    note_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if note_elements:
                        print(f"  使用选择器 '{selector}' 找到 {len(note_elements)} 个元素")
                        break
                
                page_notes = []
                for i, element in enumerate(note_elements):
                    try:
                        if self.debug:
                            print(f"\n[DEBUG] 正在解析第 {i+1}/{len(note_elements)} 个笔记元素...")
                        note_info = self._parse_selenium_element(element, driver)
                        if note_info and note_info.get('Post_ID'):
                            # 检查是否已存在
                            existing_ids = [n['Post_ID'] for n in all_notes]
                            if note_info['Post_ID'] not in existing_ids:
                                all_notes.append(note_info)
                                page_notes.append(note_info)
                                if self.debug:
                                    print(f"[DEBUG] ✓ 成功解析笔记 {note_info['Post_ID']}: 点赞={note_info.get('Like_Count')}, 评论={note_info.get('Comment_Count')}, 收藏={note_info.get('Collect_Count')}")
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG] ✗ 解析笔记元素失败: {e}")
                        continue
                
                print(f"第 {page + 1} 页成功解析 {len(page_notes)} 条数据（累计 {len(all_notes)} 条）")
                
                print(f"第 {page + 1} 页获取到 {len(note_elements)} 条数据")
                time.sleep(random.uniform(2, 3))
            
        except Exception as e:
            print(f"Selenium爬取时出错: {e}")
        finally:
            if driver:
                driver.quit()
        
        print(f"小红书爬取完成，共获取 {len(all_notes)} 条数据")
        
        # 爬取完成后再次保存Cookie（确保是最新的）
        if driver:
            try:
                self._save_cookies(driver)
                if self.debug:
                    print("[DEBUG] Cookie已更新保存")
            except:
                pass
        
        return all_notes
    
    def _parse_selenium_element(self, element, driver=None) -> Dict:
        """
        解析Selenium获取的元素
        """
        try:
            if self.debug:
                print(f"\n[DEBUG] 开始解析小红书元素...")
            
            # 获取链接和笔记ID
            href = ''
            note_id = ''
            
            # 尝试多种方式获取链接
            try:
                link_elem = element.find_element(By.TAG_NAME, "a")
                href = link_elem.get_attribute('href')
            except:
                href = element.get_attribute('href')
            
            # 从链接中提取笔记ID
            if href:
                match = re.search(r'/explore/([a-f0-9]+)', href)
                if match:
                    note_id = match.group(1)
                else:
                    # 如果没有找到，使用链接的一部分作为ID
                    note_id = href.split('/')[-1] or str(hash(href))[:16]
            
            # 如果没有ID，生成一个基于元素位置的ID
            if not note_id:
                note_id = f"xhs_{hash(str(element.location))}"
            
            # 获取标题 - 使用更通用的方法
            title = ''
            # 先尝试从链接元素获取
            try:
                link_elem = element.find_element(By.TAG_NAME, "a")
                if link_elem:
                    title = link_elem.text.strip()
            except:
                pass
            
            # 如果还没有，尝试多种选择器
            if not title:
                title_selectors = [
                    ".title", 
                    "[class*='title']", 
                    "[class*='Title']",
                    "h3", 
                    "h2",
                    "a[href*='/explore/']",
                    ".note-item-title",
                    "[data-v-]"
                ]
                for selector in title_selectors:
                    try:
                        title_elem = element.find_element(By.CSS_SELECTOR, selector)
                        title = title_elem.text.strip()
                        if title and len(title) > 3:  # 确保标题有意义
                            break
                    except:
                        continue
            
            # 如果还是没有，尝试从整个元素的文本中提取（取第一行，跳过数字和时间）
            if not title:
                try:
                    all_text = element.text.strip()
                    lines = all_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        # 跳过纯数字、时间、点赞数等，但保留可能的标题
                        if (line and len(line) > 3 and 
                            not line.isdigit() and 
                            '赞' not in line and 
                            '收藏' not in line and
                            '评论' not in line and
                            not re.match(r'^\d+\.?\d*[万]?$', line) and
                            not re.match(r'^\d+分钟前$', line) and
                            not re.match(r'^\d+小时前$', line)):
                            title = line
                            break
                except:
                    pass
            
            # 如果还是没有标题，至少使用一个默认值，避免被过滤
            if not title:
                title = "小红书笔记"  # 临时标题，后续可以通过URL获取
            
            # 获取作者信息 - 使用更通用的方法
            author_name = ''
            author_selectors = [
                ".author", 
                "[class*='author']", 
                "[class*='user']", 
                "[class*='User']",
                ".nickname",
                "[class*='nickname']",
                "[class*='Nickname']",
                ".username",
                "[data-v-]"
            ]
            for selector in author_selectors:
                try:
                    author_elem = element.find_element(By.CSS_SELECTOR, selector)
                    author_name = author_elem.text.strip()
                    if author_name and len(author_name) > 0:
                        break
                except:
                    continue
            
            # 如果还没有，尝试从文本中提取（通常在标题后面）
            if not author_name:
                try:
                    all_text = element.text.strip()
                    lines = all_text.split('\n')
                    # 通常作者名在标题后面
                    found_title = False
                    for line in lines:
                        line = line.strip()
                        if found_title and line and not line.isdigit() and '赞' not in line and '评论' not in line:
                            author_name = line
                            break
                        if title and title in line:
                            found_title = True
                except:
                    pass
            
            # 获取互动数据 - 使用多种方法
            like_count = 0
            comment_count = 0
            collect_count = 0
            share_count = 0
            view_count = 0
            
            if self.debug:
                print(f"[DEBUG] 开始提取互动数据...")
            
            # 方法0: 优先从页面全局数据中提取（最高效，类似抖音的方法）
            if driver:
                try:
                    # 从window对象中提取数据
                    scripts = [
                        "return window.__INITIAL_STATE__;",
                        "return window.__REDUX_STATE__;",
                        "return window._SSR_HYDRATED_DATA;",
                        "return window.__UNIVERSAL_DATA_FOR_HYDRATION__;",
                        "return window.__RENDER_DATA__;",
                        "return window.pageData;",
                        "return window.noteData;"
                    ]
                    for script in scripts:
                        try:
                            data = driver.execute_script(script)
                            if data:
                                # 递归搜索笔记数据
                                note_data = self._find_note_data_in_json(data, note_id)
                                if note_data:
                                    like_count = note_data.get('like_count', like_count) or like_count
                                    comment_count = note_data.get('comment_count', comment_count) or comment_count
                                    collect_count = note_data.get('collect_count', collect_count) or collect_count
                                    share_count = note_data.get('share_count', share_count) or share_count
                                    view_count = note_data.get('view_count', view_count) or view_count
                                    if self.debug and (like_count or comment_count or collect_count):
                                        print(f"[DEBUG] ✓ 从window对象提取到互动数据")
                                    break
                        except:
                            continue
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] 从window对象提取失败: {e}")
            
            # 方法1: 从元素文本中提取
            try:
                text = element.text
                if self.debug:
                    print(f"[DEBUG] 元素文本: {text[:200]}")
                
                # 解析点赞数 - 多种模式
                like_patterns = [
                    r'(\d+\.?\d*)[万]?赞',
                    r'(\d+\.?\d*)[万]?点赞',
                    r'点赞[：:]\s*(\d+\.?\d*)[万]?',
                    r'(\d+\.?\d*)[万]?w?\s*赞',
                    r'❤\s*(\d+\.?\d*)[万]?',
                    r'(\d+\.?\d*)[万]?\s*❤'
                ]
                for pattern in like_patterns:
                    like_match = re.search(pattern, text, re.IGNORECASE)
                    if like_match:
                        like_count = self._parse_count(like_match)
                        if self.debug:
                            print(f"[DEBUG] ✓ 点赞数: {like_count} (模式: {pattern})")
                        break
                
                # 解析评论数 - 多种模式
                comment_patterns = [
                    r'(\d+\.?\d*)[万]?评论',
                    r'(\d+\.?\d*)[万]?条评论',
                    r'评论[：:]\s*(\d+\.?\d*)[万]?',
                    r'(\d+\.?\d*)[万]?w?\s*评论',
                    r'💬\s*(\d+\.?\d*)[万]?',
                    r'(\d+\.?\d*)[万]?\s*💬'
                ]
                for pattern in comment_patterns:
                    comment_match = re.search(pattern, text, re.IGNORECASE)
                    if comment_match:
                        comment_count = self._parse_count(comment_match)
                        if self.debug:
                            print(f"[DEBUG] ✓ 评论数: {comment_count} (模式: {pattern})")
                        break
                
                # 解析收藏数 - 多种模式
                collect_patterns = [
                    r'(\d+\.?\d*)[万]?收藏',
                    r'(\d+\.?\d*)[万]?次收藏',
                    r'收藏[：:]\s*(\d+\.?\d*)[万]?',
                    r'(\d+\.?\d*)[万]?w?\s*收藏',
                    r'⭐\s*(\d+\.?\d*)[万]?',
                    r'(\d+\.?\d*)[万]?\s*⭐',
                    r'🔖\s*(\d+\.?\d*)[万]?'
                ]
                for pattern in collect_patterns:
                    collect_match = re.search(pattern, text, re.IGNORECASE)
                    if collect_match:
                        collect_count = self._parse_count(collect_match)
                        if self.debug:
                            print(f"[DEBUG] ✓ 收藏数: {collect_count} (模式: {pattern})")
                        break
                
                # 解析分享数（改进以匹配"万"单位）
                share_patterns = [
                    r'(\d+\.?\d*)[万w]?分享',
                    r'(\d+\.?\d*)[万w]?次分享',
                    r'分享[：:]\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*分享',
                    r'(\d+\.?\d*)\s*万\s*分享',
                    r'转发[：:]\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?转发'
                ]
                for pattern in share_patterns:
                    share_match = re.search(pattern, text, re.IGNORECASE)
                    if share_match:
                        share_count = self._parse_count(share_match)
                        if self.debug:
                            print(f"[DEBUG] ✓ 分享数: {share_count} (模式: {pattern})")
                        break
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 从文本提取失败: {e}")
                pass
            
            # 方法2: 尝试从特定的CSS选择器中提取
            try:
                # 尝试查找点赞按钮或显示点赞数的元素
                like_selectors = [
                    "[class*='like']",
                    "[class*='Like']",
                    "[class*='点赞']",
                    ".like-count",
                    "[data-like-count]"
                ]
                for selector in like_selectors:
                    try:
                        like_elem = element.find_element(By.CSS_SELECTOR, selector)
                        like_text = like_elem.text.strip()
                        if like_text and not like_count:
                            like_match = re.search(r'(\d+\.?\d*)[万]?', like_text)
                            if like_match:
                                like_count = self._parse_count(like_match)
                                if self.debug:
                                    print(f"[DEBUG] ✓ 从选择器 '{selector}' 获取点赞数: {like_count}")
                                break
                    except:
                        continue
                
                # 尝试查找评论数
                comment_selectors = [
                    "[class*='comment']",
                    "[class*='Comment']",
                    "[class*='评论']",
                    ".comment-count",
                    "[data-comment-count]"
                ]
                for selector in comment_selectors:
                    try:
                        comment_elem = element.find_element(By.CSS_SELECTOR, selector)
                        comment_text = comment_elem.text.strip()
                        if comment_text and not comment_count:
                            comment_match = re.search(r'(\d+\.?\d*)[万]?', comment_text)
                            if comment_match:
                                comment_count = self._parse_count(comment_match)
                                if self.debug:
                                    print(f"[DEBUG] ✓ 从选择器 '{selector}' 获取评论数: {comment_count}")
                                break
                    except:
                        continue
                
                # 尝试查找收藏数
                collect_selectors = [
                    "[class*='collect']",
                    "[class*='Collect']",
                    "[class*='收藏']",
                    ".collect-count",
                    "[data-collect-count]"
                ]
                for selector in collect_selectors:
                    try:
                        collect_elem = element.find_element(By.CSS_SELECTOR, selector)
                        collect_text = collect_elem.text.strip()
                        if collect_text and not collect_count:
                            collect_match = re.search(r'(\d+\.?\d*)[万]?', collect_text)
                            if collect_match:
                                collect_count = self._parse_count(collect_match)
                                if self.debug:
                                    print(f"[DEBUG] ✓ 从选择器 '{selector}' 获取收藏数: {collect_count}")
                                break
                    except:
                        continue
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 从选择器提取失败: {e}")
                pass
            
            # 方法3: 从页面源码中提取JSON数据（小红书通常会在页面中嵌入JSON）
            if driver and (not like_count or not comment_count or not collect_count):
                try:
                    page_source = driver.page_source
                    
                    # 方法3.1: 从页面源码中提取带"万"单位的数字
                    if not like_count:
                        wan_like_patterns = [
                            r'(\d+\.?\d*)\s*万\s*赞',
                            r'(\d+\.?\d*)\s*万\s*点赞',
                            r'(\d+\.?\d*)[万w]\s*赞'
                        ]
                        for pattern in wan_like_patterns:
                            matches = re.findall(pattern, page_source)
                            if matches:
                                try:
                                    count = float(matches[0]) * 10000
                                    like_count = int(count)
                                    if self.debug:
                                        print(f"[DEBUG] ✓ 从页面源码提取点赞数（万单位）: {like_count}")
                                    break
                                except:
                                    continue
                    
                    if not comment_count:
                        wan_comment_patterns = [
                            r'(\d+\.?\d*)\s*万\s*评论',
                            r'(\d+\.?\d*)[万w]\s*评论'
                        ]
                        for pattern in wan_comment_patterns:
                            matches = re.findall(pattern, page_source)
                            if matches:
                                try:
                                    count = float(matches[0]) * 10000
                                    comment_count = int(count)
                                    if self.debug:
                                        print(f"[DEBUG] ✓ 从页面源码提取评论数（万单位）: {comment_count}")
                                    break
                                except:
                                    continue
                    
                    if not collect_count:
                        wan_collect_patterns = [
                            r'(\d+\.?\d*)\s*万\s*收藏',
                            r'(\d+\.?\d*)[万w]\s*收藏'
                        ]
                        for pattern in wan_collect_patterns:
                            matches = re.findall(pattern, page_source)
                            if matches:
                                try:
                                    count = float(matches[0]) * 10000
                                    collect_count = int(count)
                                    if self.debug:
                                        print(f"[DEBUG] ✓ 从页面源码提取收藏数（万单位）: {collect_count}")
                                    break
                                except:
                                    continue
                    
                    # 方法3.2: 从JSON数据中提取（小红书通常会在script标签中嵌入JSON）
                    json_patterns = [
                        r'"liked_count":\s*(\d+)',
                        r'"likeCount":\s*(\d+)',
                        r'"likedCount":\s*(\d+)',
                        r'"comment_count":\s*(\d+)',
                        r'"commentCount":\s*(\d+)',
                        r'"collected_count":\s*(\d+)',
                        r'"collectCount":\s*(\d+)',
                        r'"collectedCount":\s*(\d+)',
                        r'"share_count":\s*(\d+)',
                        r'"shareCount":\s*(\d+)',
                        r'"viewed_count":\s*(\d+)',
                        r'"viewCount":\s*(\d+)'
                    ]
                    
                    # 在笔记ID附近查找数据（更准确）
                    if note_id:
                        # 在包含note_id的区域查找
                        note_context_pattern = rf'{note_id}.*?{{.*?}}'
                        context_matches = re.finditer(note_context_pattern, page_source, re.DOTALL)
                        for context_match in context_matches:
                            context = context_match.group(0)
                            
                            # 在上下文中查找数据
                            if not like_count:
                                like_matches = re.findall(r'"liked_count":\s*(\d+)|"likeCount":\s*(\d+)|"likedCount":\s*(\d+)', context)
                                if like_matches:
                                    for match in like_matches:
                                        count = int([x for x in match if x][0])
                                        if count > 0:
                                            like_count = count
                                            if self.debug:
                                                print(f"[DEBUG] ✓ 从JSON获取点赞数: {like_count}")
                                            break
                            
                            if not comment_count:
                                comment_matches = re.findall(r'"comment_count":\s*(\d+)|"commentCount":\s*(\d+)', context)
                                if comment_matches:
                                    for match in comment_matches:
                                        count = int([x for x in match if x][0])
                                        if count > 0:
                                            comment_count = count
                                            if self.debug:
                                                print(f"[DEBUG] ✓ 从JSON获取评论数: {comment_count}")
                                            break
                            
                            if not collect_count:
                                collect_matches = re.findall(r'"collected_count":\s*(\d+)|"collectCount":\s*(\d+)|"collectedCount":\s*(\d+)', context)
                                if collect_matches:
                                    for match in collect_matches:
                                        count = int([x for x in match if x][0])
                                        if count > 0:
                                            collect_count = count
                                            if self.debug:
                                                print(f"[DEBUG] ✓ 从JSON获取收藏数: {collect_count}")
                                            break
                            
                            if not share_count:
                                share_matches = re.findall(r'"share_count":\s*(\d+)|"shareCount":\s*(\d+)', context)
                                if share_matches:
                                    for match in share_matches:
                                        count = int([x for x in match if x][0])
                                        if count > 0:
                                            share_count = count
                                            if self.debug:
                                                print(f"[DEBUG] ✓ 从JSON获取分享数: {share_count}")
                                            break
                            
                            if not view_count:
                                view_matches = re.findall(r'"viewed_count":\s*(\d+)|"viewCount":\s*(\d+)', context)
                                if view_matches:
                                    for match in view_matches:
                                        count = int([x for x in match if x][0])
                                        if count > 0:
                                            view_count = count
                                            if self.debug:
                                                print(f"[DEBUG] ✓ 从JSON获取浏览数: {view_count}")
                                            break
                            
                            # 如果找到了一些数据，就停止搜索
                            if like_count or comment_count or collect_count:
                                break
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] 从页面源码提取JSON失败: {e}")
                    pass
            
            # 方法4: 强制访问详情页获取（小红书搜索页面通常不显示互动数据）
            # 小红书搜索页面通常不显示点赞、评论、收藏等数据，必须访问详情页
            # 强制访问详情页，因为搜索页面几乎不可能有完整数据
            if href and note_id and driver:
                if self.debug:
                    print(f"[DEBUG] 强制访问详情页获取完整互动数据: {href}")
                detail_data = self._get_note_detail_from_page(driver, href, note_id)
                if detail_data:
                    # 优先使用详情页的数据（更准确），覆盖之前提取的数据
                    like_count = detail_data.get('like_count', 0) or like_count
                    comment_count = detail_data.get('comment_count', 0) or comment_count
                    collect_count = detail_data.get('collect_count', 0) or collect_count
                    share_count = detail_data.get('share_count', 0) or share_count
                    view_count = detail_data.get('view_count', 0) or view_count
                    if self.debug:
                        print(f"[DEBUG] ✓ 从详情页获取数据 - 点赞: {like_count}, 评论: {comment_count}, 收藏: {collect_count}, 分享: {share_count}, 浏览: {view_count}")
                else:
                    if self.debug:
                        print(f"[DEBUG] ⚠ 详情页访问失败或未提取到数据")
            
            if self.debug:
                print(f"[DEBUG] 最终数据 - 点赞: {like_count}, 评论: {comment_count}, 收藏: {collect_count}, 分享: {share_count}")
            
            # 检查标题是否包含关键词（放宽条件，如果标题是默认值则不过滤）
            title_lower = title.lower() if title else ''
            if title != "小红书笔记":  # 只有真实标题才进行关键词过滤
                keywords = ['华为', 'huawei', '鸿蒙', 'harmony', 'mate', 'p系列', 'nova', 'honor']
                matched_keywords = [kw for kw in keywords if kw in title_lower]
                if not matched_keywords:
                    if self.debug:
                        print(f"[DEBUG] ✗ 标题不包含关键词: {title[:50]}")
                    return None
                if self.debug:
                    print(f"[DEBUG] ✓ 关键词匹配: {matched_keywords}, 标题: {title[:50]}")
            else:
                if self.debug:
                    print(f"[DEBUG] ⚠ 使用默认标题，跳过关键词过滤")
            
            return {
                'Post_ID': note_id,
                'Platform': 'XiaoHongShu',
                'Publish_Date': '',
                'Post_URL': href or f"https://www.xiaohongshu.com/explore/{note_id}",
                'Author_ID': '',
                'Author_Name': author_name,
                'Title': title,
                'Content': title,  # 搜索页面通常只有标题
                'Tags': '',
                'Like_Count': like_count,
                'Comment_Count': comment_count,
                'Collect_Count': collect_count,
                'Share_Count': share_count,
                'View_Count': view_count
            }
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] ✗ 解析出错: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def _get_note_detail_from_page(self, driver, url: str, note_id: str) -> Dict:
        """
        访问笔记详情页获取互动数据
        """
        try:
            if self.debug:
                print(f"[DEBUG] 访问详情页: {url}")
            
            # 在新标签页打开详情页
            original_window = driver.current_window_handle
            driver.execute_script(f"window.open('{url}', '_blank');")
            time.sleep(2)
            
            # 切换到新标签页
            windows = driver.window_handles
            if len(windows) > 1:
                driver.switch_to.window(windows[-1])
                time.sleep(5)  # 等待页面完全加载，增加等待时间
                
                # 等待页面内容加载
                try:
                    from selenium.webdriver.common.by import By
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except:
                    pass
                
                # 尝试提取互动数据
                detail_data = {}
                try:
                    # 方法1: 从window对象中提取（详情页通常会有完整数据）
                    scripts = [
                            "return window.__INITIAL_STATE__;",
                            "return window.__REDUX_STATE__;",
                            "return window._SSR_HYDRATED_DATA;",
                            "return window.__UNIVERSAL_DATA_FOR_HYDRATION__;",
                            "return window.noteDetail;",
                            "return window.noteData;",
                            "return window.pageData;",
                            "return window.__NEXT_DATA__;"
                    ]
                    for script in scripts:
                        try:
                            data = driver.execute_script(script)
                            if data:
                                note_data = self._find_note_data_in_json(data, note_id)
                                if note_data:
                                    detail_data.update(note_data)
                                    if self.debug:
                                        print(f"[DEBUG] ✓ 从详情页window对象提取到数据: {note_data}")
                                    # 如果获取到完整数据，就不再尝试其他方法
                                    if detail_data.get('like_count') and detail_data.get('comment_count'):
                                        break
                        except Exception as e:
                            if self.debug:
                                print(f"[DEBUG] window对象提取失败 ({script[:30]}...): {str(e)[:50]}")
                            continue
                    
                    # 方法2: 从script标签中提取JSON
                    if not detail_data or not detail_data.get('like_count'):
                            try:
                                from selenium.webdriver.common.by import By
                                script_elements = driver.find_elements(By.TAG_NAME, "script")
                                for script in script_elements:
                                    try:
                                        script_text = script.get_attribute('innerHTML') or script.get_attribute('textContent')
                                        if not script_text or len(script_text) < 100:
                                            continue
                                        
                                        # 查找包含互动数据的JSON
                                        if 'liked_count' in script_text or 'interact_info' in script_text or 'noteDetail' in script_text:
                                            # 尝试提取JSON对象 - 多种模式
                                            json_patterns = [
                                                r'{"noteDetail"[^}]*?"interact_info"[^}]*?}}',
                                                r'"interact_info"[^}]*?}',
                                                r'{"noteId":"[^"]*"[^}]*?"interact_info"[^}]*?}}',
                                                r'"liked_count":\s*(\d+)[^}]*"comment_count":\s*(\d+)[^}]*"collected_count":\s*(\d+)',
                                            ]
                                            
                                            for json_pattern in json_patterns:
                                                json_match = re.search(json_pattern, script_text, re.DOTALL)
                                                if json_match:
                                                    json_str = json_match.group(0)
                                                    
                                                    # 提取各个字段
                                                    like_match = re.search(r'"liked_count":\s*(\d+)', json_str)
                                                    comment_match = re.search(r'"comment_count":\s*(\d+)', json_str)
                                                    collect_match = re.search(r'"collected_count":\s*(\d+)', json_str)
                                                    share_match = re.search(r'"share_count":\s*(\d+)', json_str)
                                                    view_match = re.search(r'"viewed_count":\s*(\d+)', json_str)
                                                    
                                                    if like_match and not detail_data.get('like_count'):
                                                        detail_data['like_count'] = int(like_match.group(1))
                                                    if comment_match and not detail_data.get('comment_count'):
                                                        detail_data['comment_count'] = int(comment_match.group(1))
                                                    if collect_match and not detail_data.get('collect_count'):
                                                        detail_data['collect_count'] = int(collect_match.group(1))
                                                    if share_match and not detail_data.get('share_count'):
                                                        detail_data['share_count'] = int(share_match.group(1))
                                                    if view_match and not detail_data.get('view_count'):
                                                        detail_data['view_count'] = int(view_match.group(1))
                                                    
                                                    if detail_data and self.debug:
                                                        print(f"[DEBUG] ✓ 从script标签提取到数据: {detail_data}")
                                                    break
                                            
                                            if detail_data.get('like_count'):
                                                break
                                    except Exception as e:
                                        if self.debug:
                                            print(f"[DEBUG] script标签提取失败: {str(e)[:50]}")
                                        continue
                            except Exception as e:
                                if self.debug:
                                    print(f"[DEBUG] 从script标签提取失败: {e}")
                    
                    # 方法3: 从页面元素中提取（小红书详情页通常会在页面上显示这些数据）
                    if not detail_data or not detail_data.get('like_count'):
                            try:
                                from selenium.webdriver.common.by import By
                                
                                # 尝试从页面元素中查找互动数据
                                # 小红书详情页通常会显示点赞、评论、收藏等数据
                                interact_selectors = [
                                    "[class*='like']",
                                    "[class*='comment']",
                                    "[class*='collect']",
                                    "[class*='interact']",
                                    "[class*='stats']",
                                    "[data-v-]"
                                ]
                                
                                for selector in interact_selectors:
                                    try:
                                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                        for elem in elements:
                                            text = elem.text.strip()
                                            if not text:
                                                continue
                                            
                                            # 从文本中提取数字
                                            if '赞' in text or 'like' in text.lower():
                                                match = re.search(r'(\d+\.?\d*)[万w]?', text)
                                                if match and not detail_data.get('like_count'):
                                                    detail_data['like_count'] = self._parse_count(match)
                                                    if self.debug:
                                                        print(f"[DEBUG] ✓ 从元素提取点赞数: {detail_data['like_count']}")
                                            
                                            if '评论' in text or 'comment' in text.lower():
                                                match = re.search(r'(\d+\.?\d*)[万w]?', text)
                                                if match and not detail_data.get('comment_count'):
                                                    detail_data['comment_count'] = self._parse_count(match)
                                                    if self.debug:
                                                        print(f"[DEBUG] ✓ 从元素提取评论数: {detail_data['comment_count']}")
                                            
                                            if '收藏' in text or 'collect' in text.lower():
                                                match = re.search(r'(\d+\.?\d*)[万w]?', text)
                                                if match and not detail_data.get('collect_count'):
                                                    detail_data['collect_count'] = self._parse_count(match)
                                                    if self.debug:
                                                        print(f"[DEBUG] ✓ 从元素提取收藏数: {detail_data['collect_count']}")
                                            
                                            if '分享' in text or 'share' in text.lower():
                                                match = re.search(r'(\d+\.?\d*)[万w]?', text)
                                                if match and not detail_data.get('share_count'):
                                                    detail_data['share_count'] = self._parse_count(match)
                                                    if self.debug:
                                                        print(f"[DEBUG] ✓ 从元素提取分享数: {detail_data['share_count']}")
                                            
                                            # 如果已经找到了所有数据，停止搜索
                                            if detail_data.get('like_count') and detail_data.get('comment_count') and detail_data.get('collect_count'):
                                                break
                                    except:
                                        continue
                            except Exception as e:
                                if self.debug:
                                    print(f"[DEBUG] 从页面元素提取失败: {e}")
                    
                    # 方法4: 从页面源码HTML中提取（最后的手段）
                    if not detail_data or not detail_data.get('like_count'):
                            page_text = driver.page_source
                            
                            # 从页面源码中提取数据
                            patterns = {
                                'like_count': [
                                    r'"liked_count":\s*(\d+)',
                                    r'"likeCount":\s*(\d+)',
                                    r'"likedCount":\s*(\d+)',
                                    r'(\d+\.?\d*)\s*万\s*赞',
                                    r'(\d+\.?\d*)[万w]\s*赞',
                                    r'点赞[：:]\s*(\d+\.?\d*)[万w]?',
                                    r'(\d+\.?\d*)[万w]?赞'
                                ],
                                'comment_count': [
                                    r'"comment_count":\s*(\d+)',
                                    r'"commentCount":\s*(\d+)',
                                    r'(\d+\.?\d*)\s*万\s*评论',
                                    r'(\d+\.?\d*)[万w]\s*评论',
                                    r'评论[：:]\s*(\d+\.?\d*)[万w]?',
                                    r'(\d+\.?\d*)[万w]?评论'
                                ],
                                'collect_count': [
                                    r'"collected_count":\s*(\d+)',
                                    r'"collectCount":\s*(\d+)',
                                    r'"collectedCount":\s*(\d+)',
                                    r'(\d+\.?\d*)\s*万\s*收藏',
                                    r'(\d+\.?\d*)[万w]\s*收藏',
                                    r'收藏[：:]\s*(\d+\.?\d*)[万w]?',
                                    r'(\d+\.?\d*)[万w]?收藏'
                                ],
                                'share_count': [
                                    r'"share_count":\s*(\d+)',
                                    r'"shareCount":\s*(\d+)',
                                    r'(\d+\.?\d*)\s*万\s*分享',
                                    r'(\d+\.?\d*)[万w]\s*分享',
                                    r'分享[：:]\s*(\d+\.?\d*)[万w]?',
                                    r'(\d+\.?\d*)[万w]?分享'
                                ],
                                'view_count': [
                                    r'"viewed_count":\s*(\d+)',
                                    r'"viewCount":\s*(\d+)',
                                    r'(\d+\.?\d*)\s*万\s*浏览',
                                    r'(\d+\.?\d*)[万w]\s*浏览'
                                ]
                            }
                            
                            for key, pattern_list in patterns.items():
                                if detail_data.get(key):  # 如果已经有数据，跳过
                                    continue
                                for pattern in pattern_list:
                                    match = re.search(pattern, page_text)
                                    if match:
                                        try:
                                            # 检查是否包含"万"
                                            full_text = match.group(0)
                                            count_str = match.group(1)
                                            count = float(count_str)
                                            
                                            if '万' in full_text or 'w' in full_text.lower():
                                                count = int(count * 10000)
                                            else:
                                                count = int(count)
                                            
                                            detail_data[key] = count
                                            if self.debug:
                                                print(f"[DEBUG] ✓ 从详情页页面源码提取{key}: {count}")
                                            break
                                        except Exception as e:
                                            if self.debug:
                                                print(f"[DEBUG] 解析{key}失败: {e}")
                                            continue
                    
                    # 如果还是没有数据，打印页面源码的一部分用于调试
                    if not detail_data and self.debug:
                        page_text_sample = driver.page_source[:2000]  # 前2000个字符
                        print(f"[DEBUG] ⚠ 未找到互动数据，页面源码示例:\n{page_text_sample}")
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] 从详情页提取数据失败: {e}")
                
                # 关闭详情页标签，切换回原窗口
                driver.close()
                driver.switch_to.window(original_window)
                time.sleep(1)
                
                return detail_data
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 访问详情页失败: {e}")
            # 确保切换回原窗口
            try:
                driver.switch_to.window(original_window)
            except:
                pass
            return {}
    
    def _save_cookies(self, driver) -> bool:
        """
        保存Cookie到文件
        """
        try:
            import pickle
            cookies = driver.get_cookies()
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            if self.debug:
                print(f"[DEBUG] Cookie已保存到: {self.cookie_file}")
            return True
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 保存Cookie失败: {e}")
            return False
    
    def _load_cookies(self, driver) -> bool:
        """
        从文件加载Cookie
        """
        try:
            import pickle
            import os
            if not os.path.exists(self.cookie_file):
                return False
            
            with open(self.cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            
            # 先访问域名，然后添加Cookie
            driver.get("https://www.xiaohongshu.com")
            time.sleep(1)
            
            for cookie in cookies:
                try:
                    # 移除可能导致问题的字段
                    cookie.pop('domain', None)
                    cookie.pop('expiry', None)
                    driver.add_cookie(cookie)
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] 添加Cookie失败: {e}")
                    continue
            
            if self.debug:
                print(f"[DEBUG] Cookie已加载: {len(cookies)} 个")
            return True
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 加载Cookie失败: {e}")
            return False
    
    def get_comments(self, note_id: str, note_url: str, driver=None, top_n: int = 5) -> List[Dict]:
        """
        获取笔记的热门评论（按点赞数排序，取前N条）
        :param note_id: 笔记ID
        :param note_url: 笔记URL
        :param driver: Selenium driver（必需）
        :param top_n: 获取前N条评论
        :return: 评论列表
        """
        comments = []
        try:
            if not driver:
                if self.debug:
                    print(f"[DEBUG] ⚠ 需要driver来获取小红书评论")
                return comments
            
            if self.debug:
                print(f"[DEBUG] 开始获取小红书评论: {note_url}")
            
            # 访问笔记详情页
            driver.get(note_url)
            time.sleep(5)  # 等待页面加载
            
            # 等待页面内容加载
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass
            
            # 尝试滚动到评论区
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                # 再滚动一点，确保评论区加载
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            except:
                pass
            
            # 方法1: 从window对象中提取评论数据（最准确）
            try:
                scripts = [
                    "return window.__INITIAL_STATE__;",
                    "return window.__REDUX_STATE__;",
                    "return window._SSR_HYDRATED_DATA;",
                    "return window.noteDetail;",
                    "return window.commentsData;",
                    "return window.pageData;"
                ]
                
                for script in scripts:
                    try:
                        data = driver.execute_script(script)
                        if data:
                            # 递归搜索评论数据
                            comment_list = self._find_comments_in_json(data)
                            if comment_list:
                                # 按点赞数排序
                                comment_list.sort(key=lambda x: x.get('like_count', 0), reverse=True)
                                # 取前N条
                                for i, comment_data in enumerate(comment_list[:top_n]):
                                    comments.append({
                                        'Post_ID': note_id,
                                        'Comment_ID': comment_data.get('comment_id', f"{note_id}_comment_{i+1}"),
                                        'Comment_Content': comment_data.get('content', ''),
                                        'Comment_Author': comment_data.get('author', ''),
                                        'Comment_Like_Count': comment_data.get('like_count', 0),
                                        'Comment_Time': comment_data.get('time', ''),
                                        'Platform': 'XiaoHongShu'
                                    })
                                if self.debug:
                                    print(f"[DEBUG] ✓ 从window对象获取到 {len(comments)} 条评论")
                                break
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG] window对象提取评论失败 ({script[:30]}...): {str(e)[:50]}")
                        continue
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 从window对象提取评论失败: {e}")
            
            # 方法2: 从页面源码script标签中提取评论JSON
            if not comments:
                try:
                    from selenium.webdriver.common.by import By
                    page_source = driver.page_source
                    
                    # 查找评论相关的JSON数据
                    comment_patterns = [
                        r'"comments":\s*\[(.*?)\]',
                        r'"commentList":\s*\[(.*?)\]',
                        r'"items":\s*\[(.*?)\]',
                        r'"comment_list":\s*\[(.*?)\]',
                    ]
                    
                    for pattern in comment_patterns:
                        matches = re.finditer(pattern, page_source, re.DOTALL)
                        for match in matches:
                            comments_json_str = match.group(1)
                            if not comments_json_str or len(comments_json_str) < 10:
                                continue
                            
                            # 尝试提取单个评论
                            single_comment_pattern = r'{"comment_id"[^}]*?"content":"([^"]+)"[^}]*?"user_name":"([^"]+)"[^}]*?"liked_count":(\d+)'
                            comment_matches = re.finditer(single_comment_pattern, comments_json_str, re.DOTALL)
                            
                            comment_list = []
                            for cm in comment_matches:
                                try:
                                    comment_list.append({
                                        'comment_id': '',
                                        'content': cm.group(1),
                                        'author': cm.group(2),
                                        'like_count': int(cm.group(3)),
                                        'time': ''
                                    })
                                except:
                                    continue
                            
                            if comment_list:
                                # 按点赞数排序
                                comment_list.sort(key=lambda x: x['like_count'], reverse=True)
                                # 取前N条
                                for i, comment_data in enumerate(comment_list[:top_n]):
                                    comments.append({
                                        'Post_ID': note_id,
                                        'Comment_ID': f"{note_id}_comment_{i+1}",
                                        'Comment_Content': comment_data['content'],
                                        'Comment_Author': comment_data['author'],
                                        'Comment_Like_Count': comment_data['like_count'],
                                        'Comment_Time': comment_data['time'],
                                        'Platform': 'XiaoHongShu'
                                    })
                                if self.debug:
                                    print(f"[DEBUG] ✓ 从JSON获取到 {len(comments)} 条评论")
                                break
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] 从JSON提取评论失败: {e}")
            
            # 方法3: 从页面元素中提取评论（最可靠的方法）
            if not comments:
                try:
                    from selenium.webdriver.common.by import By
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    
                    # 等待评论区域加载
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='comment'], [class*='Comment']"))
                        )
                    except:
                        pass
                    
                    comment_selectors = [
                        ".comment-item",
                        "[class*='comment-item']",
                        "[class*='CommentItem']",
                        "[class*='comment']",
                        "[class*='Comment']",
                        ".note-comment-item",
                        "[data-v-]",
                        "li[class*='comment']"
                    ]
                    
                    comment_elements = []
                    for selector in comment_selectors:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements and len(elements) > 0:
                                comment_elements = elements
                                if self.debug:
                                    print(f"[DEBUG] ✓ 使用选择器 '{selector}' 找到 {len(elements)} 个评论元素")
                                break
                        except:
                            continue
                    
                    if comment_elements:
                        comment_data_list = []
                        for elem in comment_elements[:30]:  # 最多取30条，然后排序
                            try:
                                # 提取评论内容
                                content = ''
                                try:
                                    content_elem = elem.find_element(By.CSS_SELECTOR, "[class*='content'], [class*='text'], p, span")
                                    content = content_elem.text.strip()
                                except:
                                    # 如果找不到特定元素，使用整个元素的文本
                                    content = elem.text.strip()
                                    # 尝试从文本中提取评论内容（排除作者名和点赞数）
                                    lines = content.split('\n')
                                    for line in lines:
                                        line = line.strip()
                                        if line and len(line) > 5 and '赞' not in line and '评论' not in line:
                                            content = line
                                            break
                                
                                # 提取点赞数
                                like_count = 0
                                try:
                                    like_elem = elem.find_elements(By.CSS_SELECTOR, "[class*='like'], [class*='Like'], [class*='点赞']")
                                    if like_elem:
                                        like_text = like_elem[0].text.strip()
                                        like_match = re.search(r'(\d+\.?\d*)[万w]?', like_text)
                                        if like_match:
                                            like_count = self._parse_count(like_match)
                                except:
                                    # 从元素文本中提取
                                    elem_text = elem.text
                                    like_match = re.search(r'(\d+\.?\d*)[万w]?\s*赞', elem_text)
                                    if like_match:
                                        like_count = self._parse_count(like_match)
                                
                                # 提取作者
                                author = ''
                                try:
                                    author_elem = elem.find_elements(By.CSS_SELECTOR, "[class*='author'], [class*='user'], [class*='name'], [class*='nickname']")
                                    if author_elem:
                                        author = author_elem[0].text.strip()
                                        # 过滤掉数字和特殊字符
                                        if author and not author.isdigit() and len(author) < 50:
                                            pass  # 保留
                                        else:
                                            author = ''
                                except:
                                    pass
                                
                                # 如果没有作者，尝试从文本第一行提取
                                if not author:
                                    elem_text = elem.text
                                    lines = elem_text.split('\n')
                                    for line in lines[:3]:  # 只检查前3行
                                        line = line.strip()
                                        if line and not line.isdigit() and '赞' not in line and '评论' not in line and len(line) < 30:
                                            author = line
                                            break
                                
                                if content and len(content) > 3:  # 确保有实际的评论内容
                                    comment_data_list.append({
                                        'content': content[:500],  # 限制长度
                                        'like_count': like_count,
                                        'author': author[:50]  # 限制长度
                                    })
                            except Exception as e:
                                if self.debug:
                                    print(f"[DEBUG] 解析单条评论失败: {e}")
                                continue
                        
                        if comment_data_list:
                            # 按点赞数排序
                            comment_data_list.sort(key=lambda x: x['like_count'], reverse=True)
                            
                            # 取前N条
                            for i, comment_data in enumerate(comment_data_list[:top_n]):
                                comments.append({
                                    'Post_ID': note_id,
                                    'Comment_ID': f"{note_id}_comment_{i+1}",
                                    'Comment_Content': comment_data['content'],
                                    'Comment_Author': comment_data['author'],
                                    'Comment_Like_Count': comment_data['like_count'],
                                    'Comment_Time': '',
                                    'Platform': 'XiaoHongShu'
                                })
                            
                            if self.debug:
                                print(f"[DEBUG] ✓ 从页面元素获取到 {len(comments)} 条小红书评论")
                        else:
                            if self.debug:
                                print(f"[DEBUG] ⚠ 找到了评论元素但无法提取评论内容")
                    else:
                        if self.debug:
                            print(f"[DEBUG] ⚠ 未找到评论元素，可能没有评论或需要登录")
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] 从页面元素提取评论失败: {e}")
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 小红书评论爬取出错: {e}")
                import traceback
                traceback.print_exc()
        
        return comments
    
    def _find_comments_in_json(self, data, path="") -> List[Dict]:
        """
        递归搜索JSON数据中的评论信息
        """
        comments = []
        try:
            if isinstance(data, dict):
                # 检查是否包含评论数据
                if 'comments' in data or 'commentList' in data or 'items' in data:
                    comment_list = data.get('comments') or data.get('commentList') or data.get('items', [])
                    if isinstance(comment_list, list):
                        for comment in comment_list:
                            if isinstance(comment, dict):
                                comment_data = {
                                    'comment_id': str(comment.get('comment_id', comment.get('id', ''))),
                                    'content': comment.get('content', comment.get('text', comment.get('comment', ''))),
                                    'author': comment.get('user_name', comment.get('author', comment.get('nickname', ''))),
                                    'like_count': comment.get('liked_count', comment.get('like_count', comment.get('likeCount', 0))),
                                    'time': comment.get('create_time', comment.get('time', ''))
                                }
                                if comment_data['content']:
                                    comments.append(comment_data)
                
                # 递归搜索
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        nested_comments = self._find_comments_in_json(value, f"{path}.{key}")
                        comments.extend(nested_comments)
            
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, (dict, list)):
                        nested_comments = self._find_comments_in_json(item, f"{path}[{i}]")
                        comments.extend(nested_comments)
        except:
            pass
        
        return comments
    
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
    
    def crawl(self, keyword: str = "华为", max_pages: int = 10, use_selenium: bool = True) -> List[Dict]:
        """
        爬取多页数据
        :param keyword: 搜索关键词
        :param max_pages: 最大爬取页数
        :param use_selenium: 是否使用selenium（推荐）
        :return: 所有笔记数据
        """
        if use_selenium:
            return self.crawl_with_selenium(keyword, max_pages)
        else:
            all_notes = []
            for page in range(1, max_pages + 1):
                print(f"正在爬取小红书第 {page} 页...")
                notes = self.search_notes(keyword, page=page)
                if not notes:
                    break
                all_notes.extend(notes)
                time.sleep(random.uniform(2, 4))
            return all_notes


if __name__ == "__main__":
    spider = XiaohongshuSpider()
    # 测试爬取（使用selenium）
    results = spider.crawl(keyword="华为", max_pages=2, use_selenium=True)
    print(f"\n测试结果: 共获取 {len(results)} 条数据")
    if results:
        print("\n第一条数据示例:")
        print(json.dumps(results[0], ensure_ascii=False, indent=2))

