"""
抖音（Douyin）爬虫
用于爬取华为相关视频数据
注意：抖音有较强的反爬机制，推荐使用selenium
整合了DouYin文件夹中的API功能（搜索、详情、评论）
完整实现了逆向工程功能，包括 a_bogus 签名生成
"""
import requests  # type: ignore
import json
import time
import re
import sys
import os
import base64
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional
import random
from urllib.parse import quote
from os import path
# 尝试导入 execjs 用于生成 a_bogus 签名
# 注意：不修改全局的 subprocess.Popen，避免与 asyncio 冲突
EXECJS_AVAILABLE = False
try:
    import execjs
    EXECJS_AVAILABLE = True
except ImportError:
    EXECJS_AVAILABLE = False


class DouyinSpider:
    def __init__(self, debug: bool = False, cookie_file: str = 'douyin_cookies.pkl', cookie_str: Optional[str] = None):
        """
        初始化爬虫
        :param debug: 是否开启调试模式
        :param cookie_file: Cookie保存文件路径
        :param cookie_str: Cookie字符串（可选，用于API方式）
        """
        self.debug = debug
        self.cookie_file = cookie_file
        self.cookie_str = cookie_str
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyin.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://www.douyin.com'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.base_url = "https://www.douyin.com"
        
        # 初始化逆向工程工具（a_bogus 签名生成）
        self.dy_js = None
        self._init_reverse_engineering()
        
        # 如果提供了Cookie字符串，解析并设置
        if cookie_str:
            self._parse_cookie_str(cookie_str)
    
    def _init_reverse_engineering(self):
        """
        初始化逆向工程工具（加载 dy_ab.js 用于生成 a_bogus 签名）
        """
        if not EXECJS_AVAILABLE:
            if self.debug:
                print("[DEBUG] ⚠ execjs 未安装，a_bogus 签名生成将不可用")
            return
        
        try:
            # 尝试从 DouYin 文件夹加载 dy_ab.js
            basedir = path.dirname(path.abspath(__file__))
            douyin_dir = path.join(basedir, 'DouYin')
            
            # 查找 node_modules 和 dy_ab.js
            node_modules_paths = [
                path.join(douyin_dir, 'node_modules'),
                path.join(basedir, 'node_modules'),
            ]
            
            dy_ab_paths = [
                path.join(douyin_dir, 'static', 'dy_ab.js'),
                path.join(basedir, 'DouYin', 'static', 'dy_ab.js'),
            ]
            
            node_modules = None
            dy_ab_path = None
            
            for nm_path in node_modules_paths:
                if path.exists(nm_path):
                    node_modules = nm_path
                    break
            
            for dy_path in dy_ab_paths:
                if path.exists(dy_path):
                    dy_ab_path = dy_path
                    break
            
            if dy_ab_path:
                # 安全地修改 subprocess.Popen（仅在此处使用，避免与 asyncio 冲突）
                import subprocess
                from functools import partial
                original_popen = subprocess.Popen
                try:
                    # 临时修改 Popen 以支持 encoding 参数（execjs 需要）
                    subprocess.Popen = partial(original_popen, encoding="utf-8")
                    with open(dy_ab_path, 'r', encoding='utf-8') as f:
                        js_code = f.read()
                    
                    # 如果 node_modules 存在，使用它；否则尝试不使用 cwd
                    if node_modules:
                        self.dy_js = execjs.compile(js_code, cwd=node_modules)
                    else:
                        # 尝试不使用 cwd（某些情况下可能仍然工作）
                        try:
                            self.dy_js = execjs.compile(js_code, cwd=node_modules)
                        except:
                            # 如果失败，尝试不使用 cwd
                            self.dy_js = execjs.compile(js_code)
                    
                    if self.debug:
                        print("[DEBUG] ✓ 成功加载 dy_ab.js，a_bogus 签名生成已启用")
                except Exception as compile_error:
                    if self.debug:
                        print(f"[DEBUG] ⚠ 编译 dy_ab.js 失败: {compile_error}")
                        if not node_modules:
                            print(f"[DEBUG]   提示：需要安装 Node.js 依赖，请在 DouYin 文件夹中运行: npm install")
                    self.dy_js = None
                finally:
                    # 恢复原始的 Popen，避免影响其他模块（如 asyncio）
                    subprocess.Popen = original_popen
            else:
                if self.debug:
                    print(f"[DEBUG] ⚠ 未找到 dy_ab.js，a_bogus 签名生成将不可用")
                    print(f"[DEBUG]   请确保 DouYin/static/dy_ab.js 存在")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] ⚠ 初始化逆向工程工具失败: {e}")
                import traceback
                traceback.print_exc()
    
    def _generate_a_bogus(self, query: str, data: str = "") -> Optional[str]:
        """
        生成 a_bogus 签名参数（核心逆向工程功能）
        :param query: URL 参数字符串
        :param data: POST 数据字符串（可选）
        :return: a_bogus 签名值
        """
        if not self.dy_js:
            if self.debug:
                print("[DEBUG] ⚠ dy_js 未初始化，无法生成 a_bogus")
            return None
        
        try:
            a_bogus = self.dy_js.call('get_ab', query, data)
            if self.debug:
                print(f"[DEBUG] ✓ 成功生成 a_bogus: {a_bogus[:20]}...")
            return a_bogus
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] ⚠ 生成 a_bogus 失败: {e}")
            return None
    
    def _generate_msToken(self, randomlength: int = 107) -> str:
        """
        生成 msToken 参数
        :param randomlength: 随机字符串长度
        :return: msToken 值
        """
        random_str = ''
        base_str = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789='
        length = len(base_str) - 1
        for _ in range(randomlength):
            random_str += base_str[random.randint(0, length)]
        return random_str
    
    def _generate_fake_webid(self, random_length: int = 19) -> str:
        """
        生成假的 webid（当无法从页面获取时使用）
        :param random_length: 随机数字长度
        :return: webid 值
        """
        random_str = ''
        base_str = '0123456789'
        length = len(base_str) - 1
        for _ in range(random_length):
            random_str += base_str[random.randint(0, length)]
        return random_str
    
    def _generate_webid(self, url: str = "") -> str:
        """
        生成或获取 webid
        :param url: 参考 URL
        :return: webid 值
        """
        if not url:
            url = "https://www.douyin.com/discover?modal_id=7376449060384935209"
        
        try:
            if self.cookie_str:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                    'Cookie': self.cookie_str,
                    'Referer': 'https://www.douyin.com/',
                }
                response = requests.get(url, headers=headers, verify=False, timeout=10)
                res_text = response.text
                user_unique_id = re.findall(r'"user_unique_id":"([^"]+)"', res_text)
                if user_unique_id:
                    return user_unique_id[0]
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 获取 webid 失败: {e}，使用假的 webid")
        
        return self._generate_fake_webid()
    
    def _generate_csrf_token(self) -> tuple:
        """
        生成 CSRF token
        :return: (csrf_token_1, csrf_token_2)
        """
        if not self.cookie_str:
            return None, None
        
        try:
            headers = {
                'accept': '*/*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'cache-control': 'no-cache',
                'cookie': self.cookie_str,
                'pragma': 'no-cache',
                'referer': 'https://www.douyin.com/?recommend=1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'x-secsdk-csrf-request': '1',
                'x-secsdk-csrf-version': '1.2.22',
            }
            response = requests.head('https://www.douyin.com/service/2/abtest_config/', headers=headers, verify=False, timeout=10)
            if 'X-Ware-Csrf-Token' in response.headers:
                tokens = response.headers['X-Ware-Csrf-Token'].split(',')
                if len(tokens) >= 5:
                    return tokens[1], tokens[4]
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 获取 CSRF token 失败: {e}")
        
        return None, None
    
    def _splice_url(self, params: dict) -> str:
        """
        拼接 URL 参数字符串
        :param params: 参数字典
        :return: 拼接后的参数字符串
        """
        splice_url_str = ''
        for key, value in params.items():
            if value is None:
                value = ''
            splice_url_str += key + '=' + urllib.parse.quote(str(value)) + '&'
        return splice_url_str[:-1]
    
    def _sort_params(self, params: dict) -> dict:
        """
        按照抖音要求的顺序排序参数（用于生成 a_bogus 签名）
        :param params: 参数字典
        :return: 排序后的参数字典
        """
        # 抖音要求的参数顺序（参考 DouYin/builder/params.py）
        order = [
            'device_platform', 'aid', 'channel', 'publish_video_strategy_type', 'source', 'sec_user_id',
            'personal_center_strategy', 'update_version_code', 'pc_client_type', 'version_code', 'version_name',
            'cookie_enabled', 'screen_width', 'screen_height', 'browser_language', 'browser_platform',
            'browser_name', 'browser_version', 'browser_online', 'engine_name', 'engine_version', 'os_name',
            'os_version', 'cpu_core_num', 'device_memory', 'platform', 'downlink', 'effective_type',
            'round_trip_time', 'webid', 'verifyFp', 'fp', 'msToken', 'a_bogus',
            # 其他可能的参数
            'aweme_id', 'search_channel', 'keyword', 'offset', 'count', 'filter_selected',
            'enable_history', 'search_source', 'query_correct_type', 'is_filter_search',
            'from_group_id', 'need_filter_settings', 'list_type'
        ]
        
        # 按照 order 排序的字段
        sorted_params = {}
        for key in order:
            if key in params:
                sorted_params[key] = params[key]
        
        # 不在 order 中的字段（追加到末尾）
        for key, value in params.items():
            if key not in sorted_params:
                sorted_params[key] = value
        
        return sorted_params
    
    def _parse_cookie_str(self, cookie_str: str):
        """
        解析Cookie字符串并设置到session
        """
        try:
            cookies = {}
            for item in cookie_str.split("; "):
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies[key.strip()] = value.strip()
            self.session.cookies.update(cookies)
            if self.debug:
                print(f"[DEBUG] ✓ 已设置 {len(cookies)} 个Cookie")
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 解析Cookie失败: {e}")
    
    def _trans_cookies(self, cookies_str: str) -> dict:
        """
        转换Cookie字符串为字典（从DouYin文件夹提取）
        """
        cookies = {}
        for i in cookies_str.split("; "):
            try:
                if '=' in i:
                    key, value = i.split('=', 1)
                    cookies[key.strip()] = value.strip()
            except:
                continue
        return cookies
    
    def search_videos(self, keyword: str = "华为", cursor: int = 0, count: int = 20) -> List[Dict]:
        """
        搜索视频
        注意：抖音API需要登录token，这里提供基础框架
        """
        url = f"{self.base_url}/aweme/v1/web/general/search/single/"
        params = {
            'device_platform': 'webapp',
            'aid': '6383',
            'channel': 'channel_pc_web',
            'search_channel': 'aweme_general',
            'sort_type': '0',  # 0-综合排序
            'publish_time': '0',  # 0-不限时间
            'keyword': keyword,
            'search_source': 'normal_search',
            'query_correct_type': '1',
            'is_filter_search': '0',
            'from_group_id': '',
            'offset': cursor,
            'count': count
        }
        
        # 注意：实际使用时需要添加cookie或token
        # cookies = {
        #     'sessionid': 'your_session_id',
        #     # 其他必要的cookies
        # }
        # self.session.cookies.update(cookies)
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status_code') == 0:
                videos = []
                for item in data.get('data', []):
                    video_info = self._parse_video_info(item)
                    if video_info:
                        videos.append(video_info)
                return videos
            else:
                print(f"搜索失败: {data.get('status_msg', '未知错误')}")
                return []
        except Exception as e:
            print(f"搜索视频时出错: {e}")
            print("提示：抖音需要登录token，请使用selenium方式或配置cookie")
            return []
    
    def _parse_video_info(self, item: Dict) -> Dict:
        """
        解析视频信息
        """
        try:
            aweme_info = item.get('aweme_info', {})
            if not aweme_info:
                return None
            
            aweme_id = aweme_info.get('aweme_id', '')
            author_info = aweme_info.get('author', {})
            statistics = aweme_info.get('statistics', {})
            
            # 解析时间戳
            create_time = aweme_info.get('create_time', 0)
            publish_date = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S') if create_time else ''
            
            # 解析标签/话题
            text_extra = aweme_info.get('text_extra', [])
            tags = ','.join([
                extra.get('hashtag_name', '') 
                for extra in text_extra 
                if isinstance(extra, dict) and extra.get('hashtag_name')
            ])
            
            return {
                'Post_ID': aweme_id,
                'Platform': 'Douyin',
                'Publish_Date': publish_date,
                'Post_URL': f"https://www.douyin.com/video/{aweme_id}",
                'Author_ID': str(author_info.get('uid', '')),
                'Author_Name': author_info.get('nickname', ''),
                'Title': aweme_info.get('desc', ''),
                'Content': aweme_info.get('desc', ''),
                'Tags': tags,
                'Like_Count': statistics.get('digg_count', 0),
                'Comment_Count': statistics.get('comment_count', 0),
                'Collect_Count': statistics.get('collect_count', 0),
                'Share_Count': statistics.get('share_count', 0),
                'View_Count': statistics.get('play_count', 0)
            }
        except Exception as e:
            print(f"解析视频信息时出错: {e}")
            return None
    
    def crawl_with_selenium(self, keyword: str = "华为", max_scrolls: int = 10) -> List[Dict]:
        """
        使用Selenium方式爬取（推荐）
        需要安装selenium和webdriver
        """
        try:
            from selenium import webdriver  # type: ignore
            from selenium.webdriver.common.by import By  # type: ignore
            from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
            from selenium.webdriver.support import expected_conditions as EC  # type: ignore
            from selenium.webdriver.chrome.options import Options  # type: ignore
            from selenium.common.exceptions import TimeoutException, NoSuchElementException  # type: ignore
        except ImportError:
            print("请安装selenium: pip install selenium")
            return []
        
        all_videos = []
        
        # 配置Chrome选项
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # 可以开启无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--window-size=1920,1080')
        
        driver = None
        try:
            # 尝试使用webdriver-manager自动管理ChromeDriver
            try:
                from selenium.webdriver.chrome.service import Service  # type: ignore
                from webdriver_manager.chrome import ChromeDriverManager  # type: ignore
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except ImportError:
                # 如果没有webdriver-manager，使用系统PATH中的ChromeDriver
                driver = webdriver.Chrome(options=chrome_options)
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 先访问主页，尝试加载保存的Cookie
            print("正在加载Cookie...")
            driver.get("https://www.douyin.com")
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
            search_url = f"https://www.douyin.com/search/{quote(keyword)}?type=video"
            print(f"正在访问: {search_url}")
            driver.get(search_url)
            time.sleep(3)
            
            # 检查是否需要登录（类似小红书的方式）
            need_login = False
            try:
                # 检查是否有登录提示或登录按钮
                login_indicators = [
                    ".dy-account-close",  # 登录弹窗的关闭按钮（存在说明有登录弹窗）
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
                            if self.debug:
                                print(f"[DEBUG] 检测到登录指示器: {indicator}")
                            break
                    except:
                        continue
                
                # 检查是否能看到搜索结果（如果没有结果可能是需要登录）
                try:
                    video_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/video/']")
                    if not video_elements:
                        # 检查是否有"请登录"提示
                        page_text = driver.page_source
                        if '登录' in page_text or 'login' in page_text.lower() or '请登录' in page_text:
                            need_login = True
                            if self.debug:
                                print("[DEBUG] 未找到视频元素，且页面包含登录提示")
                except:
                    pass
                
                if need_login:
                    print("\n" + "="*60)
                    print("⚠️  检测到需要登录！")
                    print("="*60)
                    print("请在浏览器中手动登录账号")
                    print("登录步骤：")
                    print("  1. 在打开的浏览器窗口中点击登录按钮")
                    print("  2. 使用手机扫码或输入账号密码登录")
                    print("  3. 完成登录后，爬虫将自动继续...")
                    print("="*60)
                    print("等待120秒，请充分完成登录（包括扫码、确认等所有步骤）...")
                    print("提示：如果登录过程中出现验证码，请手动完成验证")
                    
                    # 等待用户登录 - 增加到120秒，给用户充分时间
                    for i in range(120, 0, -10):
                        print(f"  还剩 {i} 秒...", end='\r')
                        time.sleep(10)
                    print("\n")
                    print("等待时间结束，开始验证登录状态...")
                    
                    # 登录后刷新页面
                    driver.refresh()
                    time.sleep(5)  # 增加等待时间，确保页面完全加载
                    
                    # 验证登录状态（确认登录成功）
                    login_success = False
                    max_retries = 5  # 增加重试次数，给用户更多时间
                    for retry in range(max_retries):
                        try:
                            # 等待页面稳定
                            time.sleep(3)
                            
                            # 检查是否有视频元素（登录成功应该能看到搜索结果）
                            video_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/video/']")
                            page_text = driver.page_source
                            
                            # 检查是否还有登录提示或登录弹窗
                            has_login_prompt = (
                                '请登录' in page_text or 
                                ('登录' in page_text and len(video_elements) == 0) or
                                '扫码登录' in page_text
                            )
                            
                            # 检查是否还有登录弹窗
                            try:
                                login_popup = driver.find_elements(By.CSS_SELECTOR, ".dy-account-close, .login-container, [class*='login-modal']")
                                if login_popup:
                                    has_login_prompt = True
                            except:
                                pass
                            
                            if video_elements and len(video_elements) >= 3 and not has_login_prompt:
                                login_success = True
                                print(f"✓ 登录验证成功，已检测到 {len(video_elements)} 个视频内容")
                                break
                            else:
                                if retry < max_retries - 1:
                                    remaining = max_retries - retry - 1
                                    print(f"⚠ 登录验证中... 检测到 {len(video_elements) if video_elements else 0} 个视频 (剩余 {remaining} 次验证)")
                                    time.sleep(5)  # 增加等待时间
                                    driver.refresh()
                                    time.sleep(5)  # 增加刷新后等待时间
                        except Exception as e:
                            if self.debug:
                                print(f"[DEBUG] 验证登录状态时出错: {e}")
                            if retry < max_retries - 1:
                                time.sleep(5)
                                try:
                                    driver.refresh()
                                    time.sleep(5)
                                except:
                                    pass
                    
                    if not login_success:
                        print("\n⚠️  警告：登录状态验证失败！")
                        print("   可能的原因：")
                        print("   1. 登录未完成或登录失败")
                        print("   2. 需要完成额外的验证步骤（如验证码）")
                        print("   3. 页面加载时间过长")
                        print("\n   建议：")
                        print("   - 检查浏览器窗口，确认是否已成功登录")
                        print("   - 如果登录窗口还在，请完成所有登录步骤")
                        print("   - 如果已完成登录但验证失败，可以选择继续")
                        print()
                        user_input = input("   是否继续？（可能会影响数据爬取）(y/n): ")
                        if user_input.lower() != 'y':
                            print("已取消爬取")
                            return []
                        else:
                            print("⚠️  继续运行，但请注意数据可能不完整")
                    
                    # 保存Cookie（只有在登录成功或用户确认继续时才保存）
                    self._save_cookies(driver)
                    print("✓ Cookie已保存，下次运行可自动登录")
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 检查登录状态时出错: {e}")
            
            # 尝试关闭登录弹窗（如果有，登录后可能还有残留弹窗）
            try:
                close_selectors = [
                    ".dy-account-close",
                    "[class*='close']",
                    "[class*='Close']",
                    "[aria-label*='关闭']",
                    "[aria-label*='Close']",
                    "button[aria-label*='关闭']"
                ]
                for selector in close_selectors:
                    try:
                        close_btn = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        close_btn.click()
                        time.sleep(1)
                        if self.debug:
                            print(f"[DEBUG] 已关闭弹窗: {selector}")
                        break
                    except:
                        continue
            except:
                pass
            
            # 等待页面内容加载
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='search-result-item'], .video-card, [class*='video']"))
                )
            except TimeoutException:
                print("页面加载超时，尝试继续...")
                time.sleep(3)
            
            # 滚动加载更多
            # 优化：在开始前先提取一次全局数据
            global_data_map = {}
            try:
                global_data_map = self._extract_global_video_data(driver)
                if global_data_map and self.debug:
                    print(f"[DEBUG] ✓ 初始提取到 {len(global_data_map)} 个视频的互动数据")
            except:
                pass
            
            for scroll in range(max_scrolls):
                print(f"正在爬取抖音，滚动第 {scroll + 1} 次...")
                
                # 滚动到页面底部
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                
                # 优化：每次滚动后重新提取全局数据（新加载的视频）
                try:
                    new_global_data = self._extract_global_video_data(driver)
                    global_data_map.update(new_global_data)
                    if new_global_data and self.debug:
                        print(f"[DEBUG] ✓ 滚动后新增 {len(new_global_data)} 个视频的互动数据")
                except:
                    pass
                
                # 获取视频卡片 - 使用多种选择器
                video_cards = []
                selectors = [
                    "[data-e2e='search-result-item']",
                    ".video-card",
                    "[class*='video-item']",
                    "a[href*='/video/']",
                    "[class*='search-result']"
                ]
                
                for selector in selectors:
                    video_cards = driver.find_elements(By.CSS_SELECTOR, selector)
                    if video_cards:
                        print(f"  使用选择器 '{selector}' 找到 {len(video_cards)} 个视频")
                        break
                
                if video_cards:
                    page_videos = []
                    for card in video_cards:
                        try:
                            # 优化：传递全局数据映射，避免重复解析
                            video_info = self._parse_selenium_element(card, driver, global_data_map)
                            if video_info and video_info.get('Post_ID'):
                                existing_ids = [v['Post_ID'] for v in all_videos]
                                if video_info['Post_ID'] not in existing_ids:
                                    all_videos.append(video_info)
                                    page_videos.append(video_info)
                        except Exception as e:
                            if self.debug:
                                print(f"[DEBUG] 解析视频卡片失败: {e}")
                            continue
                    print(f"滚动第 {scroll + 1} 次：新增 {len(page_videos)} 条，累计 {len(all_videos)} 条数据")
                else:
                    print(f"滚动第 {scroll + 1} 次：未找到视频元素")
                time.sleep(random.uniform(2, 3))
            
        except Exception as e:
            print(f"Selenium爬取时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                driver.quit()
        
        print(f"抖音爬取完成，共获取 {len(all_videos)} 条数据")
        
        # 爬取完成后再次保存Cookie（确保是最新的）
        if driver:
            try:
                self._save_cookies(driver)
                if self.debug:
                    print("[DEBUG] Cookie已更新保存")
            except:
                pass
        
        return all_videos
    
    def _extract_global_video_data(self, driver) -> Dict[str, Dict]:
        """
        从页面全局数据中批量提取所有视频的互动数据（高效方法）
        抖音通常会在window对象或script标签中嵌入JSON数据
        """
        global_data_map = {}
        try:
            # 方法1: 从window对象中提取（最常用）
            try:
                # 尝试获取window._SSR_HYDRATED_DATA或类似变量
                scripts = [
                    "return window._SSR_HYDRATED_DATA;",
                    "return window.__INITIAL_STATE__;",
                    "return window.__UNIVERSAL_DATA_FOR_HYDRATION__;",
                    "return window.__RENDER_DATA__;",
                ]
                for script in scripts:
                    try:
                        data = driver.execute_script(script)
                        if data:
                            # 递归搜索视频数据
                            video_data = self._find_video_data_in_json(data)
                            if video_data:
                                global_data_map.update(video_data)
                                if self.debug:
                                    print(f"[DEBUG] ✓ 从window对象提取到 {len(video_data)} 个视频数据")
                                break
                    except:
                        continue
            except:
                pass
            
            # 方法2: 从页面源码中提取所有JSON数据（一次性提取）
            try:
                page_source = driver.page_source
                
                # 优化：使用更灵活的正则表达式，支持字段顺序变化
                # 查找所有包含视频ID和互动数据的JSON对象
                # 模式：包含aweme_id或itemId的JSON对象（字段顺序可能不同）
                
                # 方法1: 精确匹配（字段顺序固定）
                json_patterns = [
                    r'{"aweme_id":"(\d+)".*?"digg_count":(\d+).*?"comment_count":(\d+).*?"play_count":(\d+).*?"share_count":(\d+).*?"collect_count":(\d+)',
                    r'"itemId":"(\d+)".*?"diggCount":(\d+).*?"commentCount":(\d+).*?"playCount":(\d+).*?"shareCount":(\d+).*?"collectCount":(\d+)',
                ]
                
                for pattern in json_patterns:
                    matches = re.finditer(pattern, page_source, re.DOTALL)
                    for match in matches:
                        video_id = match.group(1)
                        if video_id not in global_data_map:  # 避免重复
                            try:
                                global_data_map[video_id] = {
                                    'like_count': int(match.group(2)),
                                    'comment_count': int(match.group(3)),
                                    'view_count': int(match.group(4)),
                                    'share_count': int(match.group(5)),
                                    'collect_count': int(match.group(6))
                                }
                            except:
                                continue
                
                # 方法2: 灵活匹配（字段顺序不固定，更慢但更全面）
                # 查找所有包含aweme_id的JSON块，然后分别提取各个字段
                flexible_pattern = r'{"aweme_id":"(\d+)"[^}]*?}'
                video_blocks = re.finditer(flexible_pattern, page_source, re.DOTALL)
                for block_match in video_blocks:
                    block = block_match.group(0)
                    video_id_match = re.search(r'"aweme_id":"(\d+)"', block)
                    if not video_id_match:
                        continue
                    video_id = video_id_match.group(1)
                    
                    if video_id not in global_data_map:  # 避免重复
                        try:
                            stats = {}
                            # 提取各个字段（顺序不固定）
                            digg_match = re.search(r'"digg_count":(\d+)', block)
                            comment_match = re.search(r'"comment_count":(\d+)', block)
                            play_match = re.search(r'"play_count":(\d+)', block)
                            share_match = re.search(r'"share_count":(\d+)', block)
                            collect_match = re.search(r'"collect_count":(\d+)', block)
                            
                            if digg_match or comment_match or play_match:
                                global_data_map[video_id] = {
                                    'like_count': int(digg_match.group(1)) if digg_match else 0,
                                    'comment_count': int(comment_match.group(1)) if comment_match else 0,
                                    'view_count': int(play_match.group(1)) if play_match else 0,
                                    'share_count': int(share_match.group(1)) if share_match else 0,
                                    'collect_count': int(collect_match.group(1)) if collect_match else 0
                                }
                        except:
                            continue
                
                if global_data_map and self.debug:
                    print(f"[DEBUG] ✓ 从页面源码JSON提取到 {len(global_data_map)} 个视频数据")
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 从页面源码提取失败: {e}")
            
            # 方法3: 从script标签中提取
            try:
                script_elements = driver.find_elements(By.TAG_NAME, "script")
                for script in script_elements:
                    try:
                        script_text = script.get_attribute('innerHTML')
                        if not script_text or len(script_text) < 100:
                            continue
                        
                        # 查找包含视频数据的JSON
                        if 'aweme_id' in script_text or 'itemId' in script_text:
                            # 尝试提取JSON对象
                            json_matches = re.finditer(
                                r'{"aweme_id":"(\d+)".*?"digg_count":(\d+).*?"comment_count":(\d+).*?"play_count":(\d+).*?"share_count":(\d+).*?"collect_count":(\d+)',
                                script_text,
                                re.DOTALL
                            )
                            for match in json_matches:
                                video_id = match.group(1)
                                if video_id not in global_data_map:
                                    try:
                                        global_data_map[video_id] = {
                                            'like_count': int(match.group(2)),
                                            'comment_count': int(match.group(3)),
                                            'view_count': int(match.group(4)),
                                            'share_count': int(match.group(5)),
                                            'collect_count': int(match.group(6))
                                        }
                                    except:
                                        continue
                    except:
                        continue
                
                if global_data_map and self.debug:
                    print(f"[DEBUG] ✓ 从script标签提取到 {len(global_data_map)} 个视频数据")
            except:
                pass
                
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 提取全局数据失败: {e}")
        
        return global_data_map
    
    def _verify_video_data(self, data: Dict, video_id: str, driver) -> bool:
        """
        验证提取的数据是否对应正确的视频ID
        """
        try:
            # 检查当前页面的URL是否包含正确的视频ID
            current_url = driver.current_url
            if video_id not in current_url:
                if self.debug:
                    print(f"[DEBUG] ⚠ 警告：URL中的视频ID不匹配！当前URL: {current_url}, 期望ID: {video_id}")
                return False
            
            # 检查数据是否合理（比如不应该都是0或过大）
            if data.get('like_count', 0) < 0 or data.get('like_count', 0) > 1000000000:
                if self.debug:
                    print(f"[DEBUG] ⚠ 警告：点赞数异常: {data.get('like_count')}")
                return False
            
            return True
        except:
            return True  # 验证失败时不阻止，继续使用数据
    
    def _validate_interaction_data(self, data: Dict, video_id: str) -> bool:
        """
        验证互动数据的合理性（确保数据准确且属于正确的视频）
        :param data: 提取的数据
        :param video_id: 目标视频ID
        :return: 是否验证通过
        """
        try:
            # 检查是否有至少一个有效数据
            has_valid_data = (
                (data.get('like_count', 0) > 0) or
                (data.get('comment_count', 0) > 0) or
                (data.get('view_count', 0) > 0) or
                (data.get('share_count', 0) > 0) or
                (data.get('collect_count', 0) > 0)
            )
            
            if not has_valid_data:
                if self.debug:
                    print(f"[DEBUG] ⚠ 所有互动数据都为0，可能提取失败")
                return False
            
            # 检查数据范围是否合理（避免提取到错误的数据）
            like_count = data.get('like_count', 0)
            comment_count = data.get('comment_count', 0)
            view_count = data.get('view_count', 0)
            share_count = data.get('share_count', 0)
            collect_count = data.get('collect_count', 0)
            
            # 验证数据范围（合理范围）
            if like_count > 1000000000:  # 10亿
                if self.debug:
                    print(f"[DEBUG] ⚠ 点赞数异常大（{like_count}），可能提取错误")
                return False
            
            if comment_count > 100000000:  # 1亿
                if self.debug:
                    print(f"[DEBUG] ⚠ 评论数异常大（{comment_count}），可能提取错误")
                return False
            
            if view_count > 10000000000:  # 100亿
                if self.debug:
                    print(f"[DEBUG] ⚠ 播放数异常大（{view_count}），可能提取错误")
                return False
            
            # 验证数据的合理性（播放数通常 > 点赞数）
            if view_count > 0 and like_count > 0 and view_count < like_count:
                if self.debug:
                    print(f"[DEBUG] ⚠ 数据异常：播放数({view_count})小于点赞数({like_count})，可能提取错误")
                return False
            
            # 验证数据的合理性（评论数通常 <= 播放数）
            if view_count > 0 and comment_count > 0 and comment_count > view_count * 10:
                if self.debug:
                    print(f"[DEBUG] ⚠ 数据异常：评论数({comment_count})远大于播放数({view_count})，可能提取错误")
                return False
            
            return True
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 数据验证出错: {e}")
            return True  # 验证失败时不阻止，继续使用数据
    
    def _find_video_data_in_json(self, data, path="", target_video_id: str = None) -> Dict[str, Dict]:
        """
        递归搜索JSON数据中的视频信息
        :param target_video_id: 目标视频ID（如果提供，只提取该视频的数据）
        """
        video_data = {}
        try:
            if isinstance(data, dict):
                # 检查是否包含视频ID和统计数据
                if 'aweme_id' in data or 'itemId' in data:
                    video_id = str(data.get('aweme_id') or data.get('itemId', ''))
                    
                    # 如果指定了目标视频ID，只提取匹配的数据
                    if target_video_id and video_id != target_video_id:
                        # 继续递归搜索，但不提取此数据
                        pass
                    elif video_id:
                        stats = data.get('statistics', {}) or data.get('stats', {}) or {}
                        
                        # 提取统计数据
                        like_count = stats.get('digg_count', 0) or data.get('digg_count', 0) or 0
                        comment_count = stats.get('comment_count', 0) or data.get('comment_count', 0) or 0
                        view_count = stats.get('play_count', 0) or data.get('play_count', 0) or stats.get('view_count', 0) or 0
                        share_count = stats.get('share_count', 0) or data.get('share_count', 0) or 0
                        collect_count = stats.get('collect_count', 0) or data.get('collect_count', 0) or 0
                        
                        # 只有在有有效数据时才添加
                        if like_count > 0 or comment_count > 0 or view_count > 0:
                            video_data[video_id] = {
                                'like_count': like_count,
                                'comment_count': comment_count,
                                'view_count': view_count,
                                'share_count': share_count,
                                'collect_count': collect_count,
                            }
                            
                            if self.debug and target_video_id:
                                print(f"[DEBUG] ✓ 找到目标视频 {target_video_id} 的数据: {video_data[video_id]}")
                
                # 递归搜索
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        nested_data = self._find_video_data_in_json(value, f"{path}.{key}", target_video_id)
                        video_data.update(nested_data)
                        
                        # 如果已经找到目标视频的数据，可以提前返回（优化性能）
                        if target_video_id and target_video_id in video_data:
                            break
            
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, (dict, list)):
                        nested_data = self._find_video_data_in_json(item, f"{path}[{i}]", target_video_id)
                        video_data.update(nested_data)
                        
                        # 如果已经找到目标视频的数据，可以提前返回（优化性能）
                        if target_video_id and target_video_id in video_data:
                            break
        except:
            pass
        
        return video_data
    
    def _parse_selenium_element(self, element, driver, global_data_map: Dict[str, Dict] = None) -> Dict:
        """
        解析Selenium获取的元素
        """
        try:
            if self.debug:
                print(f"\n[DEBUG] 开始解析抖音元素...")
            
            # 获取视频链接 - 尝试多种方式
            href = ''
            try:
                link_element = element.find_element(By.TAG_NAME, "a")
                href = link_element.get_attribute('href')
            except:
                # 如果没有a标签，尝试从元素本身获取href
                href = element.get_attribute('href')
            
            # 从链接中提取视频ID
            video_id = ''
            if href:
                match = re.search(r'/video/(\d+)', href)
                if match:
                    video_id = match.group(1)
            
            if not video_id:
                return None
            
            # 获取标题 - 尝试多种选择器和方法
            title = ''
            # 先尝试从链接元素获取
            try:
                link_element = element.find_element(By.TAG_NAME, "a")
                if link_element:
                    title = link_element.text.strip()
            except:
                pass
            
            # 如果还没有，尝试多种选择器
            if not title:
                title_selectors = [
                    "[data-e2e='search-card-title']",
                    "[data-e2e='search-card-desc']",
                    ".title",
                    "[class*='title']",
                    "[class*='Title']",
                    "h3",
                    "h2",
                    "span[title]",
                    "[title]"
                ]
                for selector in title_selectors:
                    try:
                        title_elem = element.find_element(By.CSS_SELECTOR, selector)
                        title = title_elem.text.strip() or title_elem.get_attribute('title')
                        if title and len(title) > 3:
                            break
                    except:
                        continue
            
            # 如果还是没有，尝试从整个元素的文本中提取
            if not title:
                try:
                    all_text = element.text.strip()
                    lines = all_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        # 跳过纯数字、@用户名、点赞数等
                        if (line and len(line) > 3 and 
                            not line.isdigit() and 
                            not line.startswith('@') and
                            '赞' not in line and
                            '评论' not in line and
                            '播放' not in line and
                            not re.match(r'^\d+\.?\d*[万]?', line)):
                            title = line
                            break
                except:
                    pass
            
            # 获取作者信息 - 使用更通用的方法
            author_name = ''
            author_selectors = [
                "[data-e2e='search-card-user-name']",
                "[data-e2e='search-card-author']",
                ".author",
                "[class*='author']",
                "[class*='user']",
                "[class*='User']",
                "[class*='nickname']",
                "a[href*='/user/']"
            ]
            for selector in author_selectors:
                try:
                    author_elem = element.find_element(By.CSS_SELECTOR, selector)
                    author_name = author_elem.text.strip()
                    if author_name and len(author_name) > 0:
                        break
                except:
                    continue
            
            # 如果还没有，尝试从文本中提取（通常以@开头）
            if not author_name:
                try:
                    all_text = element.text.strip()
                    lines = all_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('@'):
                            author_name = line.replace('@', '').strip()
                            break
                except:
                    pass
            
            # 获取互动数据（点赞、评论、收藏等）
            like_count = 0
            comment_count = 0
            view_count = 0
            share_count = 0
            collect_count = 0
            
            # 优化：优先使用全局数据（最快）
            if global_data_map and video_id in global_data_map:
                global_data = global_data_map[video_id]
                like_count = global_data.get('like_count', 0)
                comment_count = global_data.get('comment_count', 0)
                view_count = global_data.get('view_count', 0)
                share_count = global_data.get('share_count', 0)
                collect_count = global_data.get('collect_count', 0)
                if self.debug and (like_count or comment_count or view_count):
                    print(f"[DEBUG] ✓ 从全局数据获取互动数据 - 点赞: {like_count}, 评论: {comment_count}, 播放: {view_count}, 分享: {share_count}, 收藏: {collect_count}")
            
            # 优先使用API方式获取准确的互动数据（如果提供了Cookie）
            # 这是获取真实可靠数据的最佳方式
            if href and video_id and self.cookie_str:
                try:
                    if self.debug:
                        print(f"[DEBUG] 尝试使用API方式获取准确的互动数据（视频ID: {video_id}）...")
                    api_data = self._get_video_info_via_api(href)
                    if api_data:
                        # API返回的数据是最准确的，直接使用
                        like_count = api_data.get('like_count', 0) or like_count
                        comment_count = api_data.get('comment_count', 0) or comment_count
                        view_count = api_data.get('view_count', 0) or view_count
                        share_count = api_data.get('share_count', 0) or share_count
                        collect_count = api_data.get('collect_count', 0) or collect_count
                        
                        # 如果API返回了作者信息，也更新
                        if api_data.get('author_name'):
                            author_name = api_data.get('author_name', author_name)
                        if api_data.get('title'):
                            title = api_data.get('title', title)
                        
                        if self.debug:
                            print(f"[DEBUG] ✓ API方式获取到准确的互动数据 - 点赞: {like_count}, 评论: {comment_count}, 播放: {view_count}, 分享: {share_count}, 收藏: {collect_count}")
                    else:
                        if self.debug:
                            print(f"[DEBUG] API方式获取失败，回退到详情页方式...")
                        # API失败，回退到详情页方式
                        has_complete_data = (like_count > 0 and comment_count > 0 and view_count > 0)
                        if not has_complete_data:
                            detail_data = self._get_video_detail_from_page(driver, href, video_id)
                            if detail_data and self._validate_interaction_data(detail_data, video_id):
                                if detail_data.get('like_count', 0) > 0:
                                    like_count = detail_data.get('like_count', 0)
                                if detail_data.get('comment_count', 0) > 0:
                                    comment_count = detail_data.get('comment_count', 0)
                                if detail_data.get('view_count', 0) > 0:
                                    view_count = detail_data.get('view_count', 0)
                                if detail_data.get('share_count', 0) > 0:
                                    share_count = detail_data.get('share_count', 0)
                                if detail_data.get('collect_count', 0) > 0:
                                    collect_count = detail_data.get('collect_count', 0)
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] API方式获取失败: {e}，回退到详情页方式...")
                    # API失败，回退到详情页方式
                    has_complete_data = (like_count > 0 and comment_count > 0 and view_count > 0)
                    if not has_complete_data:
                        detail_data = self._get_video_detail_from_page(driver, href, video_id)
                        if detail_data and self._validate_interaction_data(detail_data, video_id):
                            if detail_data.get('like_count', 0) > 0:
                                like_count = detail_data.get('like_count', 0)
                            if detail_data.get('comment_count', 0) > 0:
                                comment_count = detail_data.get('comment_count', 0)
                            if detail_data.get('view_count', 0) > 0:
                                view_count = detail_data.get('view_count', 0)
                            if detail_data.get('share_count', 0) > 0:
                                share_count = detail_data.get('share_count', 0)
                            if detail_data.get('collect_count', 0) > 0:
                                collect_count = detail_data.get('collect_count', 0)
            elif href and video_id:
                # 如果没有Cookie，使用详情页方式
                has_complete_data = (like_count > 0 and comment_count > 0 and view_count > 0)
                if not has_complete_data:
                    if self.debug:
                        print(f"[DEBUG] 搜索页面数据不完整（点赞: {like_count}, 评论: {comment_count}, 播放: {view_count}），访问详情页获取数据...")
                    detail_data = self._get_video_detail_from_page(driver, href, video_id)
                    if detail_data and self._validate_interaction_data(detail_data, video_id):
                        if detail_data.get('like_count', 0) > 0:
                            like_count = detail_data.get('like_count', 0)
                        if detail_data.get('comment_count', 0) > 0:
                            comment_count = detail_data.get('comment_count', 0)
                        if detail_data.get('view_count', 0) > 0:
                            view_count = detail_data.get('view_count', 0)
                        if detail_data.get('share_count', 0) > 0:
                            share_count = detail_data.get('share_count', 0)
                        if detail_data.get('collect_count', 0) > 0:
                            collect_count = detail_data.get('collect_count', 0)
            
            if self.debug and not (like_count or comment_count or view_count):
                print(f"[DEBUG] ⚠ 仍未获取到互动数据，尝试从元素文本提取...")
            
            # 方法1: 从元素文本中提取数字
            try:
                text = element.text
                if self.debug:
                    print(f"[DEBUG] 元素文本: {text[:300]}")
                
                # 解析点赞数 - 多种模式（改进以匹配"8.3万"格式）
                like_patterns = [
                    r'(\d+\.?\d*)[万w]?赞',
                    r'(\d+\.?\d*)[万w]?点赞',
                    r'点赞[：:]\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*赞',
                    r'❤\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*❤',
                    r'👍\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*👍',
                    r'(\d+\.?\d*)\s*万\s*赞',  # 匹配"8.3 万 赞"
                    r'(\d+\.?\d*)\s*万',  # 匹配"8.3万"（通用）
                ]
                for pattern in like_patterns:
                    like_match = re.search(pattern, text, re.IGNORECASE)
                    if like_match:
                        like_count = self._parse_count(like_match)
                        if self.debug:
                            print(f"[DEBUG] ✓ 点赞数: {like_count} (模式: {pattern})")
                        break
                
                # 解析评论数
                comment_patterns = [
                    r'(\d+\.?\d*)[万w]?评论',
                    r'(\d+\.?\d*)[万w]?条评论',
                    r'评论[：:]\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*评论',
                    r'💬\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*💬',
                    r'(\d+\.?\d*)\s*万\s*评论'
                ]
                for pattern in comment_patterns:
                    comment_match = re.search(pattern, text, re.IGNORECASE)
                    if comment_match:
                        comment_count = self._parse_count(comment_match)
                        if self.debug:
                            print(f"[DEBUG] ✓ 评论数: {comment_count} (模式: {pattern})")
                        break
                
                # 解析播放量
                view_patterns = [
                    r'(\d+\.?\d*)[万w]?播放',
                    r'(\d+\.?\d*)[万w]?次播放',
                    r'播放[：:]\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*播放',
                    r'👁\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*👁',
                    r'(\d+\.?\d*)\s*万\s*播放'
                ]
                for pattern in view_patterns:
                    view_match = re.search(pattern, text, re.IGNORECASE)
                    if view_match:
                        view_count = self._parse_count(view_match)
                        if self.debug:
                            print(f"[DEBUG] ✓ 播放数: {view_count} (模式: {pattern})")
                        break
                
                # 解析分享数
                share_patterns = [
                    r'(\d+\.?\d*)[万w]?分享',
                    r'(\d+\.?\d*)[万w]?次分享',
                    r'分享[：:]\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*分享',
                    r'📤\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*📤',
                    r'(\d+\.?\d*)\s*万\s*分享'
                ]
                for pattern in share_patterns:
                    share_match = re.search(pattern, text, re.IGNORECASE)
                    if share_match:
                        share_count = self._parse_count(share_match)
                        if self.debug:
                            print(f"[DEBUG] ✓ 分享数: {share_count} (模式: {pattern})")
                        break
                
                # 解析收藏数
                collect_patterns = [
                    r'(\d+\.?\d*)[万w]?收藏',
                    r'(\d+\.?\d*)[万w]?次收藏',
                    r'收藏[：:]\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*收藏',
                    r'⭐\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)[万w]?\s*⭐',
                    r'🔖\s*(\d+\.?\d*)[万w]?',
                    r'(\d+\.?\d*)\s*万\s*收藏'
                ]
                for pattern in collect_patterns:
                    collect_match = re.search(pattern, text, re.IGNORECASE)
                    if collect_match:
                        collect_count = self._parse_count(collect_match)
                        if self.debug:
                            print(f"[DEBUG] ✓ 收藏数: {collect_count} (模式: {pattern})")
                        break
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 从文本提取失败: {e}")
                pass
            
            # 方法2: 尝试从特定的CSS选择器中提取
            try:
                # 尝试查找点赞按钮或显示点赞数的元素
                like_selectors = [
                    "[data-e2e='search-card-like-count']",
                    "[class*='like']",
                    "[class*='Like']",
                    "[class*='点赞']",
                    ".like-count",
                    "[data-like-count]",
                    "[aria-label*='点赞']"
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
                    "[data-e2e='search-card-comment-count']",
                    "[class*='comment']",
                    "[class*='Comment']",
                    "[class*='评论']",
                    ".comment-count",
                    "[data-comment-count]",
                    "[aria-label*='评论']"
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
                
                # 尝试查找播放量
                view_selectors = [
                    "[data-e2e='search-card-play-count']",
                    "[class*='play']",
                    "[class*='Play']",
                    "[class*='播放']",
                    ".play-count",
                    "[data-play-count]",
                    "[aria-label*='播放']"
                ]
                for selector in view_selectors:
                    try:
                        view_elem = element.find_element(By.CSS_SELECTOR, selector)
                        view_text = view_elem.text.strip()
                        if view_text and not view_count:
                            view_match = re.search(r'(\d+\.?\d*)[万]?', view_text)
                            if view_match:
                                view_count = self._parse_count(view_match)
                                if self.debug:
                                    print(f"[DEBUG] ✓ 从选择器 '{selector}' 获取播放数: {view_count}")
                                break
                    except:
                        continue
                
                # 尝试查找收藏数
                collect_selectors = [
                    "[class*='collect']",
                    "[class*='Collect']",
                    "[class*='收藏']",
                    ".collect-count",
                    "[data-collect-count]",
                    "[aria-label*='收藏']"
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
            
            # 方法3: 尝试从元素的HTML属性中提取
            try:
                html = element.get_attribute('outerHTML')
                if html:
                    # 从HTML中查找数据属性
                    data_patterns = [
                        (r'data-like-count="(\d+)"', 'like_count'),
                        (r'data-comment-count="(\d+)"', 'comment_count'),
                        (r'data-play-count="(\d+)"', 'view_count'),
                        (r'data-collect-count="(\d+)"', 'collect_count'),
                        (r'data-share-count="(\d+)"', 'share_count'),
                    ]
                    for pattern, var_name in data_patterns:
                        match = re.search(pattern, html)
                        if match:
                            count = int(match.group(1))
                            if var_name == 'like_count' and not like_count:
                                like_count = count
                            elif var_name == 'comment_count' and not comment_count:
                                comment_count = count
                            elif var_name == 'view_count' and not view_count:
                                view_count = count
                            elif var_name == 'collect_count' and not collect_count:
                                collect_count = count
                            elif var_name == 'share_count' and not share_count:
                                share_count = count
                            if self.debug:
                                print(f"[DEBUG] ✓ 从HTML属性获取{var_name}: {count}")
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 从HTML属性提取失败: {e}")
                pass
            
            # 方法3.5: 从页面源码中提取JSON数据（抖音通常会在页面中嵌入JSON）
            # 优化：只在全局数据中没有时才尝试从页面源码提取
            # 如果缺少任何互动数据，尝试从页面源码提取
            if driver and (not like_count or not comment_count or not view_count or not share_count or not collect_count):
                try:
                    # 优化：使用更高效的正则表达式，一次性提取所有数据
                    page_source = driver.page_source
                    
                    # 方法3.5.1: 优先从JSON中提取（最准确）
                    if video_id:
                        # 在视频ID附近查找JSON数据
                        video_context = re.search(
                            rf'/video/{video_id}.*?{{.*?"digg_count":(\d+).*?"comment_count":(\d+).*?"play_count":(\d+).*?"share_count":(\d+).*?"collect_count":(\d+)',
                            page_source,
                            re.DOTALL
                        )
                        if video_context:
                            try:
                                if not like_count:
                                    like_count = int(video_context.group(1))
                                if not comment_count:
                                    comment_count = int(video_context.group(2))
                                if not view_count:
                                    view_count = int(video_context.group(3))
                                if not share_count:
                                    share_count = int(video_context.group(4))
                                if not collect_count:
                                    collect_count = int(video_context.group(5))
                                if self.debug:
                                    print(f"[DEBUG] ✓ 从JSON上下文提取到完整数据")
                            except:
                                pass
                    
                    # 方法3.5.2: 从页面源码中提取带"万"单位的数字（备用方法）
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
                    
                    if not share_count:
                        wan_share_patterns = [
                            r'(\d+\.?\d*)\s*万\s*分享',
                            r'(\d+\.?\d*)[万w]\s*分享'
                        ]
                        for pattern in wan_share_patterns:
                            matches = re.findall(pattern, page_source)
                            if matches:
                                try:
                                    count = float(matches[0]) * 10000
                                    share_count = int(count)
                                    if self.debug:
                                        print(f"[DEBUG] ✓ 从页面源码提取分享数（万单位）: {share_count}")
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
                    
                    if not view_count:
                        wan_view_patterns = [
                            r'(\d+\.?\d*)\s*万\s*播放',
                            r'(\d+\.?\d*)[万w]\s*播放'
                        ]
                        for pattern in wan_view_patterns:
                            matches = re.findall(pattern, page_source)
                            if matches:
                                try:
                                    count = float(matches[0]) * 10000
                                    view_count = int(count)
                                    if self.debug:
                                        print(f"[DEBUG] ✓ 从页面源码提取播放数（万单位）: {view_count}")
                                    break
                                except:
                                    continue
                    
                    # 尝试提取JSON格式的数据
                    json_patterns = [
                        r'"digg_count":\s*(\d+)',
                        r'"like_count":\s*(\d+)',
                        r'"likeCount":\s*(\d+)',
                        r'"comment_count":\s*(\d+)',
                        r'"commentCount":\s*(\d+)',
                        r'"play_count":\s*(\d+)',
                        r'"view_count":\s*(\d+)',
                        r'"viewCount":\s*(\d+)',
                        r'"share_count":\s*(\d+)',
                        r'"shareCount":\s*(\d+)',
                        r'"collect_count":\s*(\d+)',
                        r'"collectCount":\s*(\d+)',
                    ]
                    
                    # 在视频ID附近查找数据（更准确）
                    if video_id:
                        # 在包含video_id的区域查找
                        video_context_pattern = rf'/video/{video_id}.*?{{.*?}}'
                        context_match = re.search(video_context_pattern, page_source, re.DOTALL)
                        if context_match:
                            context = context_match.group(0)
                            
                            # 在上下文中查找数据
                            if not like_count:
                                like_matches = re.findall(r'"digg_count":\s*(\d+)|"like_count":\s*(\d+)|"likeCount":\s*(\d+)', context)
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
                            
                            if not view_count:
                                view_matches = re.findall(r'"play_count":\s*(\d+)|"view_count":\s*(\d+)|"viewCount":\s*(\d+)', context)
                                if view_matches:
                                    for match in view_matches:
                                        count = int([x for x in match if x][0])
                                        if count > 0:
                                            view_count = count
                                            if self.debug:
                                                print(f"[DEBUG] ✓ 从JSON获取播放数: {view_count}")
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
                            
                            if not collect_count:
                                collect_matches = re.findall(r'"collect_count":\s*(\d+)|"collectCount":\s*(\d+)', context)
                                if collect_matches:
                                    for match in collect_matches:
                                        count = int([x for x in match if x][0])
                                        if count > 0:
                                            collect_count = count
                                            if self.debug:
                                                print(f"[DEBUG] ✓ 从JSON获取收藏数: {collect_count}")
                                            break
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] 从页面源码提取JSON失败: {e}")
                    pass
            
            # 注意：详情页访问已在上面处理，这里不再重复访问
            
            if self.debug:
                print(f"[DEBUG] 最终数据 - 点赞: {like_count}, 评论: {comment_count}, 播放: {view_count}, 收藏: {collect_count}, 分享: {share_count}")
            
            # 检查标题是否包含关键词（放宽条件）
            title_lower = title.lower() if title else ''
            keywords = ['华为', 'huawei', '鸿蒙', 'harmony', 'mate', 'p系列', 'nova', 'honor']
            matched_keywords = [kw for kw in keywords if kw in title_lower]
            if not matched_keywords:
                if self.debug:
                    print(f"[DEBUG] ✗ 标题不包含关键词: {title[:50] if title else 'N/A'}")
                return None
            if self.debug:
                print(f"[DEBUG] ✓ 关键词匹配: {matched_keywords}, 标题: {title[:50] if title else 'N/A'}")
            
            return {
                'Post_ID': video_id,
                'Platform': 'Douyin',
                'Publish_Date': '',
                'Post_URL': href or f"https://www.douyin.com/video/{video_id}",
                'Author_ID': '',
                'Author_Name': author_name,
                'Title': title,
                'Content': title,  # 抖音标题和内容通常是同一个
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
    
    def _get_video_detail_from_page(self, driver, url: str, video_id: str) -> Dict:
        """
        访问视频详情页获取互动数据（增强版，类似小红书的做法）
        使用直接导航方式，避免新标签页导致的问题
        """
        detail_data = {}
        original_window = None
        
        try:
            # 验证并构建正确的URL
            if not url or not video_id:
                if self.debug:
                    print(f"[DEBUG] ⚠ URL或视频ID无效: url={url}, video_id={video_id}")
                return {}
            
            # 确保URL格式正确
            if not url.startswith('http'):
                if video_id and video_id.isdigit():
                    url = f"https://www.douyin.com/video/{video_id}"
                else:
                    if self.debug:
                        print(f"[DEBUG] ⚠ 无法构建有效的视频URL")
                    return {}
            
            if self.debug:
                print(f"[DEBUG] 访问详情页: {url} (视频ID: {video_id})")
            
            # 保存原始窗口句柄
            original_window = driver.current_window_handle
            
            # 直接在当前窗口导航（更稳定，避免新标签页被关闭的问题）
            try:
                # 确保在有效窗口
                if original_window not in driver.window_handles:
                    available_windows = driver.window_handles
                    if available_windows:
                        original_window = available_windows[0]
                        driver.switch_to.window(original_window)
                    else:
                        if self.debug:
                            print(f"[DEBUG] ⚠ 没有可用的窗口")
                        return {}
                
                # 直接导航到URL
                driver.get(url)
                time.sleep(5)  # 等待页面加载
                
                # 验证页面是否加载成功
                try:
                    from selenium.webdriver.common.by import By
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    
                    # 等待页面加载
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    # 检查页面是否显示"视频不存在"或其他错误
                    page_text = driver.page_source
                    current_url = driver.current_url
                    
                    if '视频不存在' in page_text or '视频已删除' in page_text or 'not found' in page_text.lower():
                        if self.debug:
                            print(f"[DEBUG] ⚠ 视频不存在或已删除: {url}")
                        return {}
                    
                    # 验证URL是否包含视频ID（确保页面加载正确）
                    if video_id not in current_url and video_id not in page_text:
                        if self.debug:
                            print(f"[DEBUG] ⚠ 页面未包含视频ID，可能加载失败: {current_url}")
                        return {}
                    
                    if self.debug:
                        print(f"[DEBUG] ✓ 详情页加载成功: {current_url}")
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] 页面加载验证失败: {e}")
                    # 继续尝试提取数据，即使验证失败
                
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 导航到详情页失败: {e}")
                    import traceback
                    traceback.print_exc()
                return {}
            
            # 额外等待，确保页面完全加载
            time.sleep(3)
            
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
            
            # 可能需要处理登录弹窗
            try:
                from selenium.webdriver.common.by import By
                close_selectors = [
                    "[class*='close']",
                    "[aria-label*='关闭']",
                    ".close-btn",
                    ".dy-account-close"
                ]
                for selector in close_selectors:
                    try:
                        close_btn = driver.find_element(By.CSS_SELECTOR, selector)
                        close_btn.click()
                        time.sleep(1)
                        break
                    except:
                        continue
            except:
                pass
            
            # 尝试提取互动数据
            detail_data = {}
            try:
                # 方法1: 从window对象中提取（最准确，类似小红书）
                scripts = [
                    "return window.__INITIAL_STATE__;",
                    "return window.__REDUX_STATE__;",
                    "return window._SSR_HYDRATED_DATA;",
                    "return window.__UNIVERSAL_DATA_FOR_HYDRATION__;",
                    "return window.__RENDER_DATA__;",
                    "return window.awemeDetail;",
                    "return window.videoData;",
                    "return window.pageData;",
                    "return window.__NEXT_DATA__;"
                ]
                for script in scripts:
                    try:
                        data = driver.execute_script(script)
                        if data:
                            # 递归搜索视频数据，但只提取当前视频ID的数据
                            video_data = self._find_video_data_in_json(data, target_video_id=video_id)
                            if video_data and video_id in video_data:
                                extracted_data = video_data[video_id]
                                
                                # 验证提取的数据是否合理
                                if self._validate_interaction_data(extracted_data, video_id):
                                    detail_data.update(extracted_data)
                                    if self.debug:
                                        print(f"[DEBUG] ✓ 从window对象提取到数据（视频ID: {video_id}）: {detail_data}")
                                    # 如果获取到完整数据，就不再尝试其他方法
                                    if detail_data.get('like_count') and detail_data.get('comment_count'):
                                        break
                                elif self.debug:
                                    print(f"[DEBUG] ⚠ 从window对象提取的数据验证失败: {extracted_data}")
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
                                
                                # 查找包含互动数据的JSON（优先匹配当前视频ID）
                                if 'digg_count' in script_text or 'statistics' in script_text or 'awemeDetail' in script_text:
                                    # 优先使用包含视频ID的精确匹配
                                    # 方法1: 精确匹配当前视频ID
                                    precise_pattern = r'{"aweme_id":"' + re.escape(video_id) + r'"[^}]*?"statistics":\s*\{[^}]*?"digg_count":\s*(\d+)[^}]*?"comment_count":\s*(\d+)[^}]*?"play_count":\s*(\d+)[^}]*?"share_count":\s*(\d+)[^}]*?"collect_count":\s*(\d+)'
                                    
                                    # 方法2: 如果精确匹配失败，使用通用模式（但需要验证URL）
                                    json_patterns = [
                                        precise_pattern,  # 优先精确匹配
                                        r'{"aweme_id":"' + re.escape(video_id) + r'".*?"digg_count":\s*(\d+).*?"comment_count":\s*(\d+).*?"play_count":\s*(\d+).*?"share_count":\s*(\d+).*?"collect_count":\s*(\d+)',
                                    ]
                                    
                                    for json_pattern in json_patterns:
                                        json_match = re.search(json_pattern, script_text, re.DOTALL)
                                        if json_match:
                                            try:
                                                # 验证提取的数据是否对应正确的视频ID
                                                matched_video_id = None
                                                # 尝试从匹配结果中提取视频ID
                                                id_match = re.search(r'"aweme_id":"(\d+)"', json_match.group(0))
                                                if id_match:
                                                    matched_video_id = id_match.group(1)
                                                
                                                # 如果视频ID匹配，或者使用的是精确匹配模式
                                                if matched_video_id == video_id or json_pattern == precise_pattern:
                                                    if not detail_data.get('like_count'):
                                                        detail_data['like_count'] = int(json_match.group(1))
                                                    if not detail_data.get('comment_count'):
                                                        detail_data['comment_count'] = int(json_match.group(2))
                                                    if not detail_data.get('view_count'):
                                                        detail_data['view_count'] = int(json_match.group(3))
                                                    if not detail_data.get('share_count'):
                                                        detail_data['share_count'] = int(json_match.group(4))
                                                    if not detail_data.get('collect_count'):
                                                        detail_data['collect_count'] = int(json_match.group(5))
                                                    
                                                    if detail_data and self.debug:
                                                        print(f"[DEBUG] ✓ 从script标签提取到数据（视频ID: {video_id}）: {detail_data}")
                                                    break
                                                elif self.debug:
                                                    print(f"[DEBUG] ⚠ 警告：提取的数据视频ID不匹配！期望: {video_id}, 实际: {matched_video_id}")
                                            except Exception as e:
                                                if self.debug:
                                                    print(f"[DEBUG] 解析JSON数据失败: {e}")
                                                continue
                                    
                                    # 如果已经获取到数据，停止搜索
                                    if detail_data.get('like_count') or detail_data.get('comment_count'):
                                        break
                            except Exception as e:
                                if self.debug:
                                    print(f"[DEBUG] script标签提取失败: {str(e)[:50]}")
                                continue
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG] 从script标签提取失败: {e}")
                
                # 方法3: 从页面元素中提取（抖音详情页通常会在页面上显示这些数据）
                if not detail_data or not detail_data.get('like_count'):
                    try:
                        from selenium.webdriver.common.by import By
                        
                        # 尝试从页面元素中查找互动数据
                        interact_selectors = [
                            "[class*='like']",
                            "[class*='comment']",
                            "[class*='collect']",
                            "[class*='share']",
                            "[class*='play']",
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
                                    
                                    if '播放' in text or 'play' in text.lower() or 'view' in text.lower():
                                        match = re.search(r'(\d+\.?\d*)[万w]?', text)
                                        if match and not detail_data.get('view_count'):
                                            detail_data['view_count'] = self._parse_count(match)
                                            if self.debug:
                                                print(f"[DEBUG] ✓ 从元素提取播放数: {detail_data['view_count']}")
                                    
                                    # 如果已经找到了所有数据，停止搜索
                                    if detail_data.get('like_count') and detail_data.get('comment_count') and detail_data.get('collect_count'):
                                        break
                            except:
                                continue
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG] 从页面元素提取失败: {e}")
                
                # 方法4: 从页面源码HTML中提取（最后的手段，但必须确保匹配正确的视频）
                if not detail_data or not detail_data.get('like_count'):
                    page_text = driver.page_source
                    
                    # 首先尝试在视频ID附近提取数据（确保数据准确性）
                    # 查找视频ID附近的JSON数据块
                    escaped_video_id = re.escape(video_id)
                    video_context_pattern = rf'"aweme_id":"{escaped_video_id}"[^}}]{{0,3000}}?"statistics":\s*{{[^}}]{{0,2000}}?"digg_count":\s*(\d+)[^}}]{{0,2000}}?"comment_count":\s*(\d+)[^}}]{{0,2000}}?"play_count":\s*(\d+)[^}}]{{0,2000}}?"share_count":\s*(\d+)[^}}]{{0,2000}}?"collect_count":\s*(\d+)'
                    context_match = re.search(video_context_pattern, page_text, re.DOTALL)
                    
                    if context_match:
                        try:
                            if not detail_data.get('like_count'):
                                detail_data['like_count'] = int(context_match.group(1))
                            if not detail_data.get('comment_count'):
                                detail_data['comment_count'] = int(context_match.group(2))
                            if not detail_data.get('view_count'):
                                detail_data['view_count'] = int(context_match.group(3))
                            if not detail_data.get('share_count'):
                                detail_data['share_count'] = int(context_match.group(4))
                            if not detail_data.get('collect_count'):
                                detail_data['collect_count'] = int(context_match.group(5))
                            if self.debug:
                                print(f"[DEBUG] ✓ 从视频ID上下文提取到完整数据（视频ID: {video_id}）: {detail_data}")
                        except Exception as e:
                            if self.debug:
                                print(f"[DEBUG] 从视频ID上下文提取失败: {e}")
                    
                    # 如果上下文提取失败，尝试通用的正则匹配（但验证数据合理性）
                    if not detail_data.get('like_count'):
                        # 从页面源码中提取数据（但只提取视频ID附近的数据）
                        escaped_vid = re.escape(video_id)
                        patterns = {
                            'like_count': [
                                # 优先匹配包含视频ID的模式
                                rf'"aweme_id":"{escaped_vid}"[^}}]*?"digg_count":\s*(\d+)',
                                rf'"digg_count":\s*(\d+)(?=[^}}]*?"aweme_id":"{escaped_vid}")',
                                r'"digg_count":\s*(\d+)',
                                r'"likeCount":\s*(\d+)',
                            ],
                            'comment_count': [
                                rf'"aweme_id":"{escaped_vid}"[^}}]*?"comment_count":\s*(\d+)',
                                rf'"comment_count":\s*(\d+)(?=[^}}]*?"aweme_id":"{escaped_vid}")',
                                r'"comment_count":\s*(\d+)',
                                r'"commentCount":\s*(\d+)',
                            ],
                            'view_count': [
                                rf'"aweme_id":"{escaped_vid}"[^}}]*?"play_count":\s*(\d+)',
                                rf'"play_count":\s*(\d+)(?=[^}}]*?"aweme_id":"{escaped_vid}")',
                                r'"play_count":\s*(\d+)',
                                r'"viewCount":\s*(\d+)',
                            ],
                            'share_count': [
                                rf'"aweme_id":"{escaped_vid}"[^}}]*?"share_count":\s*(\d+)',
                                rf'"share_count":\s*(\d+)(?=[^}}]*?"aweme_id":"{escaped_vid}")',
                                r'"share_count":\s*(\d+)',
                                r'"shareCount":\s*(\d+)',
                            ],
                            'collect_count': [
                                rf'"aweme_id":"{escaped_vid}"[^}}]*?"collect_count":\s*(\d+)',
                                rf'"collect_count":\s*(\d+)(?=[^}}]*?"aweme_id":"{escaped_vid}")',
                                r'"collect_count":\s*(\d+)',
                                r'"collectCount":\s*(\d+)',
                            ]
                        }
                        
                        for key, pattern_list in patterns.items():
                            if detail_data.get(key):  # 如果已经有数据，跳过
                                continue
                            for pattern in pattern_list:
                                match = re.search(pattern, page_text, re.DOTALL)
                                if match:
                                    try:
                                        count_str = match.group(1)
                                        count = int(count_str)
                                        
                                        # 验证数据的合理性（避免提取到错误的数据）
                                        # 点赞数、评论数、播放数通常不会超过10亿
                                        if count < 1000000000:  # 10亿
                                            detail_data[key] = count
                                            if self.debug:
                                                print(f"[DEBUG] ✓ 从详情页页面源码提取{key}: {count}（视频ID: {video_id}）")
                                            break
                                        elif self.debug:
                                            print(f"[DEBUG] ⚠ 提取的{key}数据异常大（{count}），可能匹配错误，跳过")
                                    except Exception as e:
                                        if self.debug:
                                            print(f"[DEBUG] 解析{key}失败: {e}")
                                        continue
                
                # 如果还是没有数据，打印页面源码的一部分用于调试
                if not detail_data and self.debug:
                    page_text_sample = driver.page_source[:3000]  # 前3000个字符
                    print(f"[DEBUG] ⚠ 未找到互动数据，页面源码示例:\n{page_text_sample}")
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] 从详情页提取数据失败: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 最终验证：确保数据对应正确的视频ID
            if detail_data:
                # 验证URL是否包含正确的视频ID
                current_url = driver.current_url
                if video_id not in current_url:
                    if self.debug:
                        print(f"[DEBUG] ⚠ 警告：详情页URL不包含视频ID {video_id}，当前URL: {current_url}")
                    # 如果URL不匹配，清空数据避免错误
                    detail_data = {}
                else:
                    # 验证数据合理性
                    if not self._validate_interaction_data(detail_data, video_id):
                        if self.debug:
                            print(f"[DEBUG] ⚠ 警告：数据验证失败，清空无效数据")
                        detail_data = {}
            
            # 关闭详情页标签，切换回原窗口（如果使用了新标签页）
            # 注意：现在使用直接导航，不需要关闭标签页
            # 但需要确保切换回原始窗口（如果有的话）
            if original_window and original_window in driver.window_handles:
                try:
                    driver.switch_to.window(original_window)
                except:
                    pass
            
            return detail_data
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 访问详情页失败: {e}")
                import traceback
                traceback.print_exc()
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
            driver.get("https://www.douyin.com")
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
    
    def get_comments(self, video_id: str, video_url: str, driver=None, top_n: int = 5, use_api: bool = False) -> List[Dict]:
        """
        获取视频的热门评论（按点赞数排序，取前N条）
        :param video_id: 视频ID
        :param video_url: 视频URL
        :param driver: Selenium driver（可选）
        :param top_n: 获取前N条评论
        :param use_api: 是否使用API方式（需要有效的Cookie）
        :return: 评论列表
        """
        comments = []
        
        # 优先尝试API方式（如果提供了Cookie且use_api=True）
        if use_api and self.cookie_str:
            try:
                comments = self._get_comments_via_api(video_id, video_url, top_n)
                if comments:
                    if self.debug:
                        print(f"[DEBUG] ✓ 通过API获取到 {len(comments)} 条评论")
                    return comments
            except Exception as e:
                if self.debug:
                    print(f"[DEBUG] API方式获取评论失败，回退到Selenium: {e}")
        
        # 回退到Selenium方式
        try:
            if not driver:
                if self.debug:
                    print(f"[DEBUG] 需要driver来获取抖音评论")
                return comments
            
            # 访问视频详情页
            original_window = driver.current_window_handle
            driver.execute_script(f"window.open('{video_url}', '_blank');")
            time.sleep(3)
            
            # 切换到新标签页
            windows = driver.window_handles
            if len(windows) > 1:
                driver.switch_to.window(windows[-1])
                time.sleep(3)
                
                # 尝试滚动到评论区
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                except:
                    pass
                
                # 从页面源码中提取评论
                page_source = driver.page_source
                
                # 方法1: 从JSON数据中提取评论
                try:
                    # 查找评论相关的JSON数据
                    comment_patterns = [
                        r'"comment_list":\s*\[(.*?)\]',
                        r'"comments":\s*\[(.*?)\]',
                        r'"items":\s*\[(.*?)\]'
                    ]
                    
                    for pattern in comment_patterns:
                        matches = re.finditer(pattern, page_source, re.DOTALL)
                        for match in matches:
                            # 尝试提取评论数据
                            comment_block = match.group(0)
                            
                            # 提取单个评论
                            single_comment_pattern = r'{"comment_id":"(\d+)".*?"text":"([^"]+)".*?"digg_count":(\d+).*?"user_name":"([^"]+)"'
                            comment_matches = re.finditer(single_comment_pattern, comment_block, re.DOTALL)
                            
                            for cm in comment_matches:
                                try:
                                    comments.append({
                                        'Post_ID': video_id,
                                        'Comment_ID': cm.group(1),
                                        'Comment_Content': cm.group(2),
                                        'Comment_Author': cm.group(4),
                                        'Comment_Like_Count': int(cm.group(3)),
                                        'Comment_Time': '',
                                        'Platform': 'Douyin'
                                    })
                                except:
                                    continue
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] 从JSON提取评论失败: {e}")
                
                # 方法2: 从页面元素中提取评论
                if not comments:
                    try:
                        from selenium.webdriver.common.by import By
                        
                        comment_selectors = [
                            ".comment-item",
                            "[class*='comment']",
                            "[class*='Comment']",
                            "[data-e2e='comment-item']"
                        ]
                        
                        comment_elements = []
                        for selector in comment_selectors:
                            try:
                                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                if elements:
                                    comment_elements = elements
                                    break
                            except:
                                continue
                        
                        if comment_elements:
                            comment_data_list = []
                            for elem in comment_elements[:20]:  # 最多取20条，然后排序
                                try:
                                    # 提取评论内容
                                    content = elem.text.strip()
                                    
                                    # 提取点赞数
                                    like_count = 0
                                    like_elem = elem.find_elements(By.CSS_SELECTOR, "[class*='like'], [class*='Like']")
                                    if like_elem:
                                        like_text = like_elem[0].text.strip()
                                        like_match = re.search(r'(\d+\.?\d*)[万]?', like_text)
                                        if like_match:
                                            like_count = self._parse_count(like_match)
                                    
                                    # 提取作者
                                    author = ''
                                    author_elem = elem.find_elements(By.CSS_SELECTOR, "[class*='author'], [class*='user'], [class*='name']")
                                    if author_elem:
                                        author = author_elem[0].text.strip()
                                    
                                    if content:
                                        comment_data_list.append({
                                            'content': content,
                                            'like_count': like_count,
                                            'author': author
                                        })
                                except:
                                    continue
                            
                            # 按点赞数排序
                            comment_data_list.sort(key=lambda x: x['like_count'], reverse=True)
                            
                            # 取前N条
                            for i, comment_data in enumerate(comment_data_list[:top_n]):
                                comments.append({
                                    'Post_ID': video_id,
                                    'Comment_ID': f"{video_id}_comment_{i+1}",
                                    'Comment_Content': comment_data['content'],
                                    'Comment_Author': comment_data['author'],
                                    'Comment_Like_Count': comment_data['like_count'],
                                    'Comment_Time': '',
                                    'Platform': 'Douyin'
                                })
                            
                            if self.debug:
                                print(f"[DEBUG] ✓ 获取到 {len(comments)} 条抖音评论")
                    except Exception as e:
                        if self.debug:
                            print(f"[DEBUG] 从页面元素提取评论失败: {e}")
                
                # 关闭详情页标签，切换回原窗口
                driver.close()
                driver.switch_to.window(original_window)
                time.sleep(1)
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 抖音评论爬取出错: {e}")
            # 确保切换回原窗口
            try:
                driver.switch_to.window(original_window)
            except:
                pass
        
        return comments
    
    def _get_comments_via_api(self, video_id: str, video_url: str, top_n: int = 5) -> List[Dict]:
        """
        通过API获取视频评论（从DouYin文件夹提取的核心功能）
        :param video_id: 视频ID
        :param video_url: 视频URL
        :param top_n: 获取前N条评论
        :return: 评论列表
        """
        comments = []
        try:
            # 从URL中提取aweme_id
            if 'video' in video_url:
                aweme_id = video_url.split("/")[-1].split("?")[0]
            else:
                match = re.findall(r'modal_id=(\d+)', video_url)
                if match:
                    aweme_id = match[0]
                else:
                    aweme_id = video_id
            
            # API端点
            api = "/aweme/v1/web/comment/list/"
            url = f"{self.base_url}{api}"
            
            # 构建请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Referer': video_url,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            # 构建完整的请求参数（包含所有必要的签名参数）
            params = {
                "device_platform": "webapp",
                "aid": "6383",
                "channel": "channel_pc_web",
                "aweme_id": aweme_id,
                "cursor": "0",
                "count": str(min(top_n * 2, 20)),  # 多获取一些以便排序
                "item_type": "0",
                "whale_cut_token": "",
                "cut_version": "1",
                "rcFT": "",
                "update_version_code": "170400",
                "pc_client_type": "1",
                "version_code": "170400",
                "version_name": "17.4.0",
                "cookie_enabled": "true",
                "screen_width": "1707",
                "screen_height": "960",
                "browser_language": "zh-CN",
                "browser_platform": "Win32",
                "browser_name": "Edge",
                "browser_version": "125.0.0.0",
                "browser_online": "true",
                "engine_name": "Blink",
                "engine_version": "125.0.0.0",
                "os_name": "Windows",
                "os_version": "10",
                "cpu_core_num": "32",
                "device_memory": "8",
                "platform": "PC",
                "downlink": "10",
                "effective_type": "4g",
                "round_trip_time": "0",
            }
            
            # 添加完整的认证参数（包括逆向工程生成的签名）
            cookies_dict = {}
            if self.cookie_str:
                cookies_dict = self._trans_cookies(self.cookie_str)
            
            # 添加 verifyFp 和 fp
            if 's_v_web_id' in cookies_dict:
                params['verifyFp'] = cookies_dict['s_v_web_id']
                params['fp'] = cookies_dict['s_v_web_id']
            
            # 添加 webid
            webid = self._generate_webid(video_url)
            params['webid'] = webid
            
            # 添加 msToken
            if 'msToken' in cookies_dict:
                params['msToken'] = cookies_dict['msToken']
            else:
                params['msToken'] = self._generate_msToken()
            
            # 生成 a_bogus 签名参数（核心逆向工程功能）
            sorted_params = self._sort_params(params)
            query_str = self._splice_url(sorted_params)
            a_bogus = self._generate_a_bogus(query_str, "")
            if a_bogus:
                params['a_bogus'] = a_bogus
                if self.debug:
                    print(f"[DEBUG] ✓ 已添加 a_bogus 签名参数（评论）")
            else:
                if self.debug:
                    print(f"[DEBUG] ⚠ 无法生成 a_bogus（评论），API 调用可能失败")
            
            # 发送请求
            response = self.session.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status_code') == 0:
                comment_list = data.get('comments', [])
                if comment_list:
                    # 按点赞数排序
                    comment_list.sort(key=lambda x: x.get('digg_count', 0), reverse=True)
                    
                    # 取前N条
                    for i, comment in enumerate(comment_list[:top_n]):
                        comments.append({
                            'Post_ID': video_id,
                            'Comment_ID': str(comment.get('cid', f"{video_id}_comment_{i+1}")),
                            'Comment_Content': comment.get('text', ''),
                            'Comment_Author': comment.get('user', {}).get('nickname', ''),
                            'Comment_Like_Count': comment.get('digg_count', 0),
                            'Comment_Time': '',
                            'Platform': 'Douyin'
                        })
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] API方式获取评论失败: {e}")
        
        return comments
    
    def _get_video_info_via_api(self, video_url: str) -> Optional[Dict]:
        """
        通过API获取视频详情和互动数据（增强版，整合DouYin文件夹的完整功能）
        这是获取准确互动数据的最佳方式
        :param video_url: 视频URL
        :return: 视频详情字典，包含准确的互动数据
        """
        try:
            # 从URL中提取aweme_id
            if 'video' in video_url:
                aweme_id = video_url.split("/")[-1].split("?")[0]
            else:
                match = re.findall(r'modal_id=(\d+)', video_url)
                if match:
                    aweme_id = match[0]
                else:
                    return None
            
            if not aweme_id:
                return None
            
            # API端点（使用DouYin文件夹中的完整API）
            api = "/aweme/v1/web/aweme/detail/"
            url = f"{self.base_url}{api}"
            
            # 构建完整的请求参数（参考DouYin文件夹中的Params类）
            params = {
                "device_platform": "webapp",
                "aid": "6383",
                "channel": "channel_pc_web",
                "aweme_id": aweme_id,
                "update_version_code": "170400",
                "pc_client_type": "1",
                "version_code": "190500",
                "version_name": "19.5.0",
                "cookie_enabled": "true",
                "screen_width": "1707",
                "screen_height": "960",
                "browser_language": "zh-CN",
                "browser_platform": "Win32",
                "browser_name": "Edge",
                "browser_version": "125.0.0.0",
                "browser_online": "true",
                "engine_name": "Blink",
                "engine_version": "125.0.0.0",
                "os_name": "Windows",
                "os_version": "10",
                "cpu_core_num": "32",
                "device_memory": "8",
                "platform": "PC",
                "downlink": "4.75",
                "effective_type": "4g",
                "round_trip_time": "150",
            }
            
            # 添加完整的认证参数（包括逆向工程生成的签名）
            cookies_dict = {}
            if self.cookie_str:
                cookies_dict = self._trans_cookies(self.cookie_str)
            
            # 添加 verifyFp 和 fp（从 cookie 中获取 s_v_web_id）
            if 's_v_web_id' in cookies_dict:
                params['verifyFp'] = cookies_dict['s_v_web_id']
                params['fp'] = cookies_dict['s_v_web_id']
            
            # 添加 webid
            webid = self._generate_webid(video_url)
            params['webid'] = webid
            
            # 添加 msToken（如果 cookie 中有，否则生成一个）
            if 'msToken' in cookies_dict:
                params['msToken'] = cookies_dict['msToken']
            else:
                params['msToken'] = self._generate_msToken()
            
            # 生成 a_bogus 签名参数（核心逆向工程功能）
            # 先对参数进行排序（按照抖音要求的顺序）
            sorted_params = self._sort_params(params)
            query_str = self._splice_url(sorted_params)
            a_bogus = self._generate_a_bogus(query_str, "")
            if a_bogus:
                params['a_bogus'] = a_bogus
                if self.debug:
                    print(f"[DEBUG] ✓ 已添加 a_bogus 签名参数")
            else:
                if self.debug:
                    print(f"[DEBUG] ⚠ 无法生成 a_bogus，API 调用可能失败")
            
            # 构建完整的请求头（参考DouYin文件夹中的HeaderBuilder）
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Referer': video_url,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Microsoft Edge";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            }
            
            # 发送请求（使用session，会自动携带cookie）
            response = self.session.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # 解析响应（这是最准确的数据来源）
            if data.get('status_code') == 0 and 'aweme_detail' in data:
                aweme_detail = data['aweme_detail']
                statistics = aweme_detail.get('statistics', {})
                author = aweme_detail.get('author', {})
                
                # 提取准确的互动数据
                result = {
                    'like_count': statistics.get('digg_count', 0) or 0,
                    'comment_count': statistics.get('comment_count', 0) or 0,
                    'view_count': statistics.get('play_count', 0) or statistics.get('view_count', 0) or 0,
                    'share_count': statistics.get('share_count', 0) or 0,
                    'collect_count': statistics.get('collect_count', 0) or 0,
                    'author_name': author.get('nickname', ''),
                    'author_id': str(author.get('uid', '')),
                    'title': aweme_detail.get('desc', ''),
                    'publish_date': '',
                }
                
                # 解析发布时间
                create_time = aweme_detail.get('create_time')
                if create_time:
                    try:
                        result['publish_date'] = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                if self.debug:
                    print(f"[DEBUG] ✓ API获取到准确的互动数据 - 点赞: {result['like_count']}, 评论: {result['comment_count']}, 播放: {result['view_count']}, 分享: {result['share_count']}, 收藏: {result['collect_count']}")
                
                return result
            else:
                if self.debug:
                    print(f"[DEBUG] API返回错误: status_code={data.get('status_code')}, msg={data.get('status_msg', '未知错误')}")
                return None
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] API获取视频详情失败: {e}")
                import traceback
                traceback.print_exc()
            return None
    
    def _search_videos_via_api(self, keyword: str, offset: int = 0, count: int = 25) -> List[Dict]:
        """
        通过API搜索视频（从DouYin文件夹提取的核心功能）
        :param keyword: 搜索关键词
        :param offset: 偏移量
        :param count: 数量
        :return: 视频列表
        """
        videos = []
        try:
            # API端点
            api = "/aweme/v1/web/general/search/single/"
            url = f"{self.base_url}{api}"
            
            # 构建请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Referer': f'https://www.douyin.com/search/{quote(keyword)}?type=general',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            
            # 构建完整的请求参数（包含所有必要的签名参数）
            params = {
                "device_platform": "webapp",
                "aid": "6383",
                "channel": "channel_pc_web",
                "search_channel": "aweme_general",
                "enable_history": "1",
                "filter_selected": json.dumps({
                    "sort_type": "0",
                    "publish_time": "0",
                    "filter_duration": "",
                    "search_range": "0",
                    "content_type": "0"
                }, ensure_ascii=False),
                "keyword": keyword,
                "search_source": "tab_search",
                "query_correct_type": "1",
                "is_filter_search": "1",
                "from_group_id": "",
                "offset": str(offset),
                "count": str(count),
                "need_filter_settings": "1" if offset == 0 else "0",
                "list_type": "single",
                "update_version_code": "170400",
                "pc_client_type": "1",
                "version_code": "190600",
                "version_name": "19.6.0",
                "cookie_enabled": "true",
                "screen_width": "1707",
                "screen_height": "960",
                "browser_language": "zh-CN",
                "browser_platform": "Win32",
                "browser_name": "Edge",
                "browser_version": "125.0.0.0",
                "browser_online": "true",
                "engine_name": "Blink",
                "engine_version": "125.0.0.0",
                "os_name": "Windows",
                "os_version": "10",
                "cpu_core_num": "32",
                "device_memory": "8",
                "platform": "PC",
                "downlink": "10",
                "effective_type": "4g",
                "round_trip_time": "50",
            }
            
            # 添加完整的认证参数（包括逆向工程生成的签名）
            cookies_dict = {}
            if self.cookie_str:
                cookies_dict = self._trans_cookies(self.cookie_str)
            
            # 添加 verifyFp 和 fp
            if 's_v_web_id' in cookies_dict:
                params['verifyFp'] = cookies_dict['s_v_web_id']
                params['fp'] = cookies_dict['s_v_web_id']
            
            # 添加 webid
            webid = self._generate_webid()
            params['webid'] = webid
            
            # 添加 msToken
            if 'msToken' in cookies_dict:
                params['msToken'] = cookies_dict['msToken']
            else:
                params['msToken'] = self._generate_msToken()
            
            # 生成 a_bogus 签名参数（核心逆向工程功能）
            sorted_params = self._sort_params(params)
            query_str = self._splice_url(sorted_params)
            a_bogus = self._generate_a_bogus(query_str, "")
            if a_bogus:
                params['a_bogus'] = a_bogus
                if self.debug:
                    print(f"[DEBUG] ✓ 已添加 a_bogus 签名参数（搜索）")
            else:
                if self.debug:
                    print(f"[DEBUG] ⚠ 无法生成 a_bogus（搜索），API 调用可能失败")
            
            # 发送请求
            response = self.session.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status_code') == 0:
                items = data.get('data', [])
                for item in items:
                    aweme_info = item.get('aweme_info', {})
                    if aweme_info:
                        video_info = self._parse_video_info_from_api(aweme_info)
                        if video_info:
                            videos.append(video_info)
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] API方式搜索视频失败: {e}")
        
        return videos
    
    def _parse_video_info_from_api(self, aweme_info: Dict) -> Optional[Dict]:
        """
        从API返回的数据中解析视频信息
        """
        try:
            aweme_id = str(aweme_info.get('aweme_id', ''))
            author_info = aweme_info.get('author', {})
            statistics = aweme_info.get('statistics', {})
            
            # 解析时间戳
            create_time = aweme_info.get('create_time', 0)
            publish_date = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S') if create_time else ''
            
            # 解析标签
            text_extra = aweme_info.get('text_extra', [])
            tags = ','.join([item.get('hashtag_name', '') for item in text_extra if item.get('hashtag_name')])
            
            return {
                'Post_ID': aweme_id,
                'Platform': 'Douyin',
                'Publish_Date': publish_date,
                'Post_URL': f"https://www.douyin.com/video/{aweme_id}",
                'Author_ID': str(author_info.get('uid', '')),
                'Author_Name': author_info.get('nickname', ''),
                'Title': aweme_info.get('desc', ''),
                'Content': aweme_info.get('desc', ''),
                'Tags': tags,
                'Like_Count': statistics.get('digg_count', 0),
                'Comment_Count': statistics.get('comment_count', 0),
                'Collect_Count': statistics.get('collect_count', 0),
                'Share_Count': statistics.get('share_count', 0),
                'View_Count': statistics.get('play_count', 0),
            }
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 解析API视频信息失败: {e}")
            return None
    
    def _parse_count(self, match) -> int:
        """解析数量（支持万单位）"""
        if not match:
            return 0
        try:
            # 获取匹配的完整文本
            full_match = match.group(0) if hasattr(match, 'group') else str(match)
            count_str = match.group(1) if hasattr(match, 'group') else str(match)
            
            # 提取数字部分
            count = float(count_str)
            
            # 检查是否包含"万"字符
            if '万' in full_match or 'w' in full_match.lower():
                count = int(count * 10000)
            else:
                count = int(count)
            
            return count
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] 解析数量失败: {e}, match: {match}")
            return 0
    
    def crawl(self, keyword: str = "华为", max_pages: int = 10, use_selenium: bool = True) -> List[Dict]:
        """
        爬取多页数据
        :param keyword: 搜索关键词
        :param max_pages: 最大爬取页数
        :param use_selenium: 是否使用selenium（推荐）
        :return: 所有视频数据
        """
        if use_selenium:
            return self.crawl_with_selenium(keyword, max_pages)
        else:
            all_videos = []
            cursor = 0
            for page in range(1, max_pages + 1):
                print(f"正在爬取抖音第 {page} 页...")
                videos = self.search_videos(keyword, cursor=cursor)
                if not videos:
                    break
                all_videos.extend(videos)
                cursor += len(videos)
                time.sleep(random.uniform(2, 4))
            return all_videos


if __name__ == "__main__":
    spider = DouyinSpider()
    # 测试爬取（使用selenium）
    results = spider.crawl(keyword="华为", max_pages=2, use_selenium=True)
    print(f"\n测试结果: 共获取 {len(results)} 条数据")
    if results:
        print("\n第一条数据示例:")
        print(json.dumps(results[0], ensure_ascii=False, indent=2))

