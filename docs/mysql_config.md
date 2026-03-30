# MySQL 数据库配置说明

## 📋 前提条件

1. **安装 MySQL 服务器**
   - Windows: 下载 MySQL Installer
   - macOS: 使用 Homebrew 或 DMG 安装包
   - Linux: 使用包管理器（apt/yum）

2. **安装 Python 依赖**
   ```bash
   pip install pymysql cryptography
   ```

## 🔧 配置步骤

### 步骤 1：创建 MySQL 用户和数据库

```sql
-- 登录 MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE douyin_hot_comments CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（可选，建议使用专门用户）
CREATE USER 'douyin'@'localhost' IDENTIFIED BY 'ROOT';

-- 授权
GRANT ALL PRIVILEGES ON douyin_hot_comments.* TO 'douyin'@'localhost';
FLUSH PRIVILEGES;

-- 退出
EXIT;
```

### 步骤 2：修改数据库配置

编辑 `backend/lib/database/config.py`：

```python
db_config = MySQLConfig(
    host="localhost",      # MySQL 主机地址
    port=3306,            # MySQL 端口
    user="root",          # 用户名
    password="your_password",  # 密码
    database="douyin_hot_comments",  # 数据库名
    charset="utf8mb4"     # 字符集
)
```

### 步骤 3：初始化数据库

```bash
cd d:\Project_graduation\douyin-main

# 测试连接
python -m backend.lib.database.init test

# 初始化数据库和表
python -m backend.lib.database.init
```

### 步骤 4：验证初始化

```bash
# 登录 MySQL 查看
mysql -u root -p

USE douyin_hot_comments;
SHOW TABLES;
```

应该看到以下表：
- `hot_search` - 热榜数据
- `videos` - 视频数据
- `comments` - 评论数据
- `scheduler_history` - 定时任务历史

## 📊 数据库表结构

### hot_search（热榜数据表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| rank | INT | 排名 |
| title | VARCHAR(500) | 标题 |
| hot_value | BIGINT | 热度值 |
| video_id | VARCHAR(50) | 视频 ID |
| crawl_time | DATETIME | 爬取时间 |

### videos（视频数据表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| aweme_id | VARCHAR(50) | 视频 ID（唯一） |
| title | VARCHAR(500) | 视频标题 |
| author | VARCHAR(200) | 作者 |
| duration | INT | 视频时长 |
| cover_url | VARCHAR(500) | 封面 URL |
| play_count | BIGINT | 播放量 |
| digg_count | BIGINT | 点赞数 |
| comment_count | BIGINT | 评论数 |
| share_count | BIGINT | 分享数 |
| crawl_time | DATETIME | 爬取时间 |

### comments（评论数据表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| comment_id | VARCHAR(50) | 评论 ID（唯一） |
| aweme_id | VARCHAR(50) | 视频 ID |
| nickname | VARCHAR(200) | 用户昵称 |
| text | TEXT | 评论内容 |
| create_time | DATETIME | 评论时间 |
| digg_count | INT | 点赞数 |
| reply_count | INT | 回复数 |
| ip_label | VARCHAR(100) | IP 属地 |
| is_top | BOOLEAN | 是否置顶 |
| is_hot | BOOLEAN | 是否热门 |
| crawl_time | DATETIME | 爬取时间 |

### scheduler_history（定时任务历史表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| run_time | DATETIME | 运行时间 |
| video_count | INT | 爬取视频数 |
| comment_count | INT | 爬取评论数 |
| status | VARCHAR(20) | 状态（success/failed） |
| error_message | TEXT | 错误信息 |
| duration | INT | 执行时长（秒） |

## 🔍 常用 SQL 查询

### 查看热榜数据

```sql
-- 查看最新一次爬取的热榜
SELECT * FROM hot_search 
WHERE crawl_time = (SELECT MAX(crawl_time) FROM hot_search)
ORDER BY rank;

-- 查看热榜历史趋势
SELECT title, crawl_time, hot_value 
FROM hot_search 
WHERE title LIKE '%关键词%'
ORDER BY crawl_time DESC;
```

### 查看视频数据

```sql
-- 查看播放量最高的视频
SELECT aweme_id, title, author, play_count, digg_count
FROM videos
ORDER BY play_count DESC
LIMIT 10;

-- 查看某个视频的所有信息
SELECT * FROM videos WHERE aweme_id = '视频 ID';
```

### 查看评论数据

```sql
-- 查看某个视频的所有评论
SELECT nickname, text, digg_count, create_time
FROM comments
WHERE aweme_id = '视频 ID'
ORDER BY digg_count DESC;

-- 查看点赞最多的评论
SELECT nickname, text, digg_count
FROM comments
ORDER BY digg_count DESC
LIMIT 10;

-- 查看某地区的评论
SELECT nickname, text, ip_label
FROM comments
WHERE ip_label LIKE '%广东%'
ORDER BY create_time DESC;

-- 查看评论数统计
SELECT aweme_id, COUNT(*) as comment_count
FROM comments
GROUP BY aweme_id
ORDER BY comment_count DESC;
```

### 查看定时任务历史

```sql
-- 查看所有定时任务执行记录
SELECT run_time, video_count, comment_count, status, duration
FROM scheduler_history
ORDER BY run_time DESC;

-- 查看成功的任务
SELECT * FROM scheduler_history
WHERE status = 'success'
ORDER BY run_time DESC;

-- 查看失败的任务
SELECT * FROM scheduler_history
WHERE status = 'failed'
ORDER BY run_time DESC;
```

## 🛠️ 数据库管理

### 备份数据库

```bash
# 备份整个数据库
mysqldump -u root -p douyin_hot_comments > backup_$(date +%Y%m%d_%H%M%S).sql

# 备份单个表
mysqldump -u root -p douyin_hot_comments comments > comments_backup.sql
```

### 恢复数据库

```bash
# 从备份文件恢复
mysql -u root -p douyin_hot_comments < backup_20260327_000000.sql
```

### 清空数据

```sql
-- 清空所有数据（保留表结构）
TRUNCATE TABLE comments;
TRUNCATE TABLE videos;
TRUNCATE TABLE hot_search;
TRUNCATE TABLE scheduler_history;
```

## ⚠️ 注意事项

1. **字符集**：必须使用 `utf8mb4`，支持 emoji 等特殊字符
2. **密码安全**：不要使用空密码，生产环境使用强密码
3. **定期备份**：建议每天备份数据库
4. **索引优化**：表已创建常用字段的索引，无需额外优化
5. **连接池**：高并发场景建议使用连接池（如 DBUtils）

## 🐛 常见问题

### 问题 1：无法连接数据库

**错误信息**：`Can't connect to MySQL server`

**解决方法**：
1. 检查 MySQL 服务是否运行
2. 检查端口是否正确（默认 3306）
3. 检查防火墙设置

### 问题 2：字符集错误

**错误信息**：`Incorrect string value`

**解决方法**：
1. 确保数据库字符集为 `utf8mb4`
2. 检查表字符集是否为 `utf8mb4`
3. 修改连接配置中的 `charset` 参数

### 问题 3：权限不足

**错误信息**：`Access denied for user`

**解决方法**：
1. 检查用户名和密码是否正确
2. 检查用户是否有数据库权限
3. 重新授权：`GRANT ALL PRIVILEGES ON database.* TO 'user'@'host';`

## 📝 下一步

数据库配置完成后，需要：

1. ✅ 修改爬取模块，支持写入 MySQL
2. ✅ 修改分析模块，支持从 MySQL 读取
3. ✅ 更新前端 UI，增加数据库管理功能

请继续查看相关文档完成后续配置。
