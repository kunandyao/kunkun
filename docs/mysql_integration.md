# MySQL 数据库集成指南

## 📋 概述

本项目已集成 MySQL 数据库支持，用于存储热榜数据、视频信息、评论数据和定时任务历史记录。相比 CSV 文件，数据库方案提供了：

- ✅ 高效查询和检索
- ✅ 数据去重和增量更新
- ✅ 复杂查询和统计分析
- ✅ 更好的数据管理和维护

## 🚀 快速开始

### 步骤 1：安装 MySQL

**Windows 用户：**
1. 下载 [MySQL Installer](https://dev.mysql.com/downloads/installer/)
2. 运行安装程序，选择"Developer Default"或"Server only"
3. 设置 root 密码（请记住这个密码）
4. 完成安装

**macOS 用户：**
```bash
# 使用 Homebrew
brew install mysql
brew services start mysql
```

**Linux 用户：**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server

# CentOS/RHEL
sudo yum install mysql-server
sudo systemctl start mysqld
```

### 步骤 2：安装 Python 依赖

```bash
cd d:\Project_graduation\douyin-main
pip install pymysql cryptography
```

### 步骤 3：创建数据库

登录 MySQL：
```bash
mysql -u root -p
```

执行 SQL 命令：
```sql
-- 创建数据库
CREATE DATABASE douyin_hot_comments CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 查看数据库
SHOW DATABASES;

-- 退出
EXIT;
```

### 步骤 4：配置数据库连接

编辑文件 `backend/lib/database/config.py`：

```python
db_config = MySQLConfig(
    host="localhost",           # MySQL 主机地址
    port=3306,                 # MySQL 端口
    user="root",               # 用户名
    password="your_password",  # 密码（修改为你的密码）
    database="douyin_hot_comments",
    charset="utf8mb4"
)
```

### 步骤 5：初始化数据库

**方法 1：使用命令行工具**
```bash
cd d:\Project_graduation\douyin-main
python -m backend.lib.database.init
```

**方法 2：通过前端界面**
1. 启动后端和前端服务
2. 访问 http://localhost:8000
3. 在左侧菜单选择"数据库管理"
4. 点击"初始化数据库"按钮

### 步骤 6：验证安装

**命令行验证：**
```bash
python -m backend.lib.database.init test
```

**前端验证：**
访问"数据库管理"页面，查看连接状态和统计数据。

## 📊 数据库表结构

### hot_search（热榜数据表）

存储热榜信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| rank | INT | 排名（1-30） |
| title | VARCHAR(500) | 热榜标题 |
| hot_value | BIGINT | 热度值 |
| video_id | VARCHAR(50) | 关联视频 ID |
| crawl_time | DATETIME | 爬取时间 |

### videos（视频数据表）

存储视频信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| aweme_id | VARCHAR(50) | 视频 ID（唯一） |
| title | VARCHAR(500) | 视频标题 |
| author | VARCHAR(200) | 作者 |
| duration | INT | 视频时长（秒） |
| cover_url | VARCHAR(500) | 封面 URL |
| play_count | BIGINT | 播放量 |
| digg_count | BIGINT | 点赞数 |
| comment_count | BIGINT | 评论数 |
| share_count | BIGINT | 分享数 |
| crawl_time | DATETIME | 爬取时间 |

### comments（评论数据表）

存储评论数据：

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

存储定时任务执行记录：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| run_time | DATETIME | 运行时间 |
| video_count | INT | 爬取视频数 |
| comment_count | INT | 爬取评论数 |
| status | VARCHAR(20) | 状态（success/failed） |
| error_message | TEXT | 错误信息 |
| duration | INT | 执行时长（秒） |

## 🎯 使用方式

### 1. 通过前端 UI 使用

**爬取热榜评论并保存到数据库：**

1. 访问"热榜评论"页面
2. 配置爬取参数：
   - 视频数量（默认 10）
   - 每视频评论数（默认 100）
   - ✅ 勾选"保存到数据库"
3. 点击"开始爬取"

**定时任务自动保存到数据库：**

1. 在"热榜评论"页面底部找到"定时自动爬取"
2. 配置参数：
   - 间隔时间（如 2 小时）
   - ✅ 勾选"保存到数据库"
3. 点击"启动定时任务"

**查看数据库统计：**

1. 访问"数据库管理"页面
2. 查看实时统计数据：
   - 热榜数据总数
   - 视频总数
   - 评论总数
   - 任务执行次数

### 2. 通过 API 使用

**爬取并保存：**
```bash
curl -X POST http://localhost:8000/api/hot-comment/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "video_count": 10,
    "comments_per_video": 100,
    "save_to_csv": true,
    "save_to_db": true
  }'
```

**查询评论：**
```bash
# 获取所有评论（分页）
curl "http://localhost:8000/api/hot-comment/database/comments?limit=100&offset=0&order_by=digg_count"

# 获取指定视频的评论
curl "http://localhost:8000/api/hot-comment/database/comments?aweme_id=7619487934873423113&limit=50"
```

**获取统计信息：**
```bash
curl http://localhost:8000/api/hot-comment/database/statistics
```

### 3. 直接 SQL 查询

登录 MySQL：
```bash
mysql -u root -p douyin_hot_comments
```

**常用查询示例：**

```sql
-- 查看最新的评论
SELECT nickname, text, digg_count, create_time
FROM comments
ORDER BY crawl_time DESC
LIMIT 20;

-- 查看点赞最多的评论
SELECT nickname, text, digg_count, ip_label
FROM comments
ORDER BY digg_count DESC
LIMIT 10;

