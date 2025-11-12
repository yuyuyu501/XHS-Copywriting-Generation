import asyncio
import os
import json
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError

BASE_URL = "https://www.xiaohongshu.com"
DEFAULT_WAIT_TIME = 5000  # 默认等待时间（毫秒）
LOGIN_WAIT_TIME = 10000   # 登录等待时间（毫秒）
SCROLL_WAIT_TIME = 4000   # 滚动等待时间（毫秒）


class XiaohongshuCrawler:
    def __init__(self, mode="keyword"):
        """
        初始化小红书爬虫
        
        Args:
            mode (str): 爬取模式，"keyword" 为关键词搜索，"user" 为用户主页爬取
        """
        self.mode = mode
        self.user_data_dir = "xiaohongshu/user_data"
        # 设置cookie文件路径
        self.cookie_file_path = "D:/小红书文案2/代码/支线/教育/xhs_cookies.json"
        
    def _normalize_note_link(self, raw_href: str) -> str | None:
        """将用户主页里的各种笔记链接规范化为可直接打开的笔记详情页链接。

        支持：
        - /search_result/<noteId>?query_params (只处理这种格式的链接)
        返回绝对地址，如 https://www.xiaohongshu.com/search_result/<noteId>?query_params
        找不到 noteId 时返回 None。
        """
        if not raw_href:
            return None

        # 只处理包含 search_result 和查询参数的链接
        if "/search_result/" in raw_href and "?" in raw_href:
            # 确保是完整的绝对链接
            if raw_href.startswith("http"):
                return raw_href
            else:
                return f"{BASE_URL}{raw_href}"

        # 其他格式的链接不处理
        return None
    
    async def _check_login_required(self, page, context):
        """
        检查是否需要登录，并处理登录流程
        """
        need_login = False
        try:
            await page.wait_for_selector("text=登录", timeout=LOGIN_WAIT_TIME)
            need_login = True
        except TimeoutError:
            need_login = False

        if need_login:
            print("检测到需要登录，请扫码后按回车继续...")
            input()
            # 保存cookie到指定路径
            cookies = await context.cookies()
            self._save_cookies(cookies)
            print(f"已保存最新cookie到 {self.cookie_file_path}，下次可自动登录。")
        else:
            print("已登录，无需扫码。")
        
        # 等待页面加载完成
        await page.wait_for_timeout(DEFAULT_WAIT_TIME)
        return need_login

    async def _click_tab(self, page, tab_selector, tab_name):
        """
        点击指定的Tab
        """
        try:
            tab = await page.query_selector(tab_selector)
            if tab:
                await tab.click()
                print(f"✅ 已点击'{tab_name}'Tab")
                await page.wait_for_timeout(DEFAULT_WAIT_TIME)
            else:
                print(f"ℹ️ 未找到'{tab_name}'Tab，继续获取所有内容")
        except Exception as e:
            print(f"点击{tab_name}Tab时出错: {e}")

    async def _scroll_page(self, page):
        """
        滚动页面以加载更多内容
        """
        await page.mouse.wheel(0, 1500)  # 增加滚动距离
        await page.wait_for_timeout(SCROLL_WAIT_TIME)  # 增加等待时间，确保内容加载

    async def _get_user_notes_from_profile(self, user_profile_url, max_notes=0, context=None, use_cache=True):
        """
        从用户主页获取图文笔记链接
        """
        if context is None:
            raise ValueError("context 参数不能为空")
        
        # 定义缓存文件路径
        cache_file = "D:/小红书文案2/代码/支线/教育/xiaohongshu/note_urls_cache.json"
        
        # 如果启用缓存且缓存文件存在，则直接读取
        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if isinstance(cached_data, list):
                        print(f"✅ 从缓存文件{cache_file}读取到 {len(cached_data)} 个笔记链接")
                        return cached_data[:max_notes] if max_notes > 0 else cached_data
            except Exception as e:
                print(f"读取缓存文件失败: {e}")
        
        page = await context.new_page()
        await page.goto(user_profile_url)
        await page.wait_for_timeout(LOGIN_WAIT_TIME)

        # 检查是否需要登录
        await self._check_login_required(page, context)

        # 尝试点击"图文"Tab（如果存在）
        await self._click_tab(page, "div.channel[title='图文'], div.channel:has-text('图文')", "图文")

        # 获取用户的所有笔记链接
        note_urls = []
        
        # 尝试多种选择器来获取笔记链接，优先使用copy_writing.py中的方法
        selectors = [
            "a.cover.mask.ld[href]",  # copy_writing.py中使用的方法
            "a[href*='/user/profile/']",  # 优先获取用户主页格式的链接
            ".note-item a[href]",
            ".feeds-container a[href*='/user/profile/']"
        ]
        
        for selector in selectors:
            try:
                cards = await page.query_selector_all(selector)
                if cards:
                    print(f"使用选择器 {selector} 找到 {len(cards)} 个元素")
                    for card in cards:
                        href = await card.get_attribute("href")
                        normalized = self._normalize_note_link(href) if href else None
                        if normalized and normalized not in note_urls:
                            note_urls.append(normalized)
                            # 显示链接类型
                            if "/user/profile/" in normalized:
                                print(f"  + 获取到用户主页格式链接: {normalized[:80]}...")
                            else:
                                print(f"  + 获取到备选格式链接: {normalized[:80]}...")
                        if max_notes > 0 and len(note_urls) >= max_notes:
                            break
                    if note_urls:
                        break
            except Exception as e:
                print(f"选择器 {selector} 失败: {e}")
                continue

        # 无论是否找到链接，都尝试滚动加载更多内容
        print("开始滚动加载更多内容...")
        previous_count = len(note_urls)
        scroll_attempts = 0
        max_scroll_attempts = 100  # 增加滚动次数
        no_new_content_count = 5  # 连续无新内容的次数
        
        while scroll_attempts < max_scroll_attempts:
            # 滚动页面
            await self._scroll_page(page)

            # 再次尝试获取链接
            current_count = len(note_urls)
            for selector in selectors:
                try:
                    cards = await page.query_selector_all(selector)
                    if cards:
                        print(f"滚动第 {scroll_attempts + 1} 次，使用选择器 {selector} 找到 {len(cards)} 个元素")
                        for card in cards:
                            href = await card.get_attribute("href")
                            normalized = self._normalize_note_link(href) if href else None
                            if normalized and normalized not in note_urls:
                                note_urls.append(normalized)
                                # 显示链接类型
                                if "/user/profile/" in normalized:
                                    print(f"  + 新增用户主页格式链接: {normalized[:80]}...")
                                else:
                                    print(f"  + 新增备选格式链接: {normalized[:80]}...")
                            if max_notes > 0 and len(note_urls) >= max_notes:
                                break
                        if max_notes > 0 and len(note_urls) >= max_notes:
                            break
                except Exception as e:
                    print(f"选择器 {selector} 处理出错: {e}")
                    continue
            
            # 检查是否找到了新内容
            if len(note_urls) > current_count:
                print(f"✅ 滚动第 {scroll_attempts + 1} 次，新增 {len(note_urls) - current_count} 个链接，总计 {len(note_urls)} 个")
                previous_count = len(note_urls)
                no_new_content_count = 0  # 重置无新内容计数
            else:
                no_new_content_count += 1
                print(f"⚠️ 滚动第 {scroll_attempts + 1} 次，未发现新内容 (连续 {no_new_content_count} 次)")
                
                # 如果连续5次没有新内容，可能已经到底了
                if no_new_content_count >= 5:
                    print("连续5次未发现新内容，可能已到达页面底部，停止滚动")
                    break
            
            scroll_attempts += 1
            
            # 如果设置了最大笔记数且已达到，停止滚动
            if max_notes > 0 and len(note_urls) >= max_notes:
                print(f"已达到最大笔记数限制 ({max_notes})，停止滚动")
                break

        # 统计链接类型
        user_profile_links = [url for url in note_urls if "/user/profile/" in url]
        explore_links = [url for url in note_urls if "/explore/" in url]
        
        print(f"共获取到 {len(note_urls)} 个笔记链接：")
        print(f"  - 用户主页格式: {len(user_profile_links)} 个")
        print(f"  - 探索页格式: {len(explore_links)} 个")
        
        # 保存到缓存文件
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(note_urls, f, ensure_ascii=False, indent=2)
            print(f"✅ 笔记链接已保存到缓存文件: {cache_file}")
        except Exception as e:
            print(f"保存缓存文件失败: {e}")
        
        await page.close()
        return note_urls

    async def _search_notes_by_keyword(self, keyword, max_notes=0, context=None, use_cache=True):
        """
        按关键词搜索笔记链接
        """
        if context is None:
            raise ValueError("context 参数不能为空")
        
        # 定义缓存文件路径
        cache_file = f"D:/小红书文案2/代码/支线/教育/xiaohongshu/search_{keyword}_urls_cache.json"
        # 定义输出文件名
        output_file = f"D:/小红书文案2/文案/教育/原始文案/{keyword}文案.json"
        links_file = f"D:/小红书文案2/代码/支线/教育/{keyword}文案_links.json"  # 正确的链接文件路径
        
        # 第一步：检查链接文件是否存在
        existing_links = []
        if os.path.exists(links_file):
            try:
                with open(links_file, 'r', encoding='utf-8') as f:
                    existing_links = json.load(f)
                    if isinstance(existing_links, list):
                        print(f"✅ 从链接文件{links_file}读取到 {len(existing_links)} 个笔记链接")
                    else:
                        existing_links = []
            except Exception as e:
                print(f"读取链接文件失败: {e}")
                existing_links = []
        else:
            print(f"❌ 链接文件 {links_file} 不存在")
        
        # 如果链接文件存在且有内容，执行增量更新检查
        if existing_links:
            print("开始检查是否有新笔记...")
            # 构造搜索URL
            search_url = f"{BASE_URL}/search_result?keyword={keyword}"
            
            page = await context.new_page()
            await page.goto(search_url)
            await page.wait_for_timeout(LOGIN_WAIT_TIME)

            # 检查是否需要登录
            await self._check_login_required(page, context)

            # 尝试点击"笔记"Tab（如果存在）
            await self._click_tab(page, "div.channel[title='笔记'], div.channel:has-text('笔记')", "笔记")

            # 获取搜索结果中的笔记链接（只获取第一页检查是否有新内容）
            new_links = []
            found_existing = False
            
            # 尝试多种选择器来获取笔记链接
            selectors = [
                "a.cover.mask.ld[href]",  # 搜索结果页面的主要选择器
                ".note-item a[href]",
                ".feeds-container a[href]"
            ]
            
            for selector in selectors:
                try:
                    cards = await page.query_selector_all(selector)
                    if cards:
                        print(f"使用选择器 {selector} 找到 {len(cards)} 个元素")
                        for card in cards:
                            href = await card.get_attribute("href")
                            # 对于搜索结果，我们只保留符合要求的链接
                            if href and "/search_result/" in href and "?" in href:
                                # 确保是完整的绝对链接
                                if href.startswith("http"):
                                    normalized = href
                                else:
                                    normalized = f"{BASE_URL}{href}"
                                
                                # 检查是否是新链接
                                if normalized not in existing_links:
                                    new_links.append(normalized)
                                    print(f"  + 发现新链接: {normalized}")
                                else:
                                    # 遇到已存在的链接，说明没有新内容了
                                    found_existing = True
                                    print(f"  + 遇到已存在的链接，停止检查")
                                    break
                        if new_links or found_existing:
                            break
                except Exception as e:
                    print(f"选择器 {selector} 失败: {e}")
                    continue
                
                # 如果找到已存在的链接，停止检查
                if found_existing:
                    break
            
            await page.close()
            
            # 如果有新链接，更新链接文件
            if new_links:
                print(f"发现 {len(new_links)} 个新链接，正在更新链接文件...")
                updated_links = new_links + existing_links
                self._save_links_to_json(updated_links, links_file)
                print(f"✅ 链接文件已更新，现在共有 {len(updated_links)} 个链接")
                return updated_links
            else:
                print("未发现新链接，使用现有链接文件")
                return existing_links
        
        # 如果链接文件不存在或为空，执行完整获取
        print("链接文件不存在或为空，执行完整链接获取...")
        
        # 如果启用缓存且缓存文件存在，则直接读取
        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if isinstance(cached_data, list):
                        print(f"✅ 从缓存文件读取到 {len(cached_data)} 个搜索结果链接")
                        # 保存到链接文件
                        self._save_links_to_json(cached_data, links_file)
                        return cached_data[:max_notes] if max_notes > 0 else cached_data
            except Exception as e:
                print(f"读取缓存文件失败: {e}")
            
        # 构造搜索URL
        search_url = f"{BASE_URL}/search_result?keyword={keyword}"
        
        page = await context.new_page()
        await page.goto(search_url)
        await page.wait_for_timeout(LOGIN_WAIT_TIME)

        # 检查是否需要登录
        await self._check_login_required(page, context)

        # 尝试点击"笔记"Tab（如果存在）
        await self._click_tab(page, "div.channel[title='笔记'], div.channel:has-text('笔记')", "笔记")

        # 获取搜索结果中的笔记链接
        note_urls = []
        
        # 尝试多种选择器来获取笔记链接
        selectors = [
            "a.cover.mask.ld[href]",  # 搜索结果页面的主要选择器
            ".note-item a[href]",
            ".feeds-container a[href]"
        ]
        
        for selector in selectors:
            try:
                cards = await page.query_selector_all(selector)
                if cards:
                    print(f"使用选择器 {selector} 找到 {len(cards)} 个元素")
                    for card in cards:
                        href = await card.get_attribute("href")
                        # 对于搜索结果，我们只保留符合要求的链接
                        if href and "/search_result/" in href and "?" in href:
                            # 确保是完整的绝对链接
                            if href.startswith("http"):
                                normalized = href
                            else:
                                normalized = f"{BASE_URL}{href}"
                            
                            if normalized not in note_urls:
                                note_urls.append(normalized)
                                print(f"  + 获取到搜索结果链接: {normalized}")
                        if max_notes > 0 and len(note_urls) >= max_notes:
                            break
                    if note_urls:
                        break
            except Exception as e:
                print(f"选择器 {selector} 失败: {e}")
                continue

        # 滚动加载更多内容
        print("开始滚动加载更多搜索结果...")
        previous_count = len(note_urls)
        scroll_attempts = 0
        max_scroll_attempts = 100  # 增加滚动次数
        no_new_content_count = 0  # 连续无新内容的次数
        
        while scroll_attempts < max_scroll_attempts:
            # 滚动页面
            await self._scroll_page(page)

            # 再次尝试获取链接
            current_count = len(note_urls)
            for selector in selectors:
                try:
                    cards = await page.query_selector_all(selector)
                    if cards:
                        for card in cards:
                            href = await card.get_attribute("href")
                            # 对于搜索结果，我们只保留符合要求的链接
                            if href and "/search_result/" in href and "?" in href:
                                # 确保是完整的绝对链接
                                if href.startswith("http"):
                                    normalized = href
                                else:
                                    normalized = f"{BASE_URL}{href}"
                                
                                if normalized not in note_urls:
                                    note_urls.append(normalized)
                                    print(f"  + 新增搜索结果链接: {normalized}")
                            if max_notes > 0 and len(note_urls) >= max_notes:
                                break
                        if max_notes > 0 and len(note_urls) >= max_notes:
                            break
                except Exception as e:
                    print(f"选择器 {selector} 处理出错: {e}")
                    continue
            
            # 检查是否找到了新内容
            if len(note_urls) > current_count:
                print(f"✅ 滚动第 {scroll_attempts + 1} 次，新增 {len(note_urls) - current_count} 个链接，总计 {len(note_urls)} 个")
                previous_count = len(note_urls)
                no_new_content_count = 0
            else:
                no_new_content_count += 1
                print(f"⚠️ 滚动第 {scroll_attempts + 1} 次，未发现新内容 (连续 {no_new_content_count} 次)")
                
                # 如果连续5次没有新内容，可能已经到底了
                if no_new_content_count >= 5:
                    print("连续5次未发现新内容，可能已到达页面底部，停止滚动")
                    break
            
            scroll_attempts += 1
            
            # 如果设置了最大笔记数且已达到，停止滚动
            if max_notes > 0 and len(note_urls) >= max_notes:
                print(f"已达到最大笔记数限制 ({max_notes})，停止滚动")
                break

        print(f"共获取到 {len(note_urls)} 个搜索结果链接")
        
        # 保存到缓存文件和链接文件
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(note_urls, f, ensure_ascii=False, indent=2)
            print(f"✅ 搜索结果链接已保存到缓存文件: {cache_file}")
            
            # 同时保存到链接文件
            self._save_links_to_json(note_urls, links_file)
        except Exception as e:
            print(f"保存缓存文件失败: {e}")
        
        await page.close()
        return note_urls

    async def _crawl_notes_content(self, note_urls, output_file, use_cache=True):
        """
        爬取笔记内容并保存到JSON文件
        """
        # 链接文件名
        links_file = output_file.replace(".json", "_links.json").replace(
            "D:/小红书文案2/文案/教育/原始文案/", 
            "D:/小红书文案2/代码/支线/教育/"
        )
        
        # 保存所有链接到JSON文件
        self._save_links_to_json(note_urls, links_file)
        
        # 通过检查JSON文件中的文案数量来判断已处理的文案数量
        written_count = 0
        if os.path.exists(output_file):
            written_count = self._count_notes_in_doc(output_file)
            print(f"从现有文档中检测到 {written_count} 篇已处理的文案")
        
        # 过滤掉已经处理过的URL（基于文档中的内容数量）
        remaining_urls = note_urls[written_count:] if written_count < len(note_urls) else []
        print(f"总共有 {len(note_urls)} 个链接，其中 {len(remaining_urls)} 个尚未处理")
        
        # 初始化JSON数据
        notes_data = []
        
        # 如果有已处理的内容，先加载现有的文档
        if written_count > 0 and os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    notes_data = json.load(f)
                print(f"✅ 从现有文档继续: {output_file}")
            except Exception as e:
                print(f"加载现有文档失败，将创建新文档: {e}")
                notes_data = []

        # 创建浏览器上下文时加载cookie
        async with async_playwright() as p:
            # 检查cookie文件是否存在，如果存在则加载
            if os.path.exists(self.cookie_file_path):
                browser = await p.chromium.launch_persistent_context(
                    self.user_data_dir, 
                    headless=False
                )
                # 加载cookie
                cookies = self._load_cookies()
                if cookies:
                    await browser.add_cookies(cookies)
                print(f"已加载cookie文件: {self.cookie_file_path}")
            else:
                browser = await p.chromium.launch_persistent_context(
                    self.user_data_dir, 
                    headless=False
                )
                print("未找到cookie文件，将创建新的浏览器上下文")
            
            for i, url in enumerate(remaining_urls, 1):
                print(f"正在获取第 {i}/{len(remaining_urls)} 篇笔记: {url}")
                
                # 尝试获取内容，最多重试3次
                content = None
                for retry in range(3):
                    try:
                        content = await self._get_note_text(url, browser)
                        if content and content.strip():
                            break
                        else:
                            print(f"  重试 {retry + 1}/3: 内容为空")
                    except Exception as e:
                        print(f"  重试 {retry + 1}/3: 获取失败 - {e}")
                        if retry < 2:  # 不是最后一次重试
                            await asyncio.sleep(3)  # 重试前多等一会
                
                text = (content or "").strip()
                if text and text != "未找到文案" and text != "获取失败":
                    # 添加到JSON数据中
                    notes_data.append(text)
                    print(f"  ✅ 成功获取文案，长度: {len(text)} 字符")
                    
                    # 立即保存，保证意外中断也能保留已写内容
                    try:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(notes_data, f, ensure_ascii=False, indent=2)
                        print(f"  📝 已保存到 {output_file}")
                    except Exception as e:
                        print(f"  ❌ 保存失败: {e}")

                    # 显示进度
                    current_written_count = written_count + i
                    print(f"  📝 已写入 {current_written_count} 篇文案")
                else:
                    print(f"  ❌ 获取失败，跳过此笔记")

                # 避免请求过快，增加延迟到5秒
                print("⏳ 等待5秒避免请求过于频繁...")
                await asyncio.sleep(5)

            await browser.close()

        print(f"\n✅ 任务完成！")
        print(f"📄 JSON文档已保存: {output_file}")
        print(f"🔗 链接文件已保存: {links_file}")
        print(f"📊 共处理了 {written_count + len(remaining_urls)} 篇笔记")
        return True

    def _count_notes_in_doc(self, doc_file):
        """计算JSON文档中的文案数量"""
        try:
            if os.path.exists(doc_file):
                with open(doc_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return len(data)
            return 0
        except Exception as e:
            print(f"读取JSON文档失败: {e}")
            return 0

    async def _get_note_text(self, url, context):
        """
        获取单个笔记的文案内容
        """
        try:
            page = await context.new_page()
            await page.goto(url)
            await page.wait_for_timeout(DEFAULT_WAIT_TIME)  # 等待页面加载

            # 检查是否需要登录
            await self._check_login_required(page, context)

            # 尝试获取笔记内容
            content = ""
            
            # 尝试多种选择器来获取笔记内容
            selectors = [
                "div.note-content",  # 主要内容选择器
                "div.desc",          # 描述内容选择器
                "div.note-text",     # 笔记文本选择器
                "article",           # 文章选择器
                "div.content"        # 内容选择器
            ]
            
            for selector in selectors:
                try:
                    content_element = await page.query_selector(selector)
                    if content_element:
                        content = await content_element.inner_text()
                        if content and content.strip():
                            print(f"  使用选择器 {selector} 成功获取内容，长度: {len(content)} 字符")
                            break
                except Exception as e:
                    print(f"  选择器 {selector} 获取内容失败: {e}")
                    continue
            
            await page.close()
            
            if content and content.strip():
                return content.strip()
            else:
                return "未找到文案"
                
        except Exception as e:
            print(f"获取笔记内容失败: {e}")
            return "获取失败"

    def _save_cookies(self, cookies):
        """保存cookie到文件"""
        try:
            with open(self.cookie_file_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            print(f"✅ Cookie已保存到: {self.cookie_file_path}")
        except Exception as e:
            print(f"保存cookie到文件失败: {e}")

    def _save_links_to_json(self, links, json_file):
        """
        将链接保存到JSON文件
        """
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(links, f, ensure_ascii=False, indent=2)
            print(f"🔗 链接已保存到: {json_file}")
        except Exception as e:
            print(f"保存链接到JSON文件失败: {e}")

    async def crawl(self, keyword="", user_profile_url="", max_notes=0, output_file=None, use_cache=True):
        """
        主方法：根据模式爬取小红书笔记并生成JSON文档
        
        Args:
            keyword (str): 搜索关键词（关键词模式下使用）
            user_profile_url (str): 用户主页URL（用户模式下使用）
            max_notes (int): 最大笔记数量，0表示不限制
            output_file (str): 输出文件名
            use_cache (bool): 是否使用缓存
            
        Returns:
            bool: 是否成功完成爬取
        """
        if self.mode == "keyword":
            if not keyword:
                raise ValueError("关键词模式下必须提供 keyword 参数")
            
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"{keyword}文案_{timestamp}.json"
            # 确保输出文件是JSON格式
            elif not output_file.endswith('.json'):
                output_file = output_file.replace('.docx', '.json')
            
            print(f"按关键词搜索模式: {keyword}")
            
            async with async_playwright() as p:
                # 检查cookie文件是否存在，如果存在则加载
                if os.path.exists(self.cookie_file_path):
                    browser = await p.chromium.launch_persistent_context(
                        self.user_data_dir, 
                        headless=False
                    )
                    # 加载cookie
                    cookies = self._load_cookies()
                    if cookies:
                        await browser.add_cookies(cookies)
                    print(f"已加载cookie文件: {self.cookie_file_path}")
                else:
                    browser = await p.chromium.launch_persistent_context(
                        self.user_data_dir, 
                        headless=False
                    )
                    print("未找到cookie文件，将创建新的浏览器上下文")
                
                # 获取搜索结果中的笔记链接
                note_urls = await self._search_notes_by_keyword(keyword, max_notes, browser, use_cache=use_cache)
                
                if not note_urls:
                    print("未找到任何笔记链接，请检查关键词或登录状态")
                    await browser.close()
                    return False
                
                await browser.close()
                # 爬取笔记内容并保存到JSON文档
                return await self._crawl_notes_content(note_urls, output_file, use_cache)
                
        elif self.mode == "user":
            if not user_profile_url:
                raise ValueError("用户主页模式下必须提供 user_profile_url 参数")
            
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"D:/小红书文案2/文案/教育/原始文案/小红书笔记合集_{timestamp}.json"
            # 确保输出文件是JSON格式
            elif not output_file.endswith('.json'):
                output_file = output_file.replace('.docx', '.json')
            
            print(f"用户主页爬取模式: {user_profile_url}")
            
            async with async_playwright() as p:
                # 检查cookie文件是否存在，如果存在则加载
                if os.path.exists(self.cookie_file_path):
                    browser = await p.chromium.launch_persistent_context(
                        self.user_data_dir, 
                        headless=False
                    )
                    # 加载cookie
                    cookies = self._load_cookies()
                    if cookies:
                        await browser.add_cookies(cookies)
                    print(f"已加载cookie文件: {self.cookie_file_path}")
                else:
                    browser = await p.chromium.launch_persistent_context(
                        self.user_data_dir, 
                        headless=False
                    )
                    print("未找到cookie文件，将创建新的浏览器上下文")
                
                # 获取笔记链接
                note_urls = await self._get_user_notes_from_profile(user_profile_url, max_notes, browser, use_cache=use_cache)

                if not note_urls:
                    print("未找到任何笔记链接，请检查用户主页URL或登录状态")
                    await browser.close()
                    return False
                
                await browser.close()
                # 爬取笔记内容并保存到JSON文档
                return await self._crawl_notes_content(note_urls, output_file, use_cache)
                
        else:
            raise ValueError(f"不支持的模式: {self.mode}，仅支持 'keyword' 或 'user'")

    def _load_cookies(self):
        """加载cookie文件"""
        try:
            if os.path.exists(self.cookie_file_path):
                with open(self.cookie_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 检查数据格式，如果是storage_state格式，则提取cookies
                    if isinstance(data, dict) and 'cookies' in data:
                        return data['cookies']
                    elif isinstance(data, list):
                        return data
            return []
        except Exception as e:
            print(f"加载cookie文件失败: {e}")
            return []

# 使用示例
if __name__ == "__main__":
    # 在这里设置参数
    # 如果 SEARCH_KEYWORD 有内容，则按关键词搜索；否则按 USER_PROFILE_URL 爬取用户笔记
    SEARCH_KEYWORD = "小升初"  # 在这里填写搜索关键词，如 "儿科"
    USER_PROFILE_URL = ""
    
    MAX_NOTES = 0  # 设置为0表示爬取所有笔记，设置具体数字可限制数量
    USE_CACHE = True  # 是否使用缓存文件
    
    # 创建爬虫实例并执行爬取
    if SEARCH_KEYWORD:
        # 按关键词搜索模式
        OUTPUT_FILE = "D:/小红书文案2/文案/教育/原始文案/小升初文案.json"  # 输出文件名改为JSON格式
        crawler = XiaohongshuCrawler(mode="keyword")
        asyncio.run(crawler.crawl(
            keyword=SEARCH_KEYWORD,
            max_notes=MAX_NOTES,
            output_file=OUTPUT_FILE,
            use_cache=USE_CACHE
        ))
    else:
        # 用户主页爬取模式
        OUTPUT_FILE = "D:/小红书文案2/文案/教育/原始文案/小红书笔记合集.json"  # 输出文件名改为JSON格式
        crawler = XiaohongshuCrawler(mode="user")
        asyncio.run(crawler.crawl(
            user_profile_url=USER_PROFILE_URL,
            max_notes=MAX_NOTES,
            output_file=OUTPUT_FILE,
            use_cache=USE_CACHE
        ))
