# 使用示例

## 1. Agent 学习

### 学习 SKILL.md
```
Agent 需要学习：
- /skills/browser-harness/SKILL.md（核心功能）
- /skills/browser-harness/cookies-manager.md（按需加载）
```

### 学习顺序
1. 先学习 SKILL.md - 了解基本操作
2. 遇到登录问题时 - 加载 cookies-manager.md

## 2. 基本操作

### 打开网站
```bash
browser-harness <<'PY'
new_tab("https://www.zhihu.com")
wait_for_load()
print(page_info())
PY
```

### 截图
```bash
browser-harness <<'PY'
capture_screenshot("/tmp/screenshot.png")
PY
```

### 点击元素
```bash
browser-harness <<'PY'
click_at_xy(350, 420)
PY
```

## 3. 登录状态管理

### 检查状态
```bash
./cookies-cli.sh status
```

### 同步 cookies
```bash
./cookies-cli.sh sync
```

### 完整工作流
```bash
./example.sh workflow https://www.zhihu.com
```

## 4. Agent 集成示例

### Python Agent
```python
import subprocess

def browser_operation(url):
    # 检查登录状态
    result = subprocess.run(["./cookies-cli.sh", "status"], 
                          capture_output=True, text=True)
    
    if "expired" in result.stdout:
        # 提醒用户
        print("请在主浏览器登录")
        return False
    
    # 访问网站
    subprocess.run(["browser-harness", f"""
new_tab("{url}")
wait_for_load()
print(page_info())
"""])
    return True
```

### Shell Agent
```bash
#!/bin/bash
# 检查登录状态
./cookies-cli.sh status
if [ $? -ne 0 ]; then
    echo "需要登录"
    exit 1
fi

# 访问网站
browser-harness <<'PY'
new_tab("https://www.zhihu.com")
wait_for_load()
print(page_info())
PY
```

## 5. 最佳实践

### 按需加载
- 只在需要时加载 cookies-manager.md
- 遇到登录页面时自动加载

### 错误处理
- 检测到登录页面时提醒用户
- 同步失败时提供解决方案

### 定期维护
- 每周同步一次 cookies
- 登录状态过期时及时同步

## 6. 常见问题

### Q: 如何检测登录状态？
```bash
browser-harness <<'PY'
new_tab("https://www.zhihu.com")
wait_for_load()
page = page_info()
if "signin" in page.get("url", ""):
    print("NEED_LOGIN")
else:
    print("LOGIN_OK")
PY
```

### Q: 如何自动同步 cookies？
```bash
./cookies-cli.sh sync
```

### Q: 如何在云端使用？
1. 部署 browser-harness 到云端
2. 同步本地 cookies 到云端
3. Agent 调用云端的 browser-harness

## 7. 工具路径

- **SKILL.md**: `/skills/browser-harness/SKILL.md`
- **cookies-manager.md**: `/skills/browser-harness/cookies-manager.md`
- **cookies-cli.sh**: `/cookies-cli.sh`
- **example.sh**: `/skills/browser-harness/example.sh`