#!/bin/bash
# Browser Harness Skill 示例脚本
# 展示如何使用优化后的功能

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

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

# 检查 daemon 健康状态
check_daemon_health() {
    print_info "检查 daemon 健康状态..."
    
    RESULT=$("$SCRIPT_DIR/cookies-cli.sh" health 2>&1)
    
    if echo "$RESULT" | grep -q "HEALTH=ok"; then
        print_info "Daemon 健康"
        return 0
    else
        print_warn "Daemon 不健康"
        return 1
    fi
}

# 搜索 B 站视频
search_bilibili() {
    local keyword=$1
    
    print_info "搜索 B 站: $keyword"
    
    browser-harness <<'PY'
import sys
sys.path.insert(0, 'agent-workspace')
from agent_helpers import search_site, safe_new_tab, describe_page

keyword = "$keyword"
search_url = search_site("bilibili.com", keyword)
print(f"搜索 URL: {search_url}")

page = safe_new_tab(search_url)
if page:
    print(f"搜索页已打开: {page.get('title')}")
    
    # 获取搜索结果
    elements = describe_page()
    if elements:
        print("\n搜索结果:")
        for i, el in enumerate(elements[:10]):
            if el.get('tag') == 'h3':
                print(f"  {i+1}. {el.get('text')}")
else:
    print("打开搜索页失败")
PY
}

# 打开最新视频
open_latest_video() {
    local keyword=$1
    
    print_info "打开最新视频: $keyword"
    
    browser-harness <<'PY'
import sys
sys.path.insert(0, 'agent-workspace')
from agent_helpers import search_site, safe_new_tab

keyword = "$keyword"
search_url = search_site("bilibili.com", keyword)
page = safe_new_tab(search_url)

if page:
    # 获取视频链接
    links = js("""
        Array.from(document.querySelectorAll('a[href*="/video/BV"]'))
            .map(a => ({
                href: a.href,
                text: (a.innerText || a.textContent || '').trim().slice(0, 100)
            }))
            .filter(link => link.text.length > 5 && !link.text.includes('投稿'))
            .slice(0, 5)
    """)
    
    if links:
        # 打开第一个视频（最新）
        latest = links[0]
        print(f"打开最新视频: {latest.get('text')}")
        
        video_url = latest.get('href')
        if not video_url.startswith('http'):
            video_url = 'https:' + video_url
        
        video_page = safe_new_tab(video_url)
        if video_page:
            print(f"视频已打开: {video_page.get('title')}")
        else:
            print("打开视频失败")
    else:
        print("未找到视频链接")
else:
    print("打开搜索页失败")
PY
}

# 跳转到指定时间
jump_to_time() {
    local minutes=$1
    
    print_info "跳转到 ${minutes} 分钟..."
    
    browser-harness <<'PY'
import time

minutes = $minutes
seconds = minutes * 60

result = js("""
    (() => {
        const video = document.querySelector('video');
        if (!video) return '未找到视频元素';
        
        video.currentTime = $seconds;
        video.play().catch(e => '播放失败: ' + e.message);
        
        return '已跳转到 ' + $minutes + ' 分钟';
    })()
""")

print(f"结果: {result}")
time.sleep(2)

current_time = js("document.querySelector('video')?.currentTime || 0")
print(f"当前播放时间: {int(current_time // 60)}分{int(current_time % 60)}秒")
PY
}

# 显示帮助
show_help() {
    echo "Browser Harness Skill 示例脚本"
    echo ""
    echo "用法: $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  check                 检查环境"
    echo "  health                检查 daemon 健康状态"
    echo "  search <keyword>      搜索 B 站视频"
    echo "  latest <keyword>      打开最新视频"
    echo "  play <minutes>        跳转到指定时间播放"
    echo "  help                  显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 check"
    echo "  $0 health"
    echo "  $0 search 课代表立正"
    echo "  $0 latest 课代表立正"
    echo "  $0 play 12"
}

# 主函数
main() {
    case "${1:-help}" in
        "check")
            check_browser_harness
            check_daemon_health
            ;;
        "health")
            check_daemon_health
            ;;
        "search")
            if [ -z "$2" ]; then
                print_error "请提供搜索关键词"
                exit 1
            fi
            search_bilibili "$2"
            ;;
        "latest")
            if [ -z "$2" ]; then
                print_error "请提供搜索关键词"
                exit 1
            fi
            open_latest_video "$2"
            ;;
        "play")
            if [ -z "$2" ]; then
                print_error "请提供时间（分钟）"
                exit 1
            fi
            jump_to_time "$2"
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