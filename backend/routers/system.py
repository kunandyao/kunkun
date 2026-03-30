"""
系统工具路由

提供系统相关功能接口，如剪贴板访问和打开外部链接。
"""

import os
import subprocess
import webbrowser
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from ..lib.cookie_login import get_cookie_by_login

router = APIRouter(prefix="/api/system", tags=["系统工具"])

_received_cookie: Optional[Dict[str, str]] = None


# ============================================================================
# 请求/响应模型
# ============================================================================


class OpenUrlRequest(BaseModel):
    """打开 URL 请求"""

    url: str


class ClipboardResponse(BaseModel):
    """剪贴板响应"""

    text: str


class OpenUrlResponse(BaseModel):
    """打开 URL 响应"""

    status: str
    message: str


class CookieLoginResponse(BaseModel):
    """Cookie 登录获取响应"""

    success: bool
    cookie: str = ""
    user_agent: str = ""
    error: str = ""


class ReceiveCookieRequest(BaseModel):
    """接收 Cookie 请求"""

    cookie: str
    user_agent: str = ""
    source: str = ""


class ReceiveCookieResponse(BaseModel):
    """接收 Cookie 响应"""

    success: bool
    message: str = ""


# ============================================================================
# 路由定义
# ============================================================================


@router.get("/clipboard", response_model=ClipboardResponse)
def get_clipboard_text() -> Dict[str, str]:
    """
    获取系统剪贴板内容

    返回剪贴板中的文本内容。
    """
    try:
        import pyperclip

        text = pyperclip.paste()
        if text:
            cleaned_text = text.strip()
            logger.debug(f"读取剪贴板成功，长度: {len(cleaned_text)}")
            return {"text": cleaned_text}
        return {"text": ""}

    except ImportError:
        logger.warning("pyperclip 未安装，无法读取剪贴板")
        return {"text": ""}
    except Exception as e:
        logger.warning(f"读取剪贴板失败: {e}")
        return {"text": ""}


@router.post("/open-url", response_model=OpenUrlResponse)
def open_url(request: OpenUrlRequest) -> Dict[str, str]:
    """
    打开外部链接

    使用系统默认浏览器打开指定的 URL。
    """
    url = request.url

    if not url:
        raise HTTPException(status_code=400, detail="URL 不能为空")

    logger.info(f"打开 URL: {url}")

    try:
        webbrowser.open(url)
        logger.debug(f"URL 已打开: {url}")
        return {"status": "success", "message": "URL 已打开"}
    except Exception as e:
        logger.error(f"打开 URL 失败: {e}")
        raise HTTPException(status_code=500, detail=f"打开 URL 失败: {e}")


@router.post("/cookie-login", response_model=CookieLoginResponse)
def cookie_login() -> Dict[str, Any]:
    """
    通过登录获取 Cookie

    打开抖音登录页面，引导用户登录后手动获取 Cookie。
    """
    logger.info("[START] 开始通过登录获取 Cookie...")
    
    try:
        result = get_cookie_by_login()
        
        if result.success:
            logger.success("[OK] Cookie 登录获取成功")
            return {
                "success": True,
                "cookie": result.cookie,
                "user_agent": result.user_agent,
                "error": result.error,
            }
        else:
            logger.warning(f"[ERROR] Cookie 登录获取失败：{result.error}")
            return {
                "success": False,
                "cookie": "",
                "user_agent": "",
                "error": result.error,
            }
            
    except Exception as e:
        logger.error(f"[ERROR] Cookie 登录获取异常：{e}")
        return {
            "success": False,
            "cookie": "",
            "user_agent": "",
            "error": str(e),
        }


@router.post("/receive-cookie", response_model=ReceiveCookieResponse)
def receive_cookie(request: ReceiveCookieRequest) -> Dict[str, Any]:
    """
    接收来自浏览器扩展的 Cookie

    由浏览器扩展调用，将 Cookie 发送到应用。
    """
    global _received_cookie
    
    logger.info(f"[START] 接收到 Cookie，来源: {request.source}")
    
    if not request.cookie:
        return {"success": False, "message": "Cookie 为空"}
    
    _received_cookie = {
        "cookie": request.cookie,
        "user_agent": request.user_agent,
        "source": request.source,
    }
    
    logger.success(f"[OK] Cookie 已保存，长度: {len(request.cookie)}")
    
    return {"success": True, "message": "Cookie 已接收"}


@router.get("/received-cookie", response_model=CookieLoginResponse)
def get_received_cookie() -> Dict[str, Any]:
    """
    获取已接收的 Cookie

    前端轮询此接口获取浏览器扩展发送的 Cookie。
    """
    global _received_cookie
    
    if _received_cookie:
        result = {
            "success": True,
            "cookie": _received_cookie["cookie"],
            "user_agent": _received_cookie.get("user_agent", ""),
            "error": "",
        }
        _received_cookie = None
        return result
    
    return {"success": False, "cookie": "", "user_agent": "", "error": "暂无接收到的 Cookie"}
