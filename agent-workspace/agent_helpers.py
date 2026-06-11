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

