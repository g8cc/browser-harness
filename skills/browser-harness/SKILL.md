---
name: browser-harness
description: Direct browser control via CDP. Use when the user wants to automate, scrape, test, or interact with web pages. Connects to the user's already-running Chrome.
---

# browser-harness

Direct browser control via CDP. For task-specific edits, use `agent-workspace/agent_helpers.py`. For setup, install, or connection problems, read install.md.

## Usage

```bash
browser-harness <<'PY'
new_tab("https://docs.browser-use.com")
wait_for_load()
print(page_info())
PY
```

- Invoke as browser-harness — it's on $PATH. No cd, no uv run.
- Use the heredoc form for every multi-line command. It prevents shell quote mangling inside Python strings and JavaScript snippets.
- First navigation is new_tab(url), not goto_url(url) — goto runs in the user's active tab and clobbers their work.

## Tool call shape

```bash
browser-harness <<'PY'
# any python. helpers pre-imported. daemon auto-starts.
PY
```

run.py calls ensure_daemon() before exec — you never start/stop manually unless you want to.

## Core Functions

### Navigation
- `new_tab(url)` - Open new tab
- `goto_url(url)` - Navigate current tab
- `wait_for_load()` - Wait for page load
- `close_tab()` - Close current tab
- `switch_tab()` - Switch to tab

### Interaction
- `click_at_xy(x, y)` - Click at coordinates
- `type_text("text")` - Type text
- `scroll(delta_y)` - Scroll page
- `press_key("Enter")` - Press key

### Information
- `page_info()` - Get page info
- `js("code")` - Execute JavaScript
- `capture_screenshot()` - Take screenshot

### Advanced
- `cdp("Domain.method", params)` - Raw CDP command
- `http_get(url)` - HTTP request

## Interaction skills

If you start struggling with a specific mechanic while navigating, look in `interaction-skills/` for helpers. They cover reusable UI mechanics like dialogs, tabs, dropdowns, iframes, and uploads.

**Reference**: [interaction-skills/](../interaction-skills/) for detailed guides.

## Login State Management

When accessing websites that require login, check and manage login state automatically.

**Reference**: [references/cookies-manager.md](./references/cookies-manager.md) for complete cookies management workflow.

### Quick Check

```bash
# Check if login is needed
browser-harness <<'PY'
new_tab("https://www.zhihu.com")
wait_for_load()
page = page_info()
if "signin" in page.get("url", "") or "login" in page.get("url", ""):
    print("NEED_LOGIN")
else:
    print("LOGIN_OK")
PY
```

### Auto-sync Cookies

```bash
# Use cookies-cli.sh for automatic management
./scripts/cookies-cli.sh status  # Check status
./scripts/cookies-cli.sh sync    # Sync cookies
```

## What actually works

- Screenshots first: use capture_screenshot() to understand the current page quickly, find visible targets, and decide whether you need a click, a selector, or more navigation.
- Clicking: capture_screenshot() → read the pixel off the image → click_at_xy(x, y) → capture_screenshot() to verify. Suppress the Playwright-habit reflex of "locate first, then click" — no getBoundingClientRect, no selector hunt. Drop to DOM only when the target has no visible geometry (hidden input, 0×0 node). Hit-testing happens in Chrome's browser process, so clicks go through iframes / shadow DOM / cross-origin without extra work.
- Bulk HTTP: http_get(url) + ThreadPoolExecutor. No browser for static pages (249 Netflix pages in 2.8s).
- After goto: wait_for_load().
- Wrong/stale tab: ensure_real_tab(). Use it when the current tab is stale or internal; the daemon also auto-recovers from stale sessions on the next call.
- Verification: print(page_info()) is the simplest "is this alive?" check, but screenshots are the default way to verify whether a visible action actually worked.
- DOM reads: use js(...) for inspection and extraction when the screenshot shows that coordinates are the wrong tool.
- Iframe sites (Azure blades, Salesforce): click_at_xy(x, y) passes through; only drop to iframe DOM work when coordinate clicks are the wrong tool.
- Auth wall: redirected to login → stop and ask the user. Don't type credentials from screenshots.
- Raw CDP for anything helpers don't cover: cdp("Domain.method", params).

## Best Practices

### 1. Search Priority: URL Construction

优先使用 URL 构造搜索，避免交互失败：

