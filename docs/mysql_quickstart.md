# MySQL 快速入门指南

## 🚀 5 分钟快速配置

### 步骤 1：检查 MySQL 是否已安装

**Windows 用户：**
```cmd
mysql --version
```

如果显示版本号，说明已安装。否则请下载安装 [MySQL Installer](https://dev.mysql.com/downloads/installer/)

### 步骤 2：创建数据库

打开命令行，登录 MySQL：
```bash
mysql -u root -p
```

输入密码后，执行：
```sql
CREATE DATABASE douyin_hot_comments CHARACTER SET utf8mb4;
EXIT;
```

### 步骤 3：修改配置

编辑文件 `backend/lib/database/config.py`，修改密码：

```python
db_config = MySQLConfig(
    host="localhost",
    port=3306,
    user="root",
    password="你的 MySQL 密码",  # ← 修改这里
    database="douyin_hot_comments",
    charset="utf8mb4"
)
```

### 步骤 4：初始化数据库

```bash
cd d:\Project_graduation\douyin-main
python -m backend.lib.database.init
```

看到以下信息表示成功：
```
✓ 数据库初始化完成
  - 数据库：douyin_hot_comments
  - 主机：localhost:3306
  - 用户：root
```

### 步骤 5：使用数据库

**方式 1：前端界面**

1. 启动后端：`python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000`
2. 访问：http://localhost:8000
3. 选择"热榜评论"
4. 勾选"保存到数据库"
5. 点击"开始爬取"

**方式 2：API 调用**

```bash
curl -X POST http://localhost:8000/api/hot-comment/crawl \
  -H "Content-Type: application/json" \
  -d '{"video_count": 10, "comments_per_video": 100, "save_to_db": true}'
```

## ✅ 验证安装

**检查数据库连接：**
```bash
python -m backend.lib.database.init test
```

**查看数据库表：**
```bash
mysql -u root -p -e "USE douyin_hot_comments; SHOW TABLES;"
```

应该看到 4 个表：
- comments
- hot_search
- videos
- scheduler_history

## 🎯 常用操作

### 查看最新评论

```sql
USE douyin_hot_comments;

SELECT nickname, text, digg_count, create_time
FROM comments
ORDER BY crawl_time DESC
LIMIT 10;
```

### 查看统计数据

```sql
SELECT 
  (SELECT COUNT(*) FROM hot_search) as 热榜数,
  (SELECT COUNT(*) FROM videos) as 视频数,
  (SELECT COUNT(*) FROM comments) as 评论数;
```

### 清空数据

```sql
TRUNCATE TABLE comments;
TRUNCATE TABLE videos;
TRUNCATE TABLE hot_search;
TRUNCATE TABLE scheduler_history;
```

## ❓ 遇到问题？

### 问题：找不到 mysql 命令

**解决：**
- Windows：MySQL 默认安装在 `C:\Program Files\MySQL\MySQL Server X.X\bin\mysql.exe`
- 使用完整路径或添加到环境变量

### 问题：无法连接数据库

**解决：**
1. 检查 MySQL 服务是否运行
   ```cmd
   net start | findstr MySQL
   ```
2. 检查密码是否正确
3. 检查端口是否为 3306

### 问题：中文乱码

**解决：**
确保创建数据库时指定了 `CHARACTER SET utf8mb4`

## 📖 详细文档

查看完整文档：[mysql_integration.md](./mysql_integration.md)

## 🔗 相关资源

- [MySQL 下载安装](https://dev.mysql.com/downloads/installer/)
- [MySQL 入门教程](https://www.w3schools.com/mysql/)
- [本项目数据库文档](./mysql_integration.md)

---

**提示：** 如果不想使用数据库，可以继续使用 CSV 方式，只需不勾选"保存到数据库"选项即可。
