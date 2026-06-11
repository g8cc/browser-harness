# Browser Harness Skill

browser-harness 的完整 skill，支持浏览器操作和登录状态管理。

## 目录结构

```
skills/browser-harness/
├── SKILL.md              # 主文档（核心功能）
├── cookies-manager.md    # Cookies 管理（按需加载）
└── README.md             # 本文件
```

## 使用方式

### 1. Agent 学习

Agent 需要学习：
- **SKILL.md** - 核心浏览器操作
- **cookies-manager.md** - 按需加载，处理登录状态

### 2. 调用方式

```bash
# 核心操作
browser-harness <<'PY'
new_tab("https://www.zhihu.com")
wait_for_load()
print(page_info())
PY

# Cookies 管理
./cookies-cli.sh status
./cookies-cli.sh sync
```

### 3. 按需加载

当检测到登录页面时，加载 cookies-manager.md：
- 访问网站后自动检查
- 发现登录页面时提醒用户
- 用户登录后同步 cookies

## 工作流程

```
1. Agent 访问网站
   ↓
2. 检测是否需要登录
   ↓
3. 如果需要登录
   - 提醒用户
   - 等待用户登录
   - 同步 cookies
   ↓
4. 继续操作
```

## 文件说明

### SKILL.md
- 核心浏览器操作
- 常用函数和命令
- 最佳实践和注意事项

### cookies-manager.md
- 登录状态检测
- Cookies 同步流程
- CLI 工具使用
- 错误处理

## 集成示例

### Python Agent

```python
import subprocess

def browser_operation(url):
    # 访问网站
    subprocess.run(["browser-harness", f"""
new_tab("{url}")
wait_for_load()
page = page_info()
if "signin" in page.get("url", ""):
    print("NEED_LOGIN")
else:
    print("LOGIN_OK")
"""])
    
    # 检查登录状态
    result = subprocess.run(["./cookies-cli.sh", "status"], 
                          capture_output=True, text=True)
    
    if "expired" in result.stdout:
        # 提醒用户
        print("请在主浏览器登录")
        # 等待用户确认后同步
        subprocess.run(["./cookies-cli.sh", "sync"])
```

### Shell Agent

```bash
#!/bin/bash
# 访问网站
browser-harness <<'PY'
new_tab("https://www.zhihu.com")
wait_for_load()
page = page_info()
if "signin" in page.get("url", ""):
    print("NEED_LOGIN")
else:
    print("LOGIN_OK")
PY

# 检查登录状态
./cookies-cli.sh status
if [ $? -ne 0 ]; then
    echo "需要登录"
    # 等待用户操作
    ./cookies-cli.sh sync
fi
```

## 注意事项

1. **按需加载** - cookies-manager.md 只在需要时加载
2. **用户提醒** - 过期时清晰提醒用户
3. **定期同步** - 建议每周同步一次
4. **错误处理** - 同步失败时提供解决方案