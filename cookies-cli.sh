#!/bin/bash
# Cookies 管理 CLI
# 用法: ./cookies-cli.sh [check|sync|status]

set -e

ACTION=${1:-"check"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case $ACTION in
    "check")
        echo "检查 cookies 状态..."
        browser-harness <<'PY'
import sys
sys.path.insert(0, '/Users/wardonguo/Documents/work/code/AI/AIworkspace/browser-harness/agent-workspace')
from agent_helpers import check_cookies_expired, remind_sync_cookies

expired, site = check_cookies_expired()
if expired:
    remind_sync_cookies(site)
    print(f"EXPIRED=true")
    print(f"SITE={site}")
    exit(1)
else:
    print("EXPIRED=false")
    print("STATUS=valid")
PY
        ;;
    
    "sync")
        echo "同步 cookies..."
        browser-harness <<'PY'
import sys
sys.path.insert(0, '/Users/wardonguo/Documents/work/code/AI/AIworkspace/browser-harness/agent-workspace')
from agent_helpers import get_cookies_from_main_browser, sync_cookies_to_ai_browser

# 先检查状态
from agent_helpers import check_cookies_expired
expired, site = check_cookies_expired()

if expired:
    print(f"ERROR: {site} 需要先在主浏览器登录")
    print("EXPIRED=true")
    exit(1)

# 获取并同步
success = get_cookies_from_main_browser("https://www.zhihu.com")
if success:
    sync_cookies_to_ai_browser()
    print("SYNC=success")
    print("STATUS=ready")
else:
    print("SYNC=failed")
    exit(1)
PY
        ;;
    
    "status")
        echo "获取 cookies 状态..."
        browser-harness <<'PY'
import sys
sys.path.insert(0, '/Users/wardonguo/Documents/work/code/AI/AIworkspace/browser-harness/agent-workspace')
from agent_helpers import check_cookies_expired

expired, site = check_cookies_expired()
if expired:
    print("STATUS=expired")
    print(f"SITE={site}")
else:
    print("STATUS=valid")
PY
        ;;
    
    "help")
        echo "Cookies 管理 CLI"
        echo ""
        echo "用法: $0 [命令]"
        echo ""
        echo "命令:"
        echo "  check   检查 cookies 是否过期"
        echo "  sync    同步 cookies 到 AI 浏览器"
        echo "  status  获取状态（机器可读）"
        echo "  help    显示帮助"
        echo ""
        echo "示例:"
        echo "  $0 check   # 检查是否需要登录"
        echo "  $0 sync    # 同步 cookies"
        echo "  $0 status  # 获取状态"
        ;;
    
    *)
        echo "未知命令: $ACTION"
        echo "运行 '$0 help' 查看帮助"
        exit 1
        ;;
esac