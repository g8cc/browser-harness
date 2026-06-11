---
name: cookies-manager
description: 管理 browser-harness 的 cookies 同步，支持自动检测、提醒和同步功能。当需要处理登录状态时加载此文档。
---

# Cookies Manager

管理 browser-harness 的 cookies 同步，实现无人值守浏览器操作。

## 何时加载

当遇到以下情况时，加载此文档：
- 访问需要登录的网站
- 检测到登录页面（signin, login 等）
- 需要保持登录状态
- 操作失败可能是因为登录过期

## 快速检查

```bash
# 检查 cookies 状态
./scripts/cookies-cli.sh status
```

**输出格式**
- `STATUS=valid` - cookies 有效
- `STATUS=expired` - cookies 过期
- `SITE=网站名` - 过期的网站

## 工作流程

### 1. 检测登录状态

```bash
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

### 2. 提醒用户登录

如果检测到需要登录：

```
⚠️  Cookies 过期提醒
==================
网站: 知乎
状态: 需要重新登录

请按以下步骤操作：
1. 在主浏览器中打开知乎并登录
2. 登录完成后告诉我 '已登录'
3. 我会自动同步 cookies
```

### 3. 同步 Cookies

用户登录后：

```bash
./scripts/cookies-cli.sh sync
```

**输出格式**
- `SYNC=success` - 同步成功
- `SYNC=failed` - 同步失败
- `STATUS=ready` - 可以继续操作

## 完整示例

```bash
# 1. 检查状态
STATUS=$(./scripts/cookies-cli.sh status)

if echo "$STATUS" | grep -q "STATUS=expired"; then
    # 2. 提醒用户
    SITE=$(echo "$STATUS" | grep "SITE=" | cut -d'=' -f2)
    echo "⚠️  请在主浏览器登录 $SITE"
    echo "登录完成后告诉我 '已登录'"
    
    # 3. 等待用户确认
    read -p "已登录? (y/n): " CONFIRM
    if [ "$CONFIRM" = "y" ]; then
        # 4. 同步 cookies
        ./scripts/cookies-cli.sh sync
    fi
fi
```

## CLI 工具

### 位置
```
skills/browser-harness/scripts/cookies-cli.sh
```

### 命令

```bash
# 检查状态
./scripts/cookies-cli.sh status

# 同步 cookies
./scripts/cookies-cli.sh sync

# 检查并提醒
./scripts/cookies-cli.sh check
```

## 集成到 Agent

### 方式1：在 SKILL.md 中引用

```markdown
## Login State Management

当访问需要登录的网站时，参考 [cookies-manager.md](./cookies-manager.md)。
```

### 方式2：按需加载

```python
# Agent 伪代码
def handle_website(url):
    # 尝试访问
    browser_access(url)
    
    # 检测是否需要登录
    if is_login_page():
        # 加载 cookies-manager.md
        load_skill("cookies-manager")
        
        # 执行登录流程
        manage_login()
```

## 最佳实践

1. **按需加载** - 只在需要时加载此文档
2. **自动检测** - 访问网站后自动检查登录状态
3. **用户提醒** - 过期时清晰提醒用户
4. **定期同步** - 建议每周同步一次 cookies
5. **错误处理** - 同步失败时提供解决方案

## 注意事项

- Cookies 有效期由网站决定
- 本地同步更安全，不易被封
- 删除 `/tmp/chrome-debug` 会丢失 cookies
- 不同步 localStorage、扩展、历史记录