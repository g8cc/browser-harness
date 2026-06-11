"""Agent-editable browser helpers.

Add task-specific browser primitives here. Core helpers from browser_harness.helpers
load this file when BH_AGENT_WORKSPACE points at this directory, or when this
repo's default agent-workspace exists.
"""

import json
import os
import time
from pathlib import Path

# Cookies 管理
COOKIES_FILE = "/tmp/cookies.json"
COOKIES_META_FILE = "/tmp/cookies_meta.json"


def check_cookies_expired():
    """检查 cookies 是否过期（通过访问网站检测）"""
    # 先访问一个需要登录的网站
    from browser_harness.helpers import new_tab, wait_for_load, page_info
    
    new_tab("https://www.zhihu.com")
    wait_for_load()
    
    page = page_info()
    url = page.get("url", "")
    title = page.get("title", "")
    
    # 检测是否跳转到登录页面
    if "signin" in url or "登录" in title or "login" in url:
        return True, "知乎"
    
    return False, None


def remind_sync_cookies(site_name="网站"):
    """提醒用户同步 cookies"""
    print(f"⚠️  COOKIES_EXPIRED: {site_name} 登录状态失效")
    print("请按以下步骤操作：")
    print("1. 在主浏览器中打开并登录该网站")
    print("2. 告诉我 '已登录'")
    print("3. 我会自动同步 cookies")


def get_cookies_from_main_browser(url="https://www.zhihu.com"):
    """从主浏览器获取指定网站的 cookies"""
    from browser_harness.helpers import new_tab, wait_for_load, cdp
    
    new_tab(url)
    wait_for_load()
    
    cookies = cdp("Network.getCookies")
    cookie_list = cookies.get("cookies", [])
    
    if cookie_list:
        # 保存到文件
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f)
        
        # 保存元数据
        meta = {
            "sync_time": time.time(),
            "url": url,
            "count": len(cookie_list)
        }
        with open(COOKIES_META_FILE, "w") as f:
            json.dump(meta, f)
        
        print(f"✅ 获取到 {len(cookie_list)} 个 cookies")
        return True
    else:
        print("❌ 未获取到 cookies")
        return False


def sync_cookies_to_ai_browser():
    """将 cookies 同步到 AI 浏览器"""
    from browser_harness.helpers import cdp
    
    if not os.path.exists(COOKIES_FILE):
        print("❌ 未找到 cookies 文件，请先获取")
        return False
    
    with open(COOKIES_FILE, "r") as f:
        cookies = json.load(f)
    
    cookie_list = cookies.get("cookies", [])
    
    # 设置 cookies
    for cookie in cookie_list:
        try:
            cdp("Network.setCookie", 
                name=cookie["name"],
                value=cookie["value"],
                domain=cookie.get("domain", ""),
                path=cookie.get("path", "/"),
                secure=cookie.get("secure", False),
                httpOnly=cookie.get("httpOnly", False))
        except Exception as e:
            # 忽略单个 cookie 设置失败
            pass
    
    print(f"✅ 已同步 {len(cookie_list)} 个 cookies 到 AI 浏览器")
    return True


def auto_sync_workflow():
    """自动同步工作流"""
    print("🔄 开始检查 cookies 状态...")
    
    # 检查是否过期
    expired, site_name = check_cookies_expired()
    
    if expired:
        remind_sync_cookies(site_name)
        return False
    else:
        print("✅ cookies 仍然有效")
        return True


def setup_auto_sync():
    """设置自动同步（在操作失败时调用）"""
    print("📋 自动同步已设置")
    print("当检测到登录状态失效时，会提醒您重新登录并同步 cookies")


# ============================================================
# Daemon 会话健康检查和自动恢复
# ============================================================

def check_daemon_health():
    """检查 daemon 会话是否健康"""
    from browser_harness.helpers import page_info, ensure_real_tab
    
    try:
        page = page_info()
        url = page.get("url", "")
        
        # 检测是否是内部页面（daemon 会话过期的标志）
        if url.startswith("chrome://") or url.startswith("chrome-extension://"):
            print("⚠️  Daemon 会话可能过期，正在恢复...")
            ensure_real_tab()
            page = page_info()
            url = page.get("url", "")
            
            if url.startswith("chrome://") or url.startswith("chrome-extension://"):
                print("❌ Daemon 恢复失败")
                return False
            else:
                print("✅ Daemon 已恢复")
                return True
        
        return True
    except Exception as e:
        print(f"❌ Daemon 健康检查失败: {e}")
        return False


def safe_page_info():
    """安全获取页面信息（自动检查 daemon 健康）"""
    from browser_harness.helpers import page_info
    
    if not check_daemon_health():
        print("⚠️  Daemon 不健康，请检查浏览器连接")
        return None
    
    return page_info()


def safe_new_tab(url, max_retries=2):
    """安全打开新标签页（自动重试）"""
    from browser_harness.helpers import new_tab, wait_for_load, page_info
    
    for attempt in range(max_retries):
        try:
            new_tab(url)
            wait_for_load()
            page = page_info()
            
            # 检查是否成功加载
            if page.get("url") and not page.get("url").startswith("chrome://"):
                return page
            
            print(f"⚠️  第 {attempt + 1} 次尝试失败，重试...")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️  第 {attempt + 1} 次尝试失败: {e}")
            time.sleep(1)
    
    print(f"❌ 打开 {url} 失败")
    return None


# ============================================================
# 任务管理器（标签页生命周期）
# ============================================================

