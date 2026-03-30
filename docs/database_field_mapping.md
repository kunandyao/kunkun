# 数据库字段映射文档

本文档详细说明数据库表字段与实际爬取数据（CSV/JSON）之间的映射关系。

---

## 📊 数据库表概览

| 表名 | 中文名 | 数据来源 | 记录数 |
|------|--------|---------|--------|
| `hot_search` | 热榜数据表 | 热榜 API | 30 条/次 |
| `videos` | 视频数据表 | 视频详情 API | 按爬取数量 |
| `comments` | 评论数据表 | 评论 API | 按视频评论数 |
| `scheduler_history` | 定时任务历史表 | 系统生成 | 按执行次数 |

---

## 1️⃣ hot_search (热榜数据表)

### 数据来源
- **API**: `https://newsnow.busiyi.world/api/s?id=douyin&latest`
- **格式**: JSON

### 字段映射

| 数据库字段 | 类型 | 源字段 | 映射说明 |
|-----------|------|--------|---------|
| `id` | INT | - | 自增主键 |
| `rank` | INT | `ranks[0]` | 热榜排名 (1-30) |
| `title` | VARCHAR(500) | 字典的 key | 热榜标题 |
| `hot_value` | BIGINT | `hotValue` | 热度值 |
| `video_id` | VARCHAR(50) | 从 URL 提取 | 关联的视频 ID |
| `crawl_time` | DATETIME | - | 爬取时间 (系统生成) |

### 示例数据

**原始 API 响应**:
```json
{
  "items": [
    {
      "title": "某热门话题",
      "url": "https://www.douyin.com/...",
      "mobileUrl": "https://m.douyin.com/...",
      "hotValue": "1234567"
    }
  ]
}
```

**解析后存储**:
```python
{
    'rank': 1,
    'title': '某热门话题',
    'hot_value': 1234567,
    'video_id': '7620662801643703592',  # 从 URL 提取
    'crawl_time': datetime.now()
}
```

---

## 2️⃣ videos (视频数据表)

### 数据来源
- **文件**: `download/aweme_*.json`
- **格式**: JSON 数组

### 字段映射

| 数据库字段 | 类型 | 源字段 | 映射说明 |
|-----------|------|--------|---------|
| `id` | INT | - | 自增主键 |
| `aweme_id` | VARCHAR(50) | `id` | 视频唯一标识 |
| `title` | VARCHAR(500) | `desc` | 视频描述/标题 |
| `author` | VARCHAR(200) | `author_nickname` | 作者昵称 |
| `duration` | INT | `duration` | 视频时长 (毫秒) |
| `cover_url` | VARCHAR(500) | `cover` | 封面图片 URL |
| `play_count` | BIGINT | `liveWatchCount` | 播放量 (使用 liveWatchCount) |
| `digg_count` | BIGINT | `digg_count` | 点赞数 |
| `comment_count` | BIGINT | `comment_count` | 评论数 |
| `share_count` | BIGINT | `share_count` | 分享数 |
| `crawl_time` | DATETIME | - | 爬取时间 (系统生成) |

### 示例数据

**原始 JSON**:
```json
[{
  "id": "7620662801643703592",
  "desc": "在造出船之前，野兽先生被困在这座岛 #野兽先生",
  "author_nickname": "野兽中文配音版",
  "duration": 1765254,
  "cover": "https://...",
  "digg_count": 4348,
  "comment_count": 178,
  "share_count": 293,
  "liveWatchCount": 0
}]
```

**解析后存储**:
```python
{
    'aweme_id': '7620662801643703592',
    'title': '在造出船之前，野兽先生被困在这座岛 #野兽先生',
    'author': '野兽中文配音版',
    'duration': 1765254,
    'cover_url': 'https://...',
    'play_count': 0,  # 使用 liveWatchCount
    'digg_count': 4348,
    'comment_count': 178,
    'share_count': 293,
    'crawl_time': datetime.now()
}
```

---

## 3️⃣ comments (评论数据表)

### 数据来源
- **文件**: `download/comments_*.csv`
- **格式**: CSV

### 字段映射

| 数据库字段 | 类型 | 源字段 | 映射说明 |
|-----------|------|--------|---------|
| `id` | BIGINT | - | 自增主键 |
| `comment_id` | VARCHAR(50) | `id` | 评论唯一标识 ⚠️ |
| `aweme_id` | VARCHAR(50) | `aweme_id` | 所属视频 ID |
| `nickname` | VARCHAR(200) | `nickname` | 用户昵称 |
| `text` | TEXT | `text` | 评论内容 |
| `create_time` | DATETIME | `create_time` | 评论发布时间 |
| `digg_count` | INT | `digg_count` | 评论点赞数 |
| `reply_count` | INT | `reply_count` | 回复数 |
| `ip_label` | VARCHAR(100) | `ip_label` | IP 属地 |
| `is_top` | BOOLEAN | `is_top` | 是否置顶 |
| `is_hot` | BOOLEAN | `is_hot` | 是否热门 |
| `crawl_time` | DATETIME | - | 爬取时间 (系统生成) |

