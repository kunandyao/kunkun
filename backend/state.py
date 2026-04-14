# -*- encoding: utf-8 -*-
"""
应用运行时状态管理模块

管理任务状态、Aria2 连接等运行时资源。
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from .constants import DOWNLOAD_DEFAULTS, DOWNLOAD_DIR
from .settings import settings


class AppState:
    """
    应用运行时状态管理

    负责管理：
    - 任务状态和结果
    - Aria2 管理器
    - 运行时资源清理
    """

    def __init__(self) -> None:
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("🚀 应用状态初始化中...")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 任务状态
        self.task_status: Dict[str, Dict[str, Any]] = {}
        self.task_results: Dict[str, List[Dict[str, Any]]] = {}
        
        # 兼容旧代码，虽然 Aria2 功能已移除
        self.aria2_config_paths: Dict[str, str] = {}
        
        # 最新爬取的热榜评论文件列表
        self.latest_hot_comment_files: List[str] = []
        
        # 热榜评论爬取状态
        self.hot_comment_crawling: bool = False
        self.hot_comment_crawl_result: Optional[Dict[str, Any]] = None

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.success("✓ 应用状态初始化完成")
        logger.info(f"  - 下载目录: {settings.get('downloadPath')}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "ready": True,
            "error": None,
        }

    def cleanup(self) -> None:
        """清理资源"""
        logger.info("🧹 开始清理资源...")
        logger.info("✓ 资源清理完成")


# 全局实例，直接导入使用
state = AppState()
