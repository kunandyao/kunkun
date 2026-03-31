"""
封面图片下载工具

用于下载抖音视频封面到本地静态资源目录
"""

import os
import hashlib
import requests
from typing import Optional
from loguru import logger
from backend.constants import RESOURCE_ROOT


COVER_DIR = os.path.join(RESOURCE_ROOT, "static", "covers")


def download_cover(cover_url: str, filename: Optional[str] = None) -> Optional[str]:
    """
    下载封面图片到本地
    
    Args:
        cover_url: 封面图片 URL
        filename: 自定义文件名（不含扩展名），如果不提供则使用 URL 的哈希值
    
    Returns:
        本地相对路径（如 /static/covers/xxx.jpg），失败返回 None
    """
    if not cover_url:
        return None
    
    try:
        # 确保目录存在
        os.makedirs(COVER_DIR, exist_ok=True)
        
        # 生成文件名
        if not filename:
            # 使用 URL 的哈希值作为文件名
            url_hash = hashlib.md5(cover_url.encode()).hexdigest()[:16]
            filename = url_hash
        
        # 确定扩展名
        ext = ".jpg"
        if ".png" in cover_url.lower():
            ext = ".png"
        elif ".jpeg" in cover_url.lower() or ".jpg" in cover_url.lower():
            ext = ".jpg"
        elif ".webp" in cover_url.lower():
            ext = ".webp"
        
        full_filename = f"{filename}{ext}"
        filepath = os.path.join(COVER_DIR, full_filename)
        
        # 如果文件已存在，直接返回
        if os.path.exists(filepath):
            logger.debug(f"封面已存在: {full_filename}")
            return f"/static/covers/{full_filename}"
        
        # 下载图片
        headers = {
            "Referer": "https://www.douyin.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        response = requests.get(cover_url, headers=headers, timeout=10, stream=True)
        
        if response.status_code != 200:
            logger.warning(f"下载封面失败 (status={response.status_code}): {cover_url[:60]}...")
            return None
        
        # 保存文件
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"封面下载成功: {full_filename}")
        return f"/static/covers/{full_filename}"
        
    except Exception as e:
        logger.error(f"下载封面失败: {e}")
        return None


def download_covers_batch(cover_urls: list) -> dict:
    """
    批量下载封面图片
    
    Args:
        cover_urls: 封面 URL 列表
    
    Returns:
        字典，key 为原始 URL，value 为本地路径
    """
    results = {}
    for url in cover_urls:
        if url:
            local_path = download_cover(url)
            results[url] = local_path
    return results
