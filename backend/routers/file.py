# -*- encoding: utf-8 -*-
"""
文件操作路由

提供文件访问、文件夹操作等接口。
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from ..constants import DOWNLOAD_DIR
from ..settings import settings

router = APIRouter(prefix="/api/file", tags=["文件操作"])


# ============================================================================
# 请求/响应模型
# ============================================================================


class OpenFolderRequest(BaseModel):
    """打开文件夹请求"""
    folder_path: str


class OpenFolderResponse(BaseModel):
    """打开文件夹响应"""
    success: bool


class CheckFileExistsRequest(BaseModel):
    """检查文件是否存在请求"""
    file_path: str


class CheckFileExistsResponse(BaseModel):
    """检查文件是否存在响应"""
    exists: bool


class ReadConfigFileRequest(BaseModel):
    """读取配置文件请求"""
    file_path: str


class ReadConfigFileResponse(BaseModel):
    """读取配置文件响应"""
    content: str


class FindLocalFileResponse(BaseModel):
    """查找本地文件响应"""
    found: bool
    video_path: str | None = None
    images: List[str] | None = None


# ============================================================================
# 路由定义
# ============================================================================


def _validate_path(file_path: str, allow_configs: bool = False) -> str:
    """验证文件路径安全性"""
    abs_path = os.path.abspath(file_path)
    download_dir = os.path.abspath(settings.get("downloadPath", DOWNLOAD_DIR))
    
    if allow_configs:
        config_dir = os.path.abspath("config")
        if abs_path.startswith(config_dir):
            return abs_path
    
    if not abs_path.startswith(download_dir):
        raise HTTPException(status_code=403, detail="路径访问被拒绝")
    return abs_path


@router.post("/open-folder", response_model=OpenFolderResponse)
def open_folder(request: OpenFolderRequest) -> Dict[str, bool]:
    """打开文件夹"""
    try:
        folder_path = _validate_path(request.folder_path)
        if os.path.isdir(folder_path):
            os.startfile(folder_path)
            return {"success": True}
        return {"success": False}
    except Exception as e:
        logger.error(f"打开文件夹失败: {e}")
        return {"success": False}


@router.post("/check-exists", response_model=CheckFileExistsResponse)
def check_file_exists(request: CheckFileExistsRequest) -> Dict[str, bool]:
    """检查文件是否存在"""
    try:
        abs_path = _validate_path(request.file_path)
        return {"exists": os.path.exists(abs_path)}
    except Exception as e:
        logger.error(f"检查文件存在失败: {e}")
        return {"exists": False}


@router.post("/read-config", response_model=ReadConfigFileResponse)
def read_config_file(request: ReadConfigFileRequest) -> Dict[str, str]:
    """读取配置文件"""
    try:
        abs_path = _validate_path(request.file_path, allow_configs=True)
        if not abs_path.endswith(".txt"):
            raise HTTPException(status_code=400, detail="只允许读取 .txt 文件")
        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f:
                return {"content": f.read()}
        return {"content": ""}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/find-local/{work_id}", response_model=FindLocalFileResponse)
def find_local_file(work_id: str) -> Dict[str, Any]:
    """查找本地已下载的文件"""
    try:
        download_dir = os.path.abspath(settings.get("downloadPath", DOWNLOAD_DIR))
        
        patterns = [
            os.path.join(download_dir, f"{work_id}.mp4"),
            os.path.join(download_dir, f"aweme_{work_id}", f"{work_id}.mp4"),
            os.path.join(download_dir, f"{work_id}_*", f"{work_id}.mp4"),
        ]
        
        video_files = []
        for pattern in patterns:
            import glob
            video_files = glob.glob(pattern)
            if video_files:
                break
        
        if video_files:
            video_files.sort(key=os.path.getmtime, reverse=True)
            rel_path = os.path.relpath(video_files[0], download_dir)
            return {
                "found": True,
                "video_path": rel_path,
                "images": None,
            }
        
        image_patterns = [
            os.path.join(download_dir, f"aweme_{work_id}"),
            os.path.join(download_dir, f"{work_id}_*"),
        ]
        
        for img_dir_pattern in image_patterns:
            import glob as g
            img_dirs = g.glob(img_dir_pattern)
            for img_dir in img_dirs:
                if os.path.isdir(img_dir):
                    import glob
                    images = sorted(
                        glob.glob(os.path.join(img_dir, "*.jpg")) + 
                        glob.glob(os.path.join(img_dir, "*.jpeg")) +
                        glob.glob(os.path.join(img_dir, "*.png")),
                        key=os.path.getmtime,
                        reverse=True
                    )
                    if images:
                        return {
                            "found": True,
                            "video_path": None,
                            "images": [os.path.relpath(img, download_dir) for img in images],
                        }
        
        return {"found": False, "video_path": None, "images": None}
    
    except Exception as e:
        logger.error(f"查找本地文件失败: {e}")
        return {"found": False, "video_path": None, "images": None}


@router.get("/media/{file_path:path}")
def serve_media(file_path: str):
    """提供媒体文件访问"""
    try:
        download_dir = os.path.abspath(settings.get("downloadPath", DOWNLOAD_DIR))
        abs_path = os.path.abspath(os.path.join(download_dir, file_path))
        
        if not abs_path.startswith(download_dir):
            raise HTTPException(status_code=403, detail="路径访问被拒绝")
        
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        from starlette.responses import FileResponse
        return FileResponse(abs_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"媒体文件访问失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))