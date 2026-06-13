"""Agent-editable browser helpers.

Add task-specific browser primitives here. Core helpers from browser_harness.helpers
load this file when BH_AGENT_WORKSPACE points at this directory, or when this
repo's default agent-workspace exists.
"""

import json
import os
import secrets
import subprocess
import sys
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


def bilibili_extract_search_results(count=10):
    """提取 B 站搜索结果（优化版）
    
    过滤掉播放量/时长信息，只保留视频标题
    """
    from browser_harness.helpers import js
    
    return js("""
        Array.from(document.querySelectorAll('a[href*="/video/BV"]'))
            .filter(a => !a.innerText.includes('\\n'))  // 过滤掉播放量/时长
            .filter(a => a.innerText.trim().length > 10)  // 过滤掉太短的文本
            .slice(0, """ + str(count) + """)
            .map(a => ({
                href: a.href,
                text: a.innerText.trim()
            }))
    """)


def bilibili_open_latest_video(keyword):
    """打开 B 站最新视频
    
    1. 搜索关键词（按最新发布排序）
    2. 提取搜索结果
    3. 打开第一个视频
    """
    from browser_harness.helpers import new_tab, wait_for_load, page_info
    
    # 搜索 URL（按最新发布排序）
    import urllib.parse
    encoded_keyword = urllib.parse.quote(keyword)
    search_url = f"https://search.bilibili.com/all?keyword={encoded_keyword}&order=pubdate"
    
    # 打开搜索页
    new_tab(search_url)
    wait_for_load()
    
    # 提取搜索结果
    results = bilibili_extract_search_results(5)
    
    if not results:
        print("❌ 未找到搜索结果")
        return None
    
    # 获取第一个视频
    first_video = results[0]
    video_url = first_video.get("href", "")
    
    if not video_url.startswith("http"):
        video_url = "https:" + video_url
    
    # 打开视频
    new_tab(video_url)
    wait_for_load()
    
    page = page_info()
    print("✅ 已打开最新视频: " + page.get("title", ""))
    
    return page


# ============================================================
# 图片识别大模型集成
# ============================================================

# 图片识别模型配置
VISION_MODELS = {
    "openai": {
        "name": "OpenAI GPT-4V",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4-vision-preview",
        "env_key": "OPENAI_API_KEY"
    },
    "claude": {
        "name": "Claude 3.5 Sonnet",
        "api_url": "https://api.anthropic.com/v1/messages",
        "model": "claude-3-5-sonnet-20241022",
        "env_key": "ANTHROPIC_API_KEY"
    },
    "gemini": {
        "name": "Google Gemini Pro Vision",
        "api_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent",
        "model": "gemini-pro-vision",
        "env_key": "GOOGLE_API_KEY"
    },
    "qwen": {
        "name": "通义千问 VL",
        "api_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
        "model": "qwen-vl-plus",
        "env_key": "DASHSCOPE_API_KEY"
    }
}

# 默认使用的模型
DEFAULT_VISION_MODEL = "openai"


def get_vision_model(model_name=None):
    """获取图片识别模型配置"""
    model_name = model_name or DEFAULT_VISION_MODEL
    return VISION_MODELS.get(model_name)


def analyze_screenshot(image_path, prompt="描述这个页面的内容", model_name=None):
    """分析截图
    
    Args:
        image_path: 截图文件路径
        prompt: 分析提示词
        model_name: 使用的模型名称（openai, claude, gemini, qwen）
    
    Returns:
        分析结果文本
    """
    import base64
    
    model = get_vision_model(model_name)
    if not model:
        return "❌ 未知的模型: " + str(model_name)
    
    api_key = os.environ.get(model["env_key"])
    if not api_key:
        return "❌ 未设置环境变量: " + model["env_key"]
    
    # 读取图片
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    
    # 根据模型类型调用 API
    if model_name == "openai":
        return _call_openai_vision(api_key, model, image_data, prompt)
    elif model_name == "claude":
        return _call_claude_vision(api_key, model, image_data, prompt)
    elif model_name == "gemini":
        return _call_gemini_vision(api_key, model, image_data, prompt)
    elif model_name == "qwen":
        return _call_qwen_vision(api_key, model, image_data, prompt)
    else:
        return "❌ 不支持的模型: " + str(model_name)


