# Cookies 管理指南

## 概述

browser-harness 支持从主浏览器同步 cookies 到 AI 浏览器，实现无人值守操作。

## 工作流程

### 1. 首次设置

```bash
# 启动 AI 浏览器（Way 2，无弹窗）
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug \
  --remote-allow-origins="*"

# 在主浏览器登录常用网站（知乎、淘宝等）
# 告诉我 "已登录"
# 我会自动同步 cookies
```

### 2. 同步 Cookies

```bash
# 方法1：自动检测并同步
browser-harness <<'PY'
from agent_helpers import *
auto_sync_workflow()
PY

# 方法2：手动同步
browser-harness <<'PY'
from agent_helpers import *
get_cookies_from_main_browser("https://www.zhihu.com")
sync_cookies_to_ai_browser()
PY
```

### 3. 检测 Cookies 过期

```bash
browser-harness <<'PY'
from agent_helpers import *
expired, site = check_cookies_expired()
if expired:
    remind_sync_cookies(site)
else:
    print("cookies 有效")
PY
```

## 自动检测机制

在操作失败时自动检测：

```bash
browser-harness <<'PY'
from agent_helpers import *

# 尝试操作
try:
    new_tab("https://www.zhihu.com")
    wait_for_load()
    page = page_info()
    
    # 检测是否需要登录
    if "signin" in page.get("url", ""):
        remind_sync_cookies("知乎")
        # 等待用户重新登录...
except Exception as e:
    print(f"操作失败: {e}")
    auto_sync_workflow()
PY
```

## 定期同步建议

- 每周同步一次 cookies
- 登录状态过期时同步
- 更换网站时同步

## 注意事项

1. Cookies 有效期由网站决定
2. 本地同步更安全，不易被封
3. 关闭浏览器不会丢失 cookies
4. 删除 `/tmp/chrome-debug` 目录会丢失 cookies