# Scripts 目录说明

本目录包含所有构建和配置脚本。

## 📁 目录结构

```
scripts/
├── build/              # 打包脚本
├── setup/              # 环境配置
├── dev.ps1             # 开发环境构建
├── douyin_comment_crawler.py   # 抖音评论爬取工具（独立脚本）
└── requirements-comment-crawler.txt  # 评论爬虫依赖
```

## 🚀 使用方法

### 推荐方式：使用快速启动菜单

```powershell
# 在项目根目录运行
.\quick-start.ps1
```

### 直接运行脚本

```powershell
# 首次配置
.\scripts\setup\uv.ps1
.\scripts\setup\aria2.ps1

# 开发
.\scripts\dev.ps1
uv run python main.py

# 打包
.\scripts\build\pyinstaller.ps1
```

## 📝 脚本说明

### 环境配置 (setup/)

- **uv.ps1** - 配置 uv 虚拟环境
  - 创建 `.venv` 虚拟环境
  - 配置清华镜像源
  - 安装项目依赖和 PyInstaller

- **aria2.ps1** - 下载 aria2 工具
  - 从 GitHub 自动下载最新版
  - 解压到 `aria2/` 目录
  - 验证安装

### 开发构建 (dev.ps1)

- 安装 Python 依赖
- 构建前端资源（React + Vite）
- 创建必要目录
- 不生成可执行文件

### 打包脚本 (build/)

- **pyinstaller.ps1** - PyInstaller 打包（推荐）
  - 支持目录模式和单文件模式
  - 自动构建前端
  - 生成发布包
  - 打包时间：1-2 分钟

- **nuitka.ps1** - Nuitka 打包（实验性）
  - 编译为原生代码
  - 性能更好但编译时间长
  - 需要 MinGW64 编译器
  - 打包时间：3-5 分钟

## 💡 常用命令

```powershell
# 开发模式（快速迭代）
.\scripts\dev.ps1
uv run python main.py

# 打包发布（推荐目录模式）
.\scripts\build\pyinstaller.ps1 -Mode dir

# 打包发布（单文件模式）
.\scripts\build\pyinstaller.ps1 -Mode onefile

# 清理后重新构建
.\scripts\dev.ps1 -Clean
.\scripts\build\pyinstaller.ps1 -Clean
```

## 🔧 参数说明

### pyinstaller.ps1

- `-Mode dir` - 目录模式（默认，启动快）
- `-Mode onefile` - 单文件模式（便于分发）
- `-Clean` - 清理旧文件后重新打包

### dev.ps1

- `-Clean` - 清理旧文件后重新构建

## 📦 打包产物

- **目录模式**: `dist/DouyinCrawler/DouyinCrawler.exe`
- **单文件模式**: `dist/DouyinCrawler.exe`
- **发布包**: `release/DouyinCrawler_*.zip`

## 📥 评论爬取工具（独立脚本）

**douyin_comment_crawler.py** 用于爬取指定抖音视频的评论列表（含点赞数、回复等），输出为 CSV。

- **依赖**：需单独安装 `DrissionPage`（浏览器自动化），与主项目依赖隔离。
  ```powershell
  pip install -r scripts/requirements-comment-crawler.txt
  ```
- **运行**：需本机已安装 Chrome 或 Edge。
  ```powershell
  python scripts/douyin_comment_crawler.py
  ```
- 按提示输入视频 URL、最大页数，可选先登录再爬取。评论将保存到 `crawled_comments/` 目录。

## ⚠️ 注意事项

1. 首次使用必须先运行 `.\scripts\setup\uv.ps1`
2. 下载功能需要 aria2，运行 `.\scripts\setup\aria2.ps1` 安装
3. 打包前必须先构建前端：`.\scripts\dev.ps1`
4. 所有脚本使用 uv 管理虚拟环境，确保依赖隔离
