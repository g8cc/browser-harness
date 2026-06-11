#!/bin/bash
# Browser Harness Skill 示例脚本
# 展示如何集成到 Agent 工具中

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="/Users/wardonguo/Documents/work/code/AI/AIworkspace/browser-harness"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 browser-harness 是否可用
check_browser_harness() {
    if ! command -v browser-harness &> /dev/null; then
        print_error "browser-harness 未安装"
        print_info "请运行: cd $PROJECT_DIR && uv tool install -e ."
        exit 1
    fi
    print_info "browser-harness 可用"
}

# 检查浏览器连接
check_browser_connection() {
    print_info "检查浏览器连接..."
    
    STATUS=$(browser-harness --doctor 2>&1)
    
    if echo "$STATUS" | grep -q "daemon alive"; then
        print_info "浏览器连接正常"
        return 0
    else
        print_warn "浏览器未连接"
        print_info "请确保："
        print_info "1. Chrome 已启动"
        print_info "2. 已勾选 chrome://inspect/#remote-debugging 中的 checkbox"
        return 1
    fi
}

# 访问网站并检查登录状态
access_website() {
    local url=$1
    
    print_info "访问网站: $url"
    
    browser-harness <<'PY'
new_tab("$url")
wait_for_load()
page = page_info()
if "signin" in page.get("url", "") or "login" in page.get("url", ""):
    print("NEED_LOGIN")
else:
    print("LOGIN_OK")
PY
}

# 检查 cookies 状态
check_cookies_status() {
    print_info "检查 cookies 状态..."
    
    STATUS=$("$PROJECT_DIR/cookies-cli.sh" status 2>&1)
    
    if echo "$STATUS" | grep -q "STATUS=expired"; then
        SITE=$(echo "$STATUS" | grep "SITE=" | cut -d'=' -f2)
        print_warn "Cookies 过期: $SITE"
        return 1
    else
        print_info "Cookies 状态正常"
        return 0
    fi
}

# 同步 cookies
sync_cookies() {
    print_info "同步 cookies..."
    
    RESULT=$("$PROJECT_DIR/cookies-cli.sh" sync 2>&1)
    
    if echo "$RESULT" | grep -q "SYNC=success"; then
        print_info "Cookies 同步成功"
        return 0
    else
        print_error "Cookies 同步失败"
        return 1
    fi
}

# 完整工作流
full_workflow() {
    local url=$1
    
    print_info "开始完整工作流"
    print_info "目标网站: $url"
    
    # 1. 检查 browser-harness
    check_browser_harness
    
    # 2. 检查浏览器连接
    if ! check_browser_connection; then
        print_error "浏览器未连接，请先配置"
        exit 1
    fi
    
    # 3. 检查 cookies 状态
    if ! check_cookies_status; then
        print_warn "需要同步 cookies"
        
        # 提醒用户
        echo ""
        echo "⚠️  Cookies 过期提醒"
        echo "=================="
        echo ""
        echo "请在主浏览器中登录网站"
        echo "登录完成后告诉我 '已登录'"
        echo ""
        
        read -p "已登录? (y/n): " CONFIRM
        if [ "$CONFIRM" = "y" ]; then
            sync_cookies
        else
            print_error "未登录，无法继续"
            exit 1
        fi
    fi
    
    # 4. 访问网站
    access_website "$url"
    
    print_info "工作流完成"
}

# 显示帮助
show_help() {
    echo "Browser Harness Skill 示例脚本"
    echo ""
    echo "用法: $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  check           检查环境"
    echo "  status          检查 cookies 状态"
    echo "  sync            同步 cookies"
    echo "  access <url>    访问网站"
    echo "  workflow <url>  完整工作流"
    echo "  help            显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 check"
    echo "  $0 status"
    echo "  $0 sync"
    echo "  $0 access https://www.zhihu.com"
    echo "  $0 workflow https://www.zhihu.com"
}

# 主函数
main() {
    case "${1:-help}" in
        "check")
            check_browser_harness
            check_browser_connection
            ;;
        "status")
            check_cookies_status
            ;;
        "sync")
            sync_cookies
            ;;
        "access")
            if [ -z "$2" ]; then
                print_error "请提供 URL"
                exit 1
            fi
            access_website "$2"
            ;;
        "workflow")
            if [ -z "$2" ]; then
                print_error "请提供 URL"
                exit 1
            fi
            full_workflow "$2"
            ;;
        "help")
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"