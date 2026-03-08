# Aria2 可执行文件目录

## 📦 说明

此目录用于存放aria2c可执行文件，实现开箱即用的下载功能。

## 📥 下载Aria2

### Windows用户（自动脚本若因 GitHub 限流失败，可改用手动）

**方式一：直接下载（推荐）**

1. 打开浏览器访问：  
   **https://github.com/aria2/aria2/releases/download/1.37.0/aria2-1.37.0-win-64bit-build1.zip**
2. 下载完成后解压 zip，在解压出的文件夹里找到 **aria2c.exe**
3. 将 **aria2c.exe** 复制到本项目的 **aria2** 目录下（与本文档同级），即：  
   `douyin-main\aria2\aria2c.exe`

**方式二：从 Releases 页选版本**

1. 访问 [Aria2 Releases](https://github.com/aria2/aria2/releases)
2. 下载 `aria2-*-win-64bit-build1.zip`
3. 解压后将 **aria2c.exe** 复制到本项目的 **aria2** 目录

## 🔧 自动下载脚本

运行以下命令自动下载aria2c.exe：

```powershell
# Windows PowerShell
.\scripts\setup\aria2.ps1
```

## ⚠️ 注意事项

1. **版权说明**
   - Aria2是开源软件，遵循GPL-2.0许可证
   - 项目地址：https://github.com/aria2/aria2

2. **跨平台支持**
   - Windows: aria2c.exe
   - Linux: aria2c
   - Mac: aria2c

## 🚀 使用方式

程序会自动检测并使用此目录下的aria2c：

1. 优先使用 `aria2/aria2c.exe`（内置）
2. 其次使用系统PATH中的 `aria2c`（已安装）
3. 如果都没有，提示用户下载