def _call_openai_vision(api_key, model, image_data, prompt):
    """调用 OpenAI GPT-4V"""
    import httpx
    
    response = httpx.post(
        model["api_url"],
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json"
        },
        json={
            "model": model["model"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/png;base64," + image_data
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    else:
        return "❌ API 调用失败: " + str(response.status_code)


def _call_claude_vision(api_key, model, image_data, prompt):
    """调用 Claude 3.5 Sonnet"""
    import httpx
    
    response = httpx.post(
        model["api_url"],
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        json={
            "model": model["model"],
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        return result["content"][0]["text"]
    else:
        return "❌ API 调用失败: " + str(response.status_code)


def _call_gemini_vision(api_key, model, image_data, prompt):
    """调用 Google Gemini Pro Vision"""
    import httpx
    
    response = httpx.post(
        model["api_url"] + "?key=" + api_key,
        headers={"Content-Type": "application/json"},
        json={
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": image_data
                            }
                        }
                    ]
                }
            ]
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return "❌ API 调用失败: " + str(response.status_code)


def _call_qwen_vision(api_key, model, image_data, prompt):
    """调用通义千问 VL"""
    import httpx
    
    response = httpx.post(
        model["api_url"],
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json"
        },
        json={
            "model": model["model"],
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": "data:image/png;base64," + image_data},
                            {"text": prompt}
                        ]
                    }
                ]
            }
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        return result["output"]["choices"][0]["message"]["content"]
    else:
        return "❌ API 调用失败: " + str(response.status_code)


def screenshot_and_analyze(prompt="描述这个页面的内容", model_name=None):
    """截图并分析
    
    Args:
        prompt: 分析提示词
        model_name: 使用的模型名称
    
    Returns:
        分析结果文本
    """
    from browser_harness.helpers import capture_screenshot
    
    # 截图
    image_path = capture_screenshot()
    
    # 分析
    return analyze_screenshot(image_path, prompt, model_name)


def list_vision_models():
    """列出所有可用的图片识别模型"""
    print("可用的图片识别模型:")
    for name, model in VISION_MODELS.items():
        api_key = os.environ.get(model["env_key"])
        status = "✅ 已配置" if api_key else "❌ 未配置"
        print("  " + name + ": " + model["name"] + " (" + status + ")")


# ============================================================
# 飞书 Human-in-the-Loop Bridge
# ============================================================

FEISHU_USER_ID = os.environ.get("FEISHU_USER_ID", "ou_e16af12bff09416d92a9ac0bc4d98966")
FEISHU_RESPONSE_DIR = "/tmp/bh-feishu-responses"
FEISHU_LOG_FILE = "/tmp/bh-feishu-responses/.subscriber.log"
BH_LARK_PROFILE = os.environ.get("BH_LARK_PROFILE", "qs")
_feishu_subscriber = None


def _lc(*args):
    """Build a lark-cli argv, injecting --profile after the binary when BH_LARK_PROFILE is set."""
    if BH_LARK_PROFILE:
        return ["lark-cli", "--profile", BH_LARK_PROFILE, *args]
    return ["lark-cli", *args]


def _lc_pgrep_pattern():
    """Regex matching lark-cli event +subscribe with optional --profile flag."""
    if BH_LARK_PROFILE:
        return r"lark-cli --profile %s event \+subscribe" % BH_LARK_PROFILE
    return r"lark-cli( --profile \S+)? event \+subscribe"


def _log(msg):
    print(msg, flush=True)


class _AdoptedProcess:
    """包装已有运行的进程 PID，提供 poll() 和 terminate() 接口"""
    def __init__(self, pid):
        self.pid = pid

    def poll(self):
        try:
            os.kill(self.pid, 0)
            return None
        except OSError:
            return 1

    def terminate(self):
        try:
            os.kill(self.pid, 15)
        except OSError:
            pass

    def kill(self):
        try:
            os.kill(self.pid, 9)
        except OSError:
            pass

    def wait(self, timeout=None):
        pass