-- 查看某视频的评论统计
SELECT aweme_id, COUNT(*) as total, AVG(digg_count) as avg_digg
FROM comments
WHERE aweme_id = '7619487934873423113'
GROUP BY aweme_id;

-- 查看各地区评论分布
SELECT ip_label, COUNT(*) as count
FROM comments
WHERE ip_label != ''
GROUP BY ip_label
ORDER BY count DESC
LIMIT 10;

-- 查看热榜趋势
SELECT title, crawl_time, hot_value
FROM hot_search
WHERE title LIKE '%关键词%'
ORDER BY crawl_time DESC;

-- 查看定时任务执行情况
SELECT run_time, video_count, comment_count, status, duration
FROM scheduler_history
ORDER BY run_time DESC
LIMIT 10;
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
mysql -u root -p douyin_hot_comments < backup_20260327_000000.sql
```

### 清空数据

**通过前端：**
- 访问"数据库管理"页面
- 点击相应的"清空"按钮

**通过 SQL：**
```sql
-- 清空单个表
TRUNCATE TABLE comments;
TRUNCATE TABLE videos;
TRUNCATE TABLE hot_search;
TRUNCATE TABLE scheduler_history;

-- 清空所有表（慎用！）
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE comments;
TRUNCATE TABLE videos;
TRUNCATE TABLE hot_search;
TRUNCATE TABLE scheduler_history;
SET FOREIGN_KEY_CHECKS = 1;
```

### 删除数据库

```sql
DROP DATABASE douyin_hot_comments;
```

## ⚙️ 高级配置

### 修改数据库配置

编辑 `backend/lib/database/config.py`：

```python
db_config = MySQLConfig(
    host="192.168.1.100",  # 远程 MySQL 服务器
    port=3306,
    user="douyin_user",    # 使用专门的用户
    password="strong_password",
    database="douyin_hot_comments",
    charset="utf8mb4"
)
```

### 创建专门的数据库用户

```sql
-- 创建用户
CREATE USER 'douyin'@'localhost' IDENTIFIED BY 'your_password';

-- 授权
GRANT ALL PRIVILEGES ON douyin_hot_comments.* TO 'douyin'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;
```

### 远程访问配置

如果需要从其他机器访问 MySQL：

```sql
-- 创建远程用户
CREATE USER 'douyin'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON douyin_hot_comments.* TO 'douyin'@'%';
FLUSH PRIVILEGES;
```

修改防火墙设置允许 3306 端口访问。

## 🐛 常见问题

### 问题 1：无法连接数据库

**错误信息：** `Can't connect to MySQL server`

**解决方法：**
1. 检查 MySQL 服务是否运行
   ```bash
   # Windows
   net start | findstr MySQL
   
   # Linux
   systemctl status mysql
   ```

2. 检查端口是否正确
   ```bash
   netstat -ano | findstr :3306
   ```

3. 检查用户名和密码
   ```sql
   mysql -u root -p
   ```

### 问题 2：字符集错误

**错误信息：** `Incorrect string value: '\xF0\x9F...'`

**解决方法：**
1. 确保数据库字符集为 utf8mb4
   ```sql
   SHOW CREATE DATABASE douyin_hot_comments;
   ```

2. 如果不是，删除重建：
   ```sql
   DROP DATABASE douyin_hot_comments;
   CREATE DATABASE douyin_hot_comments 
     CHARACTER SET utf8mb4 
     COLLATE utf8mb4_unicode_ci;
   ```

### 问题 3：权限不足

**错误信息：** `Access denied for user 'root'@'localhost'`

**解决方法：**
```sql
-- 重新授权
GRANT ALL PRIVILEGES ON douyin_hot_comments.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```

### 问题 4：表不存在

**错误信息：** `Table 'douyin_hot_comments.comments' doesn't exist`

**解决方法：**
1. 运行初始化脚本
   ```bash
   python -m backend.lib.database.init
   ```

2. 或在前端"数据库管理"页面点击"初始化数据库"

### 问题 5：中文乱码

**解决方法：**
1. 检查数据库字符集
   ```sql
   SHOW VARIABLES LIKE 'character_set%';
   ```

2. 确保都是 utf8mb4

3. 修改 MySQL 配置文件（my.ini 或 my.cnf）：
   ```ini
   [mysqld]
   character-set-server=utf8mb4
   collation-server=utf8mb4_unicode_ci
   
   [client]
   default-character-set=utf8mb4
   ```

4. 重启 MySQL 服务

## 📈 性能优化

### 索引优化

数据库已自动创建以下索引：

- `comments`: aweme_id, comment_id, create_time, digg_count
- `videos`: aweme_id, crawl_time
- `hot_search`: rank, crawl_time, video_id

### 批量插入

代码已实现批量插入，每次最多插入 1000 条评论，提高效率。

### 定期清理

建议定期清理旧数据：

```sql
-- 删除 30 天前的评论
DELETE FROM comments 
WHERE crawl_time < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- 删除 7 天前的热榜数据
DELETE FROM hot_search 
WHERE crawl_time < DATE_SUB(NOW(), INTERVAL 7 DAY);
```

## 📝 下一步

数据库配置完成后，你可以：

1. ✅ 配置定时任务自动保存到数据库
2. ✅ 在前端查看数据库统计信息
3. ✅ 使用 SQL 进行复杂查询和分析
4. ✅ 导出数据用于进一步分析

## 🔗 相关文档

- [MySQL 官方文档](https://dev.mysql.com/doc/)
- [PyMySQL 文档](https://pymysql.readthedocs.io/)
- [热榜评论爬取文档](./hot_comment_auto.md)
- [定时任务使用指南](./scheduler_guide.md)

---

**更新日期：** 2026-03-27  
**版本：** v1.0