```bash
browser-harness <<'PY'
import sys
sys.path.insert(0, 'agent-workspace')
from agent_helpers import search_site

# 自动构造搜索 URL（B 站默认按最新发布排序）
search_url = search_site("bilibili.com", "课代表立正")
new_tab(search_url)
PY
```

### 2. Task Manager: Tab Lifecycle

使用任务管理器管理标签页生命周期：

```bash
browser-harness <<'PY'
import sys
sys.path.insert(0, 'agent-workspace')
from agent_helpers import browser_task

with browser_task("bilibili_search") as task:
    task.new_tab("https://search.bilibili.com/all?keyword=xxx&order=pubdate")
    task.new_tab("https://www.bilibili.com/video/BVxxx")
    task.close_all_except(1)  # 只保留视频标签页
PY
```

### 3. Video Playback Control

控制视频播放（跳转到指定时间）：

```bash
browser-harness <<'PY'
# 跳转到 12 分钟并播放
js("""
    const video = document.querySelector('video');
    video.currentTime = 720;  // 12分钟 = 720秒
    video.play();
""")
PY
```

### 4. Bilibili Search with Sort

B 站搜索按最新发布排序：

```bash
browser-harness <<'PY'
# 使用 URL 参数 order=pubdate 按发布时间排序
new_tab("https://search.bilibili.com/all?keyword=课代表立正&order=pubdate")
wait_for_load()
PY
```

### 5. Bilibili Search Results Extraction

提取 B 站搜索结果（过滤掉播放量/时长信息）：

```bash
browser-harness <<'PY'
import sys
sys.path.insert(0, 'agent-workspace')
from agent_helpers import bilibili_extract_search_results

# 提取搜索结果
results = bilibili_extract_search_results(10)
if results:
    for i, video in enumerate(results[:5]):
        print(str(i+1) + ". " + video.get("text"))
        print("   href: " + video.get("href"))
PY
```

**关键点**
- 播放量/时长信息包含换行符（如 "690\n2\n37:28"）
- 视频标题不包含换行符
- 使用 `!a.innerText.includes('\n')` 过滤

### 6. Bilibili Open Latest Video

打开 B 站最新视频：

```bash
browser-harness <<'PY'
import sys
sys.path.insert(0, 'agent-workspace')
from agent_helpers import bilibili_open_latest_video

# 打开最新视频
page = bilibili_open_latest_video("课代表立正")
if page:
    print("视频标题: " + page.get("title"))
PY
```

## Design constraints

- Coordinate clicks default. Input.dispatchMouseEvent goes through iframes/shadow/cross-origin at the compositor level.
- Connect to the user's running Chrome. Don't launch your own browser.
- cdp-use is only for CDPClient.send_raw. Prefer raw CDP strings over typed wrappers.
- run.py stays tiny. No argparse, subcommands, or extra control layer.
- Core helpers stay short. Put task-specific helper additions in `agent-workspace/agent_helpers.py`; daemon/bootstrap and remote session admin live in the core package.
- Don't add a manager layer. No retries framework, session manager, daemon supervisor, config system, or logging framework.

## Gotchas (field-tested)

- Omnibox popups are fake page targets. Filter chrome://omnibox-popup... and other internals when you need a real tab.
- CDP target order != Chrome's visible tab-strip order. Use UI automation when the user means "the first/second tab I can see"; Target.activateTarget only shows a known target.
- Default daemon sessions can go stale. ensure_real_tab() re-attaches to a real page.
- Browser Use API is camelCase on the wire. cdpUrl, proxyCountryCode, etc.
- Remote cdpUrl is HTTPS, not ws. Resolve the websocket URL via /json/version.
- Stop cloud browsers with PATCH /browsers/{id} + {"action":"stop"}.
- After every meaningful action, re-screenshot before assuming it worked. Use the image to verify changed state, open menus, navigation, visible errors, and whether the page is in the state you expected.
- Use screenshots to drive exploration. They are often the fastest way to find the next click target, notice hidden blockers, and decide if a selector is even worth writing.
- Prefer compositor-level actions over framework hacks. Try screenshots, coordinate clicks, and raw key input before adding DOM-specific workarounds.
- If you need framework-specific DOM tricks, check interaction-skills/ first. That is where dropdown, dialog, iframe, shadow DOM, and form-specific guidance belongs.