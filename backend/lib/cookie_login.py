# -*- encoding: utf-8 -*-
"""
Cookie 登录模块

提供通过登录获取 Cookie 的功能。
"""

import webbrowser
from dataclasses import dataclass


@dataclass
class CookieLoginResult:
    """Cookie 登录结果"""

    success: bool = False
    cookie: str = ""
    user_agent: str = ""
    error: str = ""


def get_cookie_by_login() -> CookieLoginResult:
    """
    通过登录获取 Cookie

    打开抖音登录页面，用户完成登录后手动复制 Cookie。

    Returns:
        CookieLoginResult: 登录结果对象
    """
    try:
        # 打开抖音登录页面
        login_url = "https://www.douyin.com"
        webbrowser.open(login_url, new=2)
        
        print("[OK] 已打开抖音登录页面")
        print("请在浏览器中完成登录，然后按以下步骤获取 Cookie:")
        print("1. 按 F12 打开开发者工具")
        print("2. 切换到 Network (网络) 标签")
        print("3. 刷新页面")
        print("4. 点击任意请求，查看 Request Headers")
        print("5. 复制 Cookie 字段的值")
        print("6. 粘贴到系统设置的 Cookie 输入框中")
        
        # 返回成功，但 cookie 为空，需要用户手动输入
        return CookieLoginResult(
            success=True,
            cookie='',
            user_agent='',
            error='已打开登录页面，请手动获取 Cookie'
        )
        
    except Exception as e:
        return CookieLoginResult(
            success=False,
            cookie='',
            user_agent='',
            error=f'打开登录页面失败：{str(e)}'
        )