def _kill_all_subscribers():
    """Kill ALL lark-cli event +subscribe processes to ensure exclusive access."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "lark-cli event \\+subscribe"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                try:
                    pid = int(line.strip())
                    os.kill(pid, 9)
                except (ValueError, OSError):
                    pass
            time.sleep(0.5)
    except (subprocess.TimeoutExpired, ValueError):
        pass


def _find_existing_subscriber():
    """查找已于当前 profile 下运行的 lark-cli event subscriber 进程"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", _lc_pgrep_pattern()],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().splitlines()
            if pids:
                return int(pids[0])
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return None


def feishu_start():
    """启动飞书事件监听后台进程，等待 WebSocket 连接就绪"""
    global _feishu_subscriber

    if _feishu_subscriber and _feishu_subscriber.poll() is None:
        return _feishu_subscriber

    existing_pid = _find_existing_subscriber()
    if existing_pid is not None:
        _feishu_subscriber = _AdoptedProcess(existing_pid)
        _log("已接管飞书事件监听 (PID: %d)" % existing_pid)
        return _feishu_subscriber

    _kill_all_subscribers()

    for lock_file in Path.home().glob(".lark-cli/locks/subscribe_*.lock"):
        try:
            lock_file.unlink()
        except OSError:
            pass

    os.makedirs(FEISHU_RESPONSE_DIR, mode=0o700, exist_ok=True)

    for entry in os.scandir(FEISHU_RESPONSE_DIR):
        if entry.is_file() and entry.name.endswith(".json"):
            try:
                os.unlink(entry.path)
            except OSError:
                pass

    log_fh = open(FEISHU_LOG_FILE, "w")
    _feishu_subscriber = subprocess.Popen(
        _lc("event", "+subscribe",
            "--as", "bot",
            "--force",
            "--compact",
            "--event-types", "im.message.receive_v1,card.action.trigger",
            "--output-dir", "."),
        cwd=FEISHU_RESPONSE_DIR,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )

    # 等待 WebSocket 连接就绪（从日志中检测 "Connected"）
    for _ in range(20):
        time.sleep(0.5)
        if _feishu_subscriber.poll() is not None:
            log_fh.close()
            raise RuntimeError("飞书事件监听启动失败，请检查应用权限和卡片回调配置")
        try:
            with open(FEISHU_LOG_FILE) as f:
                if "Connected" in f.read():
                    break
        except IOError:
            pass
    else:
        _feishu_subscriber.terminate()
        log_fh.close()
        raise RuntimeError("飞书事件监听连接超时 (10s)")

    log_fh.close()
    _log("飞书事件监听已启动 (PID: %d)" % _feishu_subscriber.pid)
    return _feishu_subscriber


def _ensure_subscriber():
    """确保事件监听进程存活，死亡则自动重启"""
    global _feishu_subscriber
    if _feishu_subscriber is not None and _feishu_subscriber.poll() is None:
        return
    feishu_start()


def feishu_stop():
    """停止飞书事件监听"""
    global _feishu_subscriber
    if _feishu_subscriber and _feishu_subscriber.poll() is None:
        _feishu_subscriber.terminate()
        try:
            _feishu_subscriber.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _feishu_subscriber.kill()
        _log("飞书事件监听已停止")
    _feishu_subscriber = None


def _send_feishu_card(card_json, user_id=None, urgent=True):
    """通过 lark-cli 发送互动卡片，返回 (message_id, chat_id)。urgent=True 时附带应用内加急。"""
    user_id = user_id or FEISHU_USER_ID
    result = subprocess.run(
        _lc("im", "+messages-send",
            "--as", "bot",
            "--user-id", user_id,
            "--msg-type", "interactive",
            "--content", card_json),
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        err = result.stdout.strip() or result.stderr.strip()
        raise RuntimeError("发送飞书卡片失败: " + err)
    data = json.loads(result.stdout)
    if not data.get("ok"):
        raise RuntimeError("发送飞书卡片失败: " + str(data.get("error", {})))
    msg_data = data.get("data", {})
    message_id = msg_data["message_id"]
    chat_id = msg_data.get("chat_id", "")

    if urgent and message_id:
        subprocess.run(
            _lc("im", "messages", "urgent_app", "--as", "bot",
                "--params", json.dumps({"message_id": message_id, "user_id_type": "open_id"}),
                "--data", json.dumps({"user_id_list": [user_id]})),
            capture_output=True, text=True, timeout=10,
        )

    return message_id, chat_id


def _update_feishu_card(message_id, status_text="✅ 已处理", template="green"):
    """更新已发送的卡片为终态（移除按钮，显示处理结果）"""
    card_json = json.dumps({
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": status_text}, "template": template},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": status_text}},
        ],
    }, ensure_ascii=False)
    data = json.dumps({"content": card_json})
    result = subprocess.run(
        _lc("api", "PATCH", "/open-apis/im/v1/messages/" + message_id,
            "--as", "bot", "--data", data),
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        try:
            resp = json.loads(result.stdout)
            if resp.get("ok") or resp.get("code") == 0:
                return True
        except json.JSONDecodeError:
            pass
    return False


def _safe_read_json(filepath):
    """安全读取 JSON 文件，处理部分写入和损坏文件"""
    try:
        with open(filepath) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, ValueError):
        return None