⚠️ **重要**: CSV 文件的 `id` 字段映射到数据库的 `comment_id`

### 示例数据

**原始 CSV**:
```csv
id,aweme_id,nickname,text,create_time,digg_count,reply_count,ip_label,is_top,is_hot
7619756454375998267,7619487934873423113，只野，"我已经想好了...",2026-03-22 01:06:45,91,8，江苏，False,False
```

**解析后存储**:
```python
{
    'comment_id': '7619756454375998267',  # 从 CSV 的 id 映射
    'aweme_id': '7619487934873423113',
    'nickname': '只野',
    'text': '我已经想好了...',
    'create_time': '2026-03-22 01:06:45',
    'digg_count': 91,
    'reply_count': 8,
    'ip_label': '江苏',
    'is_top': False,
    'is_hot': False,
    'crawl_time': datetime.now()
}
```

---

## 4️⃣ scheduler_history (定时任务历史表)

### 数据来源
- **来源**: 系统自动生成
- **触发**: 定时任务执行

### 字段映射

| 数据库字段 | 类型 | 说明 |
|-----------|------|------|
| `id` | INT | 自增主键 |
| `run_time` | DATETIME | 任务执行时间 |
| `video_count` | INT | 爬取的视频数量 |
| `comment_count` | INT | 爬取的评论数量 |
| `status` | VARCHAR(20) | 状态：success/failed |
| `error_message` | TEXT | 错误信息 (可选) |
| `duration` | INT | 执行时长 (秒) |

---

## 🔧 代码中的映射实现

### CommentModel 映射

文件：[`backend/lib/database/models.py`](d:\Project_graduation\douyin-main\backend\lib\database\models.py#L157-L160)

```python
params = (
    data.get('id'),  # CSV 的 id 字段映射到 comment_id
    data.get('aweme_id'),
    data.get('nickname'),
    # ...
)
```

### VideoModel 映射

文件：[`backend/lib/database/models.py`](d:\Project_graduation\douyin-main\backend\lib\database\models.py#L97-L107)

```python
params = (
    data.get('id'),  # JSON 的 id 字段映射到 aweme_id
    data.get('desc'),  # JSON 的 desc 字段映射到 title
    data.get('author_nickname'),  # JSON 的 author_nickname 映射到 author
    data.get('duration'),
    data.get('cover'),  # JSON 的 cover 映射到 cover_url
    data.get('liveWatchCount') or data.get('play_count'),
    # ...
)
```

### HotSearchModel 映射

文件：[`backend/lib/database/models.py`](d:\Project_graduation\douyin-main\backend\lib\database\models.py#L41-L48)

```python
params = (
    data.get('rank'),
    data.get('title'),
    data.get('hot_value'),
    data.get('video_id'),
    data.get('crawl_time', datetime.now())
)
```

---

## ✅ 验证测试

运行测试脚本验证字段映射：

```bash
python test_mapping.py
```

测试结果示例：
```
============================================================
测试数据库模型字段映射
============================================================

1. 测试评论数据映射
✓ 评论数据映射成功

2. 测试视频数据映射
✓ 视频数据映射成功

3. 测试热榜数据映射
✓ 热榜数据映射成功
```

---

## 📝 注意事项

1. **评论 ID 映射**: CSV 的 `id` 字段必须映射到数据库的 `comment_id`，不要混淆
2. **视频 ID 映射**: JSON 的 `id` 字段映射到数据库的 `aweme_id`
3. **字段命名**: 数据库使用下划线命名 (snake_case)，JSON 使用驼峰命名 (camelCase)
4. **时间字段**: `crawl_time` 由系统自动生成，不需要从源数据映射
5. **空值处理**: 使用 `data.get('field', default)` 处理可能的空值

---

## 🔄 数据流转

```
爬取数据 (CSV/JSON)
    ↓
字段映射 (models.py)
    ↓
SQL 生成 (insert_sql)
    ↓
MySQL 数据库
    ↓
前端展示 (React)
```

---

**文档更新时间**: 2026-03-27  
**数据库版本**: MySQL 8.0+  
**字符集**: utf8mb4
