# 自动化热榜评论爬取方案

## 🎉 新方案特点

**完全自动化**：从热榜话题页面自动提取视频 ID，无需手动复制 URL！

## 📋 工作流程

```
1. 获取抖音热榜数据（30 条）
   ↓
2. 访问每个热榜话题页面
   ↓
3. 从 HTML 中提取第一个视频 ID
   ↓
4. 调用评论爬取 API
   ↓
5. 保存评论数据到 CSV
```

## ✅ 测试结果

```
获取抖音热榜成功（缓存数据）
获取到 30 条热榜数据

测试 1: 我的春日粉彩妆容公式
  URL: https://www.douyin.com/hot/2444287
  [OK] 提取成功：7621407717302814634
```

## 🚀 使用方法

### 方法 1：完全自动化（推荐）

运行测试脚本：

```bash
python test_hot_topic.py
```

**特点：**
- 自动获取热榜数据
- 自动访问话题页面
- 自动提取视频 ID
- 可选择是否爬取评论

### 方法 2：通过 API

```bash
POST /api/hot-comment/crawl
{
  "video_count": 10,  // 爬取前 10 个热榜视频
  "comments_per_video": 100,
  "save_to_csv": true
}
```

**说明：**
- 当不提供 `video_urls` 和 `video_ids` 时，自动使用热榜话题页面提取方案
- 完全自动化，无需手动干预

### 方法 3：手动提供 URL（备选）

如果自动提取失败，可以手动提供视频 URL：

```bash
POST /api/hot-comment/crawl
{
  "video_urls": [
    "https://www.douyin.com/video/7123456789012345678"
  ],
  "comments_per_video": 100,
  "save_to_csv": true
}
```

## 🔍 技术实现

### 核心方法

```python
def get_video_from_hot_url(self, hot_url: str, hot_title: str) -> Optional[str]:
    """
    从热榜 URL 获取相关视频 ID
    
    方案：访问热榜话题页面，提取第一个视频的 URL
    """
    # 1. 访问热榜话题页面
    text = self.request.getHTML(hot_url)
    
    # 2. 使用正则表达式提取视频 ID
    video_url_pattern = r'/video/(\d{19})'
    matches = re.findall(video_url_pattern, text)
    
    # 3. 返回第一个视频 ID
    if matches:
        return matches[0]
    
    return None
```

### 正则表达式说明

- `/video/(\d{19})` - 匹配抖音视频 URL
- `\d{19}` - 匹配 19 位数字的视频 ID
- 同时支持 `/note/` 格式（笔记类型）

## 📊 方案对比

| 方案 | 自动化程度 | 可靠性 | 速度 | 推荐度 |
|------|-----------|--------|------|--------|
| **话题页面提取（新）** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **搜索 API（旧）** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| **手动 URL** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## 💡 优势

1. **完全自动化**：无需手动复制 URL
2. **可靠性高**：直接从 HTML 提取，不依赖搜索 API
3. **速度快**：访问话题页面即可获取
4. **灵活性好**：支持手动 URL 作为备选方案

## ⚠️ 注意事项

1. **访问延迟**：每个话题页面访问后延迟 1.5 秒
2. **Cookie 要求**：需要有效的抖音 Cookie
3. **网络要求**：需要能访问抖音网站

## 🎯 最佳实践

### 批量爬取热榜评论

```python
from backend.lib.douyin.hot_comment import DouyinHotCommentFetcher
from backend.settings import settings

cookie = settings.get("cookie")
fetcher = DouyinHotCommentFetcher(cookie=cookie)

# 爬取前 10 个热榜视频的评论
result = fetcher.crawl_hot_videos_comments(
    video_count=10,
    comments_per_video=100,
    save_to_csv=True,
)

print(f"爬取完成：{result['total_comments']} 条评论")
```

### 前端集成

在前端添加"热榜评论爬取"按钮，用户点击后：

1. 自动获取热榜数据
2. 自动访问话题页面提取视频 ID
3. 自动爬取评论并保存
4. 显示进度和结果

## 🔧 故障排除

### 问题 1：提取视频 ID 失败

**可能原因：**
- 话题页面结构变化
- 网络请求失败
- Cookie 无效

**解决方法：**
- 检查日志输出
- 更新 Cookie
- 使用手动 URL 方案

### 问题 2：评论爬取失败

**可能原因：**
- Cookie 权限不足
- 视频已删除
- 网络问题

**解决方法：**
- 更新 Cookie
- 跳过该视频
- 检查网络连接

## 📝 总结

新方案通过访问热榜话题页面自动提取视频 ID，实现了完全自动化的评论爬取，可靠性高，无需手动干预！