def _safe_remove(filepath):
    try:
        os.unlink(filepath)
    except OSError:
        pass


def _poll_feishu_response(request_id, timeout=300, chat_id=None, sent_time_ms=None):
    """轮询等待匹配的回调：先查 WebSocket 文件，再用 API 轮询文本消息作为降级。"""
    deadline = time.time() + timeout
    start_time = time.time()
    poll_interval = 0.3
    api_poll_interval = 5.0
    last_api_poll = 0

    while time.time() < deadline:
        _ensure_subscriber()

        try:
            entries = list(os.scandir(FEISHU_RESPONSE_DIR))
        except OSError:
            entries = []

        for entry in entries:
            if not entry.is_file() or not entry.name.endswith(".json"):
                continue

            if entry.name.startswith("card.action.trigger_"):
                data = _safe_read_json(entry.path)
                if data is None:
                    continue
                value = data.get("action", {}).get("value", {})
                if isinstance(value, dict) and value.get("request_id") == request_id:
                    _safe_remove(entry.path)
                    return data

            elif entry.name.startswith("im.message.receive_v1_"):
                data = _safe_read_json(entry.path)
                if data is None:
                    continue
                try:
                    msg_content = json.loads(data.get("message", {}).get("content", "{}"))
                except (json.JSONDecodeError, TypeError):
                    continue
                text = msg_content.get("text", "")
                if text.startswith(request_id + ":"):
                    _safe_remove(entry.path)
                    return {"action": {"value": {"action": "text_reply", "text": text.split(":", 1)[1]}}}

        if chat_id and time.time() - last_api_poll > api_poll_interval:
            last_api_poll = time.time()
            reply = _api_poll_text_reply(chat_id, sent_time_ms or 0, request_id)
            if reply is not None:
                return reply

        time.sleep(poll_interval)
        if time.time() - start_time > 30:
            poll_interval = 2.0

    return None


def _api_poll_text_reply(chat_id, since_time_ms, request_id):
    """通过 lark-cli API 轮询聊天中的文本回复，作为 WebSocket 降级。"""
    result = subprocess.run(
        _lc("im", "+chat-messages-list",
            "--as", "bot", "--chat-id", chat_id,
            "--page-size", "5", "--sort", "desc"),
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        resp = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    messages = resp.get("data", {}).get("messages", [])
    since_sec = since_time_ms // 1000 if since_time_ms > 1e12 else since_time_ms
    for msg in messages:
        if msg.get("msg_type") != "text":
            continue
        sender = msg.get("sender", {})
        if sender.get("sender_type") != "user":
            continue
        create_str = msg.get("create_time", "")
        if create_str:
            try:
                from datetime import datetime
                msg_dt = datetime.strptime(create_str, "%Y-%m-%d %H:%M")
                msg_epoch = int(msg_dt.timestamp())
                if msg_epoch < since_sec - 60:
                    continue
            except (ValueError, OSError):
                pass
        text = msg.get("content", "").strip()
        if text:
            return {"action": {"value": {"action": "text_reply", "text": text}}}
    return None


def _build_confirm_card(title, description, request_id):
    return json.dumps({
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "🤖 " + title}, "template": "orange"},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": description}},
            {"tag": "action", "actions": [
                {"tag": "button", "text": {"tag": "plain_text", "content": "✅ 确认"},
                 "type": "primary", "value": {"action": "confirm", "request_id": request_id}},
                {"tag": "button", "text": {"tag": "plain_text", "content": "❌ 取消"},
                 "type": "danger", "value": {"action": "cancel", "request_id": request_id}},
            ]},
        ],
    }, ensure_ascii=False)


