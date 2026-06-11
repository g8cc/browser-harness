#!/bin/bash
# 自动提醒脚本
# 当 cookies 过期时提醒用户

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="/Users/wardonguo/Documents/work/code/AI/AIworkspace/browser-harness"

# 检查状态
STATUS_OUTPUT=$("$PROJECT_DIR/cookies-cli.sh" status 2>&1)

if echo "$STATUS_OUTPUT" | grep -q "STATUS=expired"; then
    SITE=$(echo "$STATUS_OUTPUT" | grep "SITE=" | cut -d'=' -f2)
    
    echo "⚠️  Cookies 过期提醒"
    echo "=================="
    echo ""
    echo "网站: $SITE"
    echo "状态: 需要重新登录"
    echo ""
    echo "请按以下步骤操作："
    echo "1. 在主浏览器中打开 $SITE 并登录"
    echo "2. 登录完成后运行: $PROJECT_DIR/cookies-cli.sh sync"
    echo "3. 或者告诉我 '已登录'，我会自动同步"
    echo ""
    echo "=================================="
    
    # 返回非零退出码表示需要处理
    exit 1
else
    echo "✅ Cookies 状态正常"
    exit 0
fi