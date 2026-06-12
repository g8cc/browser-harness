# 图片识别大模型集成指南

## 概述

browser-harness 支持集成多个图片识别大模型，用于分析截图、识别页面元素、处理验证码等场景。

## 支持的模型

| 模型 | 名称 | 环境变量 | 状态 |
|------|------|----------|------|
| OpenAI | GPT-4V | `OPENAI_API_KEY` | ✅ |
| Claude | Claude 3.5 Sonnet | `ANTHROPIC_API_KEY` | ✅ |
| Gemini | Google Gemini Pro Vision | `GOOGLE_API_KEY` | ✅ |
| 通义千问 | 通义千问 VL | `DASHSCOPE_API_KEY` | ✅ |

## 配置方法

### 1. 设置环境变量

```bash
# OpenAI
export OPENAI_API_KEY="your-api-key"

# Claude
export ANTHROPIC_API_KEY="your-api-key"

# Gemini
export GOOGLE_API_KEY="your-api-key"

# 通义千问
export DASHSCOPE_API_KEY="your-api-key"
```

### 2. 检查配置

```python
from agent_helpers import list_vision_models

list_vision_models()
```

## 使用方法

### 1. 截图并分析

```python
from agent_helpers import screenshot_and_analyze

# 使用默认模型（OpenAI）
result = screenshot_and_analyze("描述这个页面的内容")
print(result)

# 指定模型
result = screenshot_and_analyze("这个页面有哪些按钮？", "claude")
print(result)
```

### 2. 分析已有截图

```python
from agent_helpers import analyze_screenshot

# 分析截图文件
result = analyze_screenshot("/tmp/screenshot.png", "描述这个页面的内容")
print(result)
```

### 3. 查看可用模型

```python
from agent_helpers import list_vision_models

list_vision_models()
```

## 使用场景

### 1. 页面分析

```python
from agent_helpers import screenshot_and_analyze

# 分析页面内容
result = screenshot_and_analyze("这个页面的主要内容是什么？")
print(result)
```

### 2. 元素识别

```python
from agent_helpers import screenshot_and_analyze

# 识别可点击的元素
result = screenshot_and_analyze("这个页面有哪些可以点击的按钮？")
print(result)
```

### 3. 验证码识别

```python
from agent_helpers import screenshot_and_analyze

# 识别验证码
result = screenshot_and_analyze("这个验证码是什么？")
print(result)
```

### 4. 数据提取

```python
from agent_helpers import screenshot_and_analyze

# 提取表格数据
result = screenshot_and_analyze("这个表格里有哪些数据？")
print(result)
```

## 示例代码

### 完整示例

```python
import sys
sys.path.insert(0, 'agent-workspace')
from agent_helpers import screenshot_and_analyze, list_vision_models

# 1. 查看可用模型
print("=== 可用模型 ===")
list_vision_models()

# 2. 截图并分析
print("\n=== 截图分析 ===")
result = screenshot_and_analyze("描述这个页面的内容")
print(result)

# 3. 使用不同模型
print("\n=== 使用 Claude 分析 ===")
result = screenshot_and_analyze("这个页面有哪些按钮？", "claude")
print(result)
```

## 注意事项

1. **API 费用**：图片识别 API 会产生费用，请注意使用量
2. **响应时间**：图片识别需要一定时间，请耐心等待
3. **图片大小**：建议截图尺寸不超过 2000x2000 像素
4. **网络环境**：需要能够访问对应的 API 服务

## 故障排除

### 问题：未设置环境变量

```
❌ 未设置环境变量: OPENAI_API_KEY
```

**解决方法**：设置对应的环境变量

### 问题：API 调用失败

```
❌ API 调用失败: 401
```

**解决方法**：检查 API Key 是否正确

### 问题：图片太大

```
❌ 图片太大
```

**解决方法**：使用 `max_dim` 参数限制截图尺寸

```python
from browser_harness.helpers import capture_screenshot

# 限制截图尺寸
capture_screenshot(max_dim=1800)
```