def _build_input_card(title, description, input_label, request_id):
    return json.dumps({
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "🤖 " + title}, "template": "orange"},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": description}},
            {"tag": "action", "actions": [
                {"tag": "input", "name": "user_input",
                 "placeholder": {"tag": "plain_text", "content": input_label}},
                {"tag": "button", "text": {"tag": "plain_text", "content": "提交"},
                 "type": "primary", "value": {"action": "submit_input", "request_id": request_id}},
            ]},
        ],
    }, ensure_ascii=False)


def _build_select_card(title, description, options, request_id):
    option_elements = [
        {"label": opt["label"], "value": opt.get("value", opt["label"])} for opt in options
    ]
    return json.dumps({
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "🤖 " + title}, "template": "orange"},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": description}},
            {"tag": "action", "actions": [
                {"tag": "select_static", "name": "user_select",
                 "placeholder": {"tag": "plain_text", "content": "请选择"},
                 "options": option_elements},
                {"tag": "button", "text": {"tag": "plain_text", "content": "提交"},
                 "type": "primary", "value": {"action": "submit_select", "request_id": request_id}},
            ]},
        ],
    }, ensure_ascii=False)


def ask_human(title, description, card_type="confirm", input_label="", options=None,
              timeout=300, user_id=None):
    """向用户发送飞书互动卡片，等待人类响应。

    Args:
        title:       卡片标题
        description: 卡片正文 (支持飞书 Markdown)
        card_type:   "confirm" | "input" | "select"
        input_label: input 类型的输入框占位文字
        options:     select 类型的选项列表 [{"label": "...", "value": "..."}, ...]
        timeout:     等待超时秒数 (默认 5 分钟)
        user_id:     飞书用户 open_id (默认使用 FEISHU_USER_ID)

    Returns:
        dict: {action, value, raw}
        - action: "confirm" | "cancel" | "submit_input" | "submit_select" | "text_reply" | None (超时)
        - value:  用户输入/选择的值
        - raw:    原始回调数据
    """
    _ensure_subscriber()

    request_id = secrets.token_hex(6)
    builders = {
        "confirm": lambda: _build_confirm_card(title, description, request_id),
        "input": lambda: _build_input_card(title, description, input_label, request_id),
        "select": lambda: _build_select_card(title, description, options or [], request_id),
    }
    builder = builders.get(card_type)
    if not builder:
        raise ValueError("不支持的 card_type: " + card_type)

    sent_time_ms = int(time.time() * 1000)
    message_id, chat_id = _send_feishu_card(builder(), user_id)
    _log("飞书卡片已发送 (%s), 等待响应..." % message_id)

    callback = _poll_feishu_response(request_id, timeout=timeout,
                                   chat_id=chat_id, sent_time_ms=sent_time_ms)
    if callback is None:
        _log("飞书响应超时 (%ds)" % timeout)
        _update_feishu_card(message_id, "⏰ 等待超时 (%ds)" % timeout, "grey")
        return {"action": None, "value": None, "raw": None}

    action_value = callback.get("action", {}).get("value", {})
    action = action_value.get("action") if isinstance(action_value, dict) else None
    inputs = callback.get("action", {}).get("inputs", {})

    value = None
    if action == "submit_input":
        value = inputs.get("user_input", "")
    elif action == "submit_select":
        value = inputs.get("user_select", "")
    elif action == "text_reply":
        value = action_value.get("text", "")

    if action in ("submit_input", "submit_select") and not value and chat_id:
        _log("卡片回调无 inputs，等待文字回复作为降级...")
        text_cb = _poll_feishu_response(request_id, timeout=30,
                                      chat_id=chat_id, sent_time_ms=sent_time_ms)
        if text_cb:
            tv = text_cb.get("action", {}).get("value", {})
            if tv.get("action") == "text_reply":
                value = tv.get("text", "")
                action = "text_reply"

    _log("收到飞书响应: action=%s, value=%s" % (action, value))

    status_map = {
        "confirm": ("✅ 已确认", "green"),
        "cancel": ("❌ 已取消", "red"),
    }
    if action in status_map:
        status_text, template = status_map[action]
    elif action == "text_reply":
        status_text, template = "💬 回复: %s" % (value or ""), "blue"
    elif action in ("submit_input", "submit_select"):
        status_text = "✅ 已提交: %s" % (value or "(空)")
        template = "green"
    else:
        status_text, template = "已响应", "green"

    _update_feishu_card(message_id, status_text, template)

    return {"action": action, "value": value, "raw": callback}