class BrowserTask:
    """浏览器任务上下文管理器"""
    
    def __init__(self, name="unnamed"):
        self.name = name
        self.tabs = []
        self.active_tab = None
    
    def new_tab(self, url):
        """打开新标签页并记录"""
        from browser_harness.helpers import new_tab, wait_for_load, page_info
        
        new_tab(url)
        wait_for_load()
        page = page_info()
        
        tab_info = {
            "url": page.get("url", url),
            "title": page.get("title", ""),
            "timestamp": time.time()
        }
        self.tabs.append(tab_info)
        self.active_tab = tab_info
        
        return page
    
    def close_tab(self):
        """关闭当前标签页"""
        from browser_harness.helpers import close_tab
        close_tab()
        
        if self.tabs:
            self.tabs.pop()
            self.active_tab = self.tabs[-1] if self.tabs else None
    
    def close_all_except(self, keep_tab_index=-1):
        """关闭所有标签页，只保留指定的"""
        from browser_harness.helpers import close_tab, switch_tab
        
        if not self.tabs:
            return
        
        keep_tab = self.tabs[keep_tab_index] if keep_tab_index < len(self.tabs) else self.tabs[-1]
        
        # 关闭其他标签页（从后往前）
        for i in range(len(self.tabs) - 1, -1, -1):
            if i != keep_tab_index:
                try:
                    # 需要先切换到该标签页才能关闭
                    switch_tab(i)
                    close_tab()
                except:
                    pass
        
        self.tabs = [keep_tab]
        self.active_tab = keep_tab
    
    def cleanup(self):
        """清理所有标签页"""
        from browser_harness.helpers import close_tab
        
        for _ in range(len(self.tabs)):
            try:
                close_tab()
            except:
                pass
        
        self.tabs = []
        self.active_tab = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 任务结束时自动清理（可选）
        pass


def browser_task(name="unnamed"):
    """创建浏览器任务上下文"""
    return BrowserTask(name)


# ============================================================
# 搜索辅助函数
# ============================================================

def search_site(base_url, keyword):
    """优先构造搜索 URL，避免交互失败"""
    import urllib.parse
    
    encoded_keyword = urllib.parse.quote(keyword)
    
    # B 站搜索（按最新发布排序）
    if "bilibili.com" in base_url:
        return f"https://search.bilibili.com/all?keyword={encoded_keyword}&order=pubdate"
    
    # 知乎搜索
    if "zhihu.com" in base_url:
        return f"https://www.zhihu.com/search?type=content&q={encoded_keyword}"
    
    # 百度搜索
    if "baidu.com" in base_url:
        return f"https://www.baidu.com/s?wd={encoded_keyword}"
    
    # Google 搜索
    if "google.com" in base_url:
        return f"https://www.google.com/search?q={encoded_keyword}"
    
    # GitHub 搜索
    if "github.com" in base_url:
        return f"https://github.com/search?q={encoded_keyword}"
    
    # 默认：返回原 URL + 搜索参数
    return f"{base_url}/search?q={encoded_keyword}"


# ============================================================
# 页面描述（截图退化方案）
# ============================================================

def describe_page():
    """当截图不可用时，用 JS 提取页面语义信息"""
    from browser_harness.helpers import js
    
    return js("""
        (() => {
            const elements = [];
            
            // 获取所有可见的文字元素
            const selectors = [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'button', 'a', 'input', 'textarea',
                'p', 'span', 'li', 'td', 'th',
                '[role="button"]', '[role="link"]',
                '[role="heading"]', '[role="menuitem"]'
            ];
            
            const seen = new Set();
            
            for (const selector of selectors) {
                try {
                    const els = document.querySelectorAll(selector);
                    for (const el of els) {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text && text.length > 0 && text.length < 200 && !seen.has(text)) {
                            seen.add(text);
                            elements.push({
                                tag: el.tagName.toLowerCase(),
                                text: text.slice(0, 100),
                                type: el.type || '',
                                href: el.href || '',
                                role: el.getAttribute('role') || ''
                            });
                        }
                    }
                } catch(e) {}
            }
            
            return elements.slice(0, 30);
        })()
    """)


def safe_text(element):
    """安全提取元素文本（自动尝试多种方式）"""
    from browser_harness.helpers import js
    
    return js(f"""
        (() => {{
            const el = document.querySelector('{element}');
            if (!el) return null;
            
            // 尝试多种方式获取文本
            const texts = [
                el.innerText,
                el.textContent,
                el.getAttribute('title'),
                el.getAttribute('aria-label'),
                el.getAttribute('placeholder'),
                el.getAttribute('alt'),
                el.value
            ];
            
            for (const text of texts) {{
                if (text && text.trim().length > 0) {{
                    return text.trim();
                }}
            }}
            
            return null;
        }})
    """)


# ============================================================
# B 站专门处理
# ============================================================

def bilibili_search(keyword):
    """B 站搜索（优先使用 API）"""
    from browser_harness.helpers import http_get
    
    try:
        # 使用 B 站搜索 API
        url = f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={keyword}"
        result = http_get(url)
        
        if result and result.get("data"):
            return result["data"]
    except:
        pass
    
    # 降级到普通搜索
    return None


def bilibili_get_video_info(bvid):
    """获取 B 站视频信息"""
    from browser_harness.helpers import http_get
    
    try:
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        result = http_get(url)
        
        if result and result.get("data"):
            return result["data"]
    except:
        pass
    
    return None

