# GitHub — Search Best Practices

Field-tested against github.com on 2026-06-12.

---

## Search URL Patterns

### Repository Search

```
https://github.com/search?q={QUERY}&type=repositories
```

### Search Types

| Type | URL Parameter |
|------|---------------|
| 仓库 | `type=repositories` |
| 代码 | `type=code` |
| Issues | `type=issues` |
| Pull Requests | `type=pullrequests` |
| 用户 | `type=users` |

### Search Filters

| Filter | Example |
|--------|---------|
| 语言 | `language:python` |
| 星标 | `stars:>1000` |
| 更新时间 | `pushed:>2024-01-01` |

---

## Search Results Extraction

### Problem

GitHub 搜索结果使用动态类名，选择器需要适配。

### Solution

使用通用选择器提取链接：

```javascript
Array.from(document.querySelectorAll('a[href*="/"]'))
    .filter(a => a.href && a.href.includes('github.com') && !a.href.includes('/search'))
    .filter(a => a.innerText?.trim()?.length > 3)
    .slice(0, 10)
    .map(a => ({
        href: a.href,
        text: a.innerText.trim()
    }))
```

### Example

```python
import urllib.parse

keyword = "browser-harness"
encoded_keyword = urllib.parse.quote(keyword)
search_url = "https://github.com/search?q=" + encoded_keyword + "&type=repositories"

new_tab(search_url)
wait_for_load()
```

---

## Navigation

### Repository Structure

| Page | URL |
|------|-----|
| 仓库首页 | `https://github.com/{owner}/{repo}` |
| Issues | `https://github.com/{owner}/{repo}/issues` |
| Pull Requests | `https://github.com/{owner}/{repo}/pulls` |
| 代码 | `https://github.com/{owner}/{repo}/tree/{branch}` |

---

## Gotchas

- **动态类名**：GitHub 使用动态类名，选择器需要适配
- **登录状态**：部分功能需要登录
- **API 优先**：GitHub 提供 API，优先使用 API