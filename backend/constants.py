# -*- encoding: utf-8 -*-
"""
应用常量配置
统一管理项目中使用的常量，避免重复定义
"""

import os

# 兼容独立脚本运行和模块导入两种方式
try:
    from .utils.paths import get_app_root, get_resource_root
except ImportError:
    from utils.paths import get_app_root, get_resource_root

# 项目根目录（应用目录）
PROJECT_ROOT = get_app_root()
# 资源根目录（包含前端静态文件）
RESOURCE_ROOT = get_resource_root()

# 完整路径
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "download")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

# 下载配置默认值
DOWNLOAD_DEFAULTS = {
    "MAX_RETRIES": 3,
    "MAX_CONCURRENCY": 5,
}

# 默认设置（用于首次运行创建配置文件）
DEFAULT_SETTINGS = {
    "cookie": "",
    "userAgent": "",
    "downloadPath": DOWNLOAD_DIR,
    "maxRetries": DOWNLOAD_DEFAULTS["MAX_RETRIES"],
    "maxConcurrency": DOWNLOAD_DEFAULTS["MAX_CONCURRENCY"],
    "windowWidth": 1280,
    "windowHeight": 720,
    "enableIncrementalFetch": True,
}

# 服务器默认配置
SERVER_DEFAULTS = {
    "HOST": "127.0.0.1",
    "PORT": 8000,
    "DEV": False,
    "LOG_LEVEL": "info",
}
