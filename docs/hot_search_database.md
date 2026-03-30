# 抖音热榜数据库刷新功能

## 功能概述

现在抖音热榜功能支持数据库持久化存储，可以实现：

1. **定时自动刷新**：每 2 小时自动刷新热榜数据到数据库
2. **手动刷新**：点击"刷新到数据库"按钮主动更新
3. **从数据库读取**：优先从数据库加载热榜数据，避免每次都重新爬取

## 新增功能

### 1. 后端 API

#### 刷新热榜到数据库
```
POST /api/hot/douyin/refresh-db
```
获取最新热榜数据并保存到数据库，同时提取前 10 个热榜话题对应的视频 ID。

**响应示例**：
```json
{
  "success": true,
  "count": 30,
  "videos_count": 10,
  "message": "已刷新 30 条热榜数据，10 个视频信息"
}
```

#### 从数据库读取热榜
```
GET /api/hot/douyin/from-db?limit=30
```
从数据库读取最新一次爬取的热榜数据。

**响应示例**：
```json
{
  "success": true,
  "from_db": true,
  "is_stale": false,
  "latest_time": "2026-03-27T03:30:00",
  "time_ago": "30 分钟前",
  "data": [
    {
      "id": 1,
      "rank": 1,
      "title": "热搜标题",
      "hot_value": "1234567",
      "video_id": "7621459127471377317",
      "crawl_time": "2026-03-27T03:30:00"
    }
  ]
}
```

### 2. 前端界面

#### 热榜大屏新增按钮

- **刷新到数据库**（紫色按钮）：获取最新热榜并保存到数据库
- **刷新**（蓝色按钮）：重新加载当前数据（从数据库或 API）
- **自动刷新开关**：开启后每分钟自动刷新一次

#### 状态提示

- 显示数据更新时间
- 显示"X 分钟前"的相对时间
- 数据超过 2 小时会提示"数据可能已过期"

### 3. 定时任务增强

定时爬取任务现在会**自动刷新热榜数据**到数据库：

```python
def _crawl_task(video_count, comments_per_video, save_to_db):
    # 1. 先刷新热榜数据到数据库
    hot_videos = fetcher.get_hot_videos(count=30)
    fetcher.save_hot_search_to_db(hot_videos)
    
    # 2. 爬取评论
    result = fetcher.crawl_hot_comments(...)
    return result
```

## 使用流程

### 方式一：使用定时任务（推荐）

1. 进入"热榜评论"页面
2. 配置定时任务参数：
   - 爬取间隔：2 小时
   - 爬取视频数量：10
   - 每个视频评论数：100
   - ✅ 勾选"保存到 MySQL 数据库"
3. 点击"启动定时任务"

**效果**：
- 每 2 小时自动刷新热榜数据
- 自动爬取热榜视频评论
- 所有数据保存到数据库

### 方式二：手动刷新

1. 进入"抖音热榜"页面（左侧边栏）
2. 点击"刷新到数据库"按钮
3. 等待刷新完成

**效果**：
- 立即获取最新热榜
- 保存到数据库
- 自动从数据库加载显示

### 方式三：热榜评论爬取时自动刷新

在"热榜评论"页面爬取评论时，定时任务会自动先刷新热榜数据。

## 数据库表结构

### hot_search（热榜表）
```sql
CREATE TABLE hot_search (
    id INT PRIMARY KEY AUTO_INCREMENT,
    rank INT NOT NULL,              -- 排名
    title VARCHAR(500) NOT NULL,    -- 标题
    hot_value VARCHAR(50),          -- 热度值
    video_id VARCHAR(50),           -- 视频 ID
    crawl_time DATETIME NOT NULL    -- 爬取时间
);
```

### videos（视频表）
```sql
CREATE TABLE videos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    aweme_id VARCHAR(50) UNIQUE NOT NULL,  -- 视频 ID
    title VARCHAR(500),                     -- 标题
    author VARCHAR(200),                    -- 作者
    hot_rank INT,                           -- 热榜排名（如果是热榜视频）
    hot_value VARCHAR(50),                  -- 热度值
    source VARCHAR(50),                     -- 来源：hot_search
    crawl_time DATETIME                     -- 爬取时间
);
```

## 优势

1. **减少重复爬取**：从数据库读取，不需要每次都调用抖音 API
2. **数据持久化**：历史热榜数据可追溯
3. **自动化**：定时任务自动更新，无需手动操作
4. **性能提升**：页面加载更快，用户体验更好

## 注意事项

1. **Cookie 配置**：刷新热榜需要有效的抖音 Cookie
2. **数据时效性**：建议至少每 2 小时刷新一次
3. **数据库清理**：定期清理过期的热榜数据（可选）

## 未来扩展

- [ ] 添加热榜历史趋势分析
- [ ] 支持查看历史热榜数据
- [ ] 热榜数据可视化大屏
- [ ] 热榜话题关联视频自动追踪
