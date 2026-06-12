# Baidu — Search Best Practices

Field-tested against baidu.com on 2026-06-12.

---

## Search URL Patterns

### Basic Search

```
https://www.baidu.com/s?wd={QUERY}
```

### Search Parameters

| Parameter | Description |
|-----------|-------------|
| `wd` | 搜索关键词 |
| `pn` | 页码（从 0 开始） |
| `rn` | 每页结果数（默认 10） |

---

## Search Results Extraction

### Problem

百度页面结构复杂，选择器需要适配。

### Solution

使用通用选择器提取链接：

```javascript
Array.from(document.querySelectorAll('a[href*="baidu.com"]'))
    .filter(a => a.href && !a.href.includes('baidu.com/s?'))
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
search_url = "https://www.baidu.com/s?wd=" + encoded_keyword

new_tab(search_url)
wait_for_load()
```

---

## Gotchas

- **页面结构复杂**：百度页面结构经常变化，需要适配选择器
- **广告结果**：需要过滤广告结果
- **登录状态**：部分功能需要登录