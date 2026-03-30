"""
路由模块

包含所有 FastAPI 路由定义。
"""

from .auth import router as auth_router
from .aria2 import router as aria2_router
from .comment import router as comment_router
from .file import router as file_router
from .hot import router as hot_router
from .hot_comment import router as hot_comment_router
from .settings import router as settings_router
from .system import router as system_router
from .task import router as task_router

__all__ = [
    "auth_router",
    "task_router",
    "comment_router",
    "settings_router",
    "aria2_router",
    "file_router",
    "system_router",
    "hot_router",
    "hot_comment_router",
]
