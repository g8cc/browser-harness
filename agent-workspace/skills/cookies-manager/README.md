# Cookies Manager Skill

browser-harness 的 cookies 管理工具，支持自动检测、提醒和同步。

## 快速开始

### 1. 检查状态
```bash
./cookies-cli.sh check
```

### 2. 同步 cookies
```bash
./cookies-cli.sh sync
```

### 3. 获取状态（机器可读）
```bash
./cookies-cli.sh status
```

## Agent 集成

### 作为子进程调用

```python
import subprocess

# 检查状态
result = subprocess.run(["./cookies-cli.sh", "status"], capture_output=True, text=True)
if "expired" in result.stdout:
    print("需要重新登录")

# 同步 cookies
result = subprocess.run(["./cookies-cli.sh", "sync"], capture_output=True, text=True)
if result.returncode == 0:
    print("同步成功")
```

### 错误处理

```python
import subprocess

def check_and_sync():
    # 检查状态
    result = subprocess.run(["./cookies-cli.sh", "status"], capture_output=True, text=True)
    
    if "expired" in result.stdout:
        # 提醒用户
        print("⚠️  Cookies 过期，请在主浏览器登录")
        return False
    
    # 同步
    result = subprocess.run(["./cookies-cli.sh", "sync"], capture_output=True, text=True)
    return result.returncode == 0
```

## 输出格式

### check 命令
```
EXPIRED=true/false
SITE=网站名
STATUS=valid/expired
```

### sync 命令
```
SYNC=success/failed
STATUS=ready/need_login
```

### status 命令
```
STATUS=valid/expired
SITE=网站名（如果过期）
```

## 工作流程

1. **首次设置**
   - 启动 AI 浏览器（Way 2）
   - 在主浏览器登录网站
   - 运行 `./cookies-cli.sh sync`

2. **日常使用**
   - Agent 调用 `./cookies-cli.sh status`
   - 如果过期，提醒用户登录
   - 自动同步 cookies

3. **定期维护**
   - 每周运行一次同步
   - 或者在操作失败时自动检测

## 注意事项

- 删除 `/tmp/chrome-debug` 会丢失 cookies
- cookies 有效期由网站决定
- 本地同步更安全，不易被封