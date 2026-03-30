# 定时自动爬取 - 快速开始

## 🎉 功能特点

- ✅ **每 2 小时自动执行**：无需手动启动
- ✅ **完全自动化**：无需询问，自动爬取
- ✅ **自动保存 CSV**：评论数据自动导出
- ✅ **详细日志**：记录每次爬取结果
- ✅ **支持后台运行**：不占用前台

## 🚀 三种启动方式

### 方式 1：双击运行（最简单）

**步骤：**
1. 双击 `start_scheduler.bat`
2. 自动开始定时爬取
3. 按 Ctrl+C 停止

**适合：** 临时使用，白天运行

---

### 方式 2：命令行运行

```bash
# 定时运行（每 2 小时）
python scheduler_hot_comment.py --interval 2

# 只运行一次（测试用）
python scheduler_hot_comment.py --run-once

# 自定义参数
python scheduler_hot_comment.py \
  --interval 4 \              # 每 4 小时
  --video-count 20 \          # 20 个视频
  --comments-per-video 200    # 每个 200 条评论
```

**适合：** 测试和调试

---

### 方式 3：Windows 任务计划（推荐长期使用）

**效果：**
- ✅ 开机自动启动
- ✅ 后台静默运行
- ✅ 无需打开命令行窗口
- ✅ 系统重启后继续运行

**配置步骤：**

#### 1. 打开任务计划程序
- 按 `Win + R`
- 输入 `taskschd.msc`
- 按回车

#### 2. 创建任务
- 点击"创建基本任务"
- 名称：`抖音热榜评论自动爬取`
- 触发器：每天
- 开始时间：`00:00:00`（或其他时间）

#### 3. 配置程序
- 操作：启动程序
- 程序/脚本：`python`
- 添加参数：
  ```
  scheduler_hot_comment.py --interval 2 --video-count 10
  ```
- 起始于：`d:\Project_graduation\douyin-main`

#### 4. 配置重复执行
- 创建完成后双击任务
- 触发器 → 编辑
- 勾选"重复任务间隔"
- 选择"2 小时"
- 持续时间选择"无限期"

#### 5. 高级设置
- 常规 → 勾选"不管用户是否登录都要运行"
- 常规 → 勾选"使用最高权限运行"
- 条件 → 取消"只在交流电源下运行"

---

## 📁 输出文件

### 评论数据（CSV 格式）

```
downloads/hot_comments/
├── comments_7621407717302814634_20260326_235135.csv
├── comments_7621407717302814635_20260326_235135.csv
└── summary_20260326_235135.txt
```

**CSV 内容示例：**
```csv
id,nickname,text,create_time,digg_count,reply_count,ip_label,is_top,is_hot
1,用户昵称，评论内容，2026-03-26,123,5,北京,false,false
```

### 日志文件

```
logs/
├── hot_comment_2026-03-26.log
└── hot_comment_2026-03-27.log
```

**日志内容示例：**
```
23:51:27 | INFO | 从热榜话题页面提取到视频 ID: 7621407717302814634
23:51:35 | INFO | 爬取到 100 条评论
23:51:35 | INFO | 评论已保存到：downloads\hot_comments\comments_7621407717302814634_20260326_235135.csv
23:51:35 | INFO | ✓ 爬取成功
23:51:35 | INFO |   总评论数：985
```

---

## ⚙️ 参数配置

### 修改爬取频率

编辑 `start_scheduler.bat` 或命令行参数：

```bash
# 每 1 小时
python scheduler_hot_comment.py --interval 1

# 每 4 小时
python scheduler_hot_comment.py --interval 4

# 每 12 小时
python scheduler_hot_comment.py --interval 12
```

### 修改爬取数量

```bash
# 爬取 5 个视频
python scheduler_hot_comment.py --video-count 5

# 爬取 30 个视频
python scheduler_hot_comment.py --video-count 30

# 每个视频 50 条评论
python scheduler_hot_comment.py --comments-per-video 50

# 每个视频 500 条评论
python scheduler_hot_comment.py --comments-per-video 500
```

### 修改输出目录

```bash
python scheduler_hot_comment.py --output-dir "D:/data/douyin"
```

---

## 📊 运行示例

### 启动日志

