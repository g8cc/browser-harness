# Bilibili — Search Best Practices

Field-tested against bilibili.com on 2026-06-12.

---

## Search URL Patterns

### Basic Search

```
https://search.bilibili.com/all?keyword={QUERY}
```

### Search with Sort

| Sort | URL Parameter |
|------|---------------|
| 综合排序 | `order=totalrank` |
| 最多播放 | `order=click` |
| 最新发布 | `order=pubdate` |
| 最多弹幕 | `order=dm` |
| 最多收藏 | `order=stow` |

### Search Tabs

| Tab | URL |
|-----|-----|
| 综合 | `/all?keyword={QUERY}` |
| 视频 | `/video?keyword={QUERY}` |
| 番剧 | `/bangumi?keyword={QUERY}` |
| 影视 | `/pgc?keyword={QUERY}` |
| 直播 | `/live?keyword={QUERY}` |
| 专栏 | `/article?keyword={QUERY}` |
| 用户 | `/bili_user?keyword={QUERY}` |

---

## Search Results Extraction

### Problem

B 站搜索结果中，每个视频卡片有两个 `<a>` 标签：
1. **播放量/时长**：包含换行符（如 "690\n2\n37:28"）
2. **视频标题**：不包含换行符

### Solution

使用 `innerText.includes('\n')` 过滤掉播放量/时长信息：

```javascript
Array.from(document.querySelectorAll('a[href*="/video/BV"]'))
    .filter(a => !a.innerText.includes('\n'))  // 过滤播放量/时长
    .filter(a => a.innerText.trim().length > 10)  // 过滤短文本
    .slice(0, 10)
    .map(a => ({
        href: a.href,
        text: a.innerText.trim()
    }))
```

### Example

```python
from agent_helpers import bilibili_extract_search_results

results = bilibili_extract_search_results(10)
for video in results[:5]:
    print(video.get("text"))
    print(video.get("href"))
```

---

## Open Latest Video

### Problem

需要打开搜索结果中的第一个视频（最新发布）

### Solution

```python
from agent_helpers import bilibili_open_latest_video

page = bilibili_open_latest_video("课代表立正")
if page:
    print("视频标题: " + page.get("title"))
```

### Steps

1. 构造搜索 URL（按最新发布排序）
2. 打开搜索页
3. 提取搜索结果
4. 打开第一个视频

---

## Video Playback Control

### Jump to Specific Time

```javascript
const video = document.querySelector('video');
video.currentTime = 720;  // 12分钟 = 720秒
video.play();
```

### Get Current Time

```javascript
const currentTime = document.querySelector('video')?.currentTime || 0;
const minutes = Math.floor(currentTime / 60);
const seconds = Math.floor(currentTime % 60);
```

### Get Video Duration

```javascript
const duration = document.querySelector('video')?.duration || 0;
```

---

## Gotchas

- **搜索结果加载延迟**：需要等待 3 秒让搜索结果加载
- **播放量/时长格式**：包含换行符，需要过滤
- **视频标题位置**：在 `a[href*="/video/BV"]` 的 `innerText` 中
- **排序参数**：使用 `order=pubdate` 按最新发布排序
- **视频跳转**：使用 `video.currentTime` 设置播放时间