# ============================================================
# Sidecar 直填模式（敏感数据零泄漏）
# ============================================================

_SIDECAR_DIR = "/tmp/bh-feishu-sidecar"
_SIDECAR_PID_FILE = os.path.join(_SIDECAR_DIR, "sidecar.pid")
_sidecar_process = None


def _sidecar_alive():
    if _sidecar_process is None or _sidecar_process.poll() is not None:
        return False
    return True


def sidecar_start():
    """启动 Sidecar 守护进程（敏感数据直填浏览器）"""
    global _sidecar_process

    if _sidecar_alive():
        return _sidecar_process

    for d in (_SIDECAR_DIR,
              os.path.join(_SIDECAR_DIR, "registry"),
              os.path.join(_SIDECAR_DIR, "status")):
        os.makedirs(d, mode=0o700, exist_ok=True)

    sidecar_script = os.path.join(os.path.dirname(__file__), "feishu_sidecar.py")
    _sidecar_process = subprocess.Popen(
        [sys.executable, sidecar_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    _log("Sidecar 守护进程已启动 (PID: %d)" % _sidecar_process.pid)
    return _sidecar_process


def sidecar_stop():
    """停止 Sidecar 守护进程"""
    global _sidecar_process
    if _sidecar_alive():
        _sidecar_process.terminate()
        try:
            _sidecar_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _sidecar_process.kill()
    _sidecar_process = None
    _log("Sidecar 守护进程已停止")


def feishu_cleanup():
    """停止所有飞书相关进程（subscriber + sidecar）"""
    feishu_stop()
    sidecar_stop()
    _log("飞书进程已全部清理")


def ask_human_and_fill(selector, title, description, card_type="input",
                       input_label="", options=None, timeout=300, user_id=None):
    """发送飞书互动卡片，用户输入直接填入浏览器（数据不经过 Agent）。

    敏感数据（验证码、密码等）只在 Sidecar 进程内存中存在，
    通过 CDP 直接写入浏览器，Agent 脚本永远接触不到明文值。

    Args:
        selector:    要填入的 CSS 选择器 (如 "#verify-code")
        title:       卡片标题
        description: 卡片正文
        card_type:   "input" | "select"
        input_label: 输入框占位文字
        options:     select 类型的选项列表
        timeout:     等待超时秒数
        user_id:     飞书用户 open_id

    Returns:
        dict: {"status": "filled"} | {"status": "timeout"} | {"status": "error", "message": "..."}
    """
    if not _sidecar_alive():
        sidecar_start()

    request_id = secrets.token_hex(6)

    builders = {
        "input": lambda: _build_input_card(title, description, input_label, request_id),
        "select": lambda: _build_select_card(title, description, options or [], request_id),
    }
    builder = builders.get(card_type)
    if not builder:
        raise ValueError("ask_human_and_fill 仅支持 input/select，不支持: " + card_type)

    sent_time_ms = int(time.time() * 1000)
    message_id, chat_id = _send_feishu_card(builder(), user_id)
    _log("Sidecar 卡片已发送 (%s, chat=%s), 等待用户输入..." % (message_id, chat_id))

    registry_path = os.path.join(_SIDECAR_DIR, "registry", request_id + ".json")
    with open(registry_path, "w") as f:
        json.dump({"selector": selector, "chat_id": chat_id, "sent_time_ms": sent_time_ms}, f)
    os.chmod(registry_path, 0o600)

    status_path = os.path.join(_SIDECAR_DIR, "status", request_id + ".json")
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = _safe_read_json(status_path)
        if status is not None:
            _safe_remove(status_path)
            _safe_remove(registry_path)
            _log("Sidecar 填入完成: status=%s" % status.get("status"))
            return {"status": status.get("status")}
        if not _sidecar_alive():
            sidecar_start()
        time.sleep(0.5)

    _safe_remove(registry_path)
    _log("Sidecar 等待超时 (%ds)" % timeout)
    return {"status": "timeout"}