```
23:51:20 | INFO | 定时爬取器已初始化
23:51:20 | INFO |   爬取间隔：2 小时
23:51:20 | INFO |   热榜视频数：10
23:51:20 | INFO |   每视频评论数：100
23:51:20 | INFO |   输出目录：downloads\hot_comments
23:51:20 | INFO | ============================================================
23:51:20 | INFO | 开始执行爬取任务：2026-03-26 23:51:20
```

### 爬取过程

```
23:51:25 | INFO | 获取到 10 个热榜视频
23:51:25 | INFO |   - 1. 我的春日粉彩妆容公式
23:51:25 | INFO |   - 2. 内存条降价
23:51:25 | INFO |   - 3. 赴一场山河之约
23:51:25 | INFO | [1/10] 处理：我的春日粉彩妆容公式
23:51:27 | INFO | 从热榜话题页面提取到视频 ID: 7621407717302814634
23:51:35 | INFO | 爬取到 100 条评论
23:51:35 | INFO | 评论已保存到 CSV
```

### 完成日志

```
23:53:00 | INFO | ✓ 爬取成功
23:53:00 | INFO |   总评论数：985
23:53:00 | INFO |   成功视频数：10
23:53:00 | INFO |   摘要已保存
23:53:00 | INFO | ============================================================
23:53:00 | INFO | 下次爬取时间：2026-03-27 01:53:00
```

---

## 🔧 常见问题

### Q1: 如何停止定时任务？

**方式 1（命令行）：** 按 `Ctrl+C`

**方式 2（任务计划）：**
1. 打开任务计划程序
2. 找到"抖音热榜评论自动爬取"
3. 右键 → 禁用

### Q2: 如何查看爬取结果？

**查看 CSV：**
```bash
# 打开最新 CSV
start downloads/hot_comments/comments_*.csv

# 打开摘要
start downloads/hot_comments/summary_*.txt
```

**查看日志：**
```bash
# 打开最新日志
start logs/hot_comment_*.log
```

### Q3: Cookie 过期了怎么办？

1. 在设置中更新 Cookie
2. 重启定时任务
3. 无需其他配置

### Q4: 如何确认任务在运行？

**方法 1：** 查看日志文件，看是否有最新记录

**方法 2：** 查看输出目录，看是否有新的 CSV 文件

**方法 3：** 任务计划程序 → 查看运行历史

---

## 💡 最佳实践

### 1. 首次使用

```bash
# 先测试运行一次
python scheduler_hot_comment.py --run-once

# 确认正常后启动定时任务
python scheduler_hot_comment.py --interval 2
```

### 2. 日常监控

每天查看一次日志：
```bash
# 查看今天的日志
type logs/hot_comment_%date:~0,4%%date:~5,2%%date:~8,2%.log
```

### 3. 定期清理

每周清理旧文件：
```bash
# 删除 7 天前的日志
forfiles /p logs /s /m *.log /d -7 /c "cmd /c del @path"

# 删除 30 天前的 CSV
forfiles /p downloads/hot_comments /s /m *.csv /d -30 /c "cmd /c del @path"
```

### 4. 数据备份

定期备份评论数据：
```bash
# 复制到备份目录
xcopy downloads\hot_comments\*.csv D:\backup\douyin\ /Y
```

---

## 📝 推荐配置

### 个人使用

```bash
python scheduler_hot_comment.py \
  --interval 4 \              # 每 4 小时（每天 6 次）
  --video-count 10 \          # 10 个视频
  --comments-per-video 100    # 每个 100 条
```

**数据量：** 约 6000 条评论/天

### 数据分析

```bash
python scheduler_hot_comment.py \
  --interval 2 \              # 每 2 小时（每天 12 次）
  --video-count 20 \          # 20 个视频
  --comments-per-video 200    # 每个 200 条
```

**数据量：** 约 48000 条评论/天

### 长期监控

```bash
python scheduler_hot_comment.py \
  --interval 1 \              # 每 1 小时（每天 24 次）
  --video-count 30 \          # 30 个视频
  --comments-per-video 50     # 每个 50 条
```

**数据量：** 约 36000 条评论/天

---

## 🎯 总结

**一键启动，全自动运行！**

1. **启动方式：** 双击 `start_scheduler.bat`
2. **运行频率：** 每 2 小时自动执行
3. **输出位置：** `downloads/hot_comments/`
4. **日志位置：** `logs/hot_comment_YYYY-MM-DD.log`
5. **停止方法：** 按 Ctrl+C 或禁用任务计划

**完全自动化，无需任何手动操作！** 🎉
