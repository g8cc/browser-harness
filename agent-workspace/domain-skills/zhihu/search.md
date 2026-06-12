# Zhihu — Search Best Practices

Field-tested against zhihu.com on 2026-06-12.

---

## Search URL Patterns

### Basic Search

```
https://www.zhihu.com/search?type=content&q={QUERY}
```

### Search Types

| Type | URL Parameter |
|------|---------------|
| 综合 | `type=content` |
| 问题 | `type=question` |
| 文章 | `type=article` |
| 用户 | `type=people` |

---

## Search Results Extraction

### Problem

知乎搜索结果需要登录才能查看完整内容。

### Solution

使用通用选择器提取可见内容：

```javascript
Array.from(document.querySelectorAll('a[href*="/question/"], a[href*="/answer/"]'))
    .filter(a => a.innerText?.trim()?.length > 5)
    .slice(0, 10)
    .map(a => ({
        href: a.href,
        text: a.innerText.trim()
    }))
```

### Example

```python
import urllib.parse

keyword = "AI 创作"
encoded_keyword = urllib.parse.quote(keyword)
search_url = "https://www.zhihu.com/search?type=content&q=" + encoded_keyword

new_tab(search_url)
wait_for_load()
```

---

## Gotchas

- **需要登录**：知乎搜索结果需要登录才能查看完整内容
- **页面结构**：搜索结果使用 React 渲染，需要等待加载
- **选择器**：使用 `a[href*="/question/"]` 和 `a[href*="/answer/"]` 提取链接