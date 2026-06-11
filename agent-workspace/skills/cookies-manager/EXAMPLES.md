# Cookies Manager 使用示例

## 1. 命令行使用

### 检查状态
```bash
./cookies-cli.sh status
# 输出: STATUS=expired
# 输出: SITE=知乎
```

### 同步 cookies
```bash
./cookies-cli.sh sync
# 输出: SYNC=success
# 输出: STATUS=ready
```

### 自动提醒
```bash
./auto-reminder.sh
# 输出: ⚠️  Cookies 过期提醒
# 输出: 请在主浏览器登录...
```

## 2. Agent 工具集成

### Python 集成
```python
from agent_integration import CookiesManager

manager = CookiesManager()

# 检查状态
status = manager.check_status()
if status["need_login"]:
    print(f"需要登录: {status['site']}")

# 同步
result = manager.sync_cookies()
if result["success"]:
    print("同步成功")
```

### Shell 脚本集成
```bash
#!/bin/bash
# 检查并同步
./cookies-cli.sh status
if [ $? -ne 0 ]; then
    echo "需要登录"
    exit 1
fi
./cookies-cli.sh sync
```

## 3. 工作流示例

### 自动化工作流
```python
import subprocess

def automation_workflow():
    # 1. 检查 cookies
    result = subprocess.run(["./cookies-cli.sh", "status"], 
                          capture_output=True, text=True)
    
    if "expired" in result.stdout:
        # 2. 提醒用户
        print("⚠️  Cookies 过期")
        print("请在主浏览器登录后告诉我")
        
        # 3. 等待用户确认
        user_input = input("已登录? (y/n): ")
        if user_input.lower() != 'y':
            return False
        
        # 4. 同步 cookies
        subprocess.run(["./cookies-cli.sh", "sync"])
    
    # 5. 执行自动化任务
    print("开始自动化任务...")
    return True
```

### 错误处理
```python
def safe_operation():
    try:
        # 尝试操作
        browser_operation()
    except Exception as e:
        if "login" in str(e).lower():
            # cookies 过期
            result = subprocess.run(["./cookies-cli.sh", "status"], 
                                  capture_output=True, text=True)
            if "expired" in result.stdout:
                print("需要重新登录")
                return False
        raise
```

## 4. 定时任务

### Cron 定时同步
```bash
# 每周日同步 cookies
0 0 * * 0 /path/to/cookies-cli.sh sync >> /tmp/cookies-sync.log 2>&1
```

### 监控脚本
```bash
#!/bin/bash
# 监控 cookies 状态

while true; do
    STATUS=$(/path/to/cookies-cli.sh status)
    
    if echo "$STATUS" | grep -q "expired"; then
        echo "⚠️  Cookies 过期，请登录"
        # 发送通知
        osascript -e 'display notification "Cookies 过期" with title "浏览器自动化"'
    fi
    
    sleep 3600  # 每小时检查一次
done
```

## 5. 集成到现有系统

### 作为 MCP 工具
```json
{
  "name": "cookies_manager",
  "description": "管理浏览器 cookies",
  "parameters": {
    "action": {
      "type": "string",
      "enum": ["check", "sync", "auto"]
    }
  }
}
```

### 作为 API 端点
```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/cookies/status')
def cookies_status():
    manager = CookiesManager()
    return jsonify(manager.check_status())

@app.route('/cookies/sync')
def cookies_sync():
    manager = CookiesManager()
    return jsonify(manager.sync_cookies())
```

## 6. 故障排除

### 问题：无法连接到浏览器
```bash
# 检查浏览器状态
browser-harness --doctor

# 重启 daemon
browser-harness --reload
```

### 问题：同步失败
```bash
# 检查 cookies 文件
ls -la /tmp/cookies.json

# 手动同步
./cookies-cli.sh sync
```

### 问题：权限错误
```bash
# 检查脚本权限
chmod +x cookies-cli.sh
chmod +x auto-reminder.sh
```