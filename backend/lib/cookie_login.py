# -*- encoding: utf-8 -*-
"""
Cookie 登录模块

提供通过 Selenium 自动化浏览器获取 Cookie 的功能。
"""

import json
import os
import time
import webbrowser
from dataclasses import dataclass
from typing import Optional

from loguru import logger


@dataclass
class CookieLoginResult:
    """Cookie 登录结果"""

    success: bool = False
    cookie: str = ""
    user_agent: str = ""
    error: str = ""


def get_cookie_by_selenium(headless: bool = False) -> CookieLoginResult:
    """
    通过 Selenium 自动化浏览器获取 Cookie

    启动 Chrome 浏览器，用户登录后自动提取 Cookie。

    Args:
        headless: 是否使用无头模式（默认 False，显示浏览器窗口）

    Returns:
        CookieLoginResult: 登录结果对象
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            use_webdriver_manager = True
        except ImportError:
            use_webdriver_manager = False
            logger.warning("webdriver-manager 未安装，使用系统 ChromeDriver")

        logger.info("正在启动 Chrome 浏览器...")

        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if use_webdriver_manager:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)

        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
            },
        )

        driver.get("https://www.douyin.com")
        logger.info("浏览器已打开抖音首页")
        logger.info("请在浏览器中完成登录（扫码或账号密码）")
        logger.info("登录完成后，此窗口将自动继续...")

        print("\n" + "=" * 50)
        print("请在浏览器中登录抖音")
        print("登录完成后按 Enter 键继续...")
        print("=" * 50 + "\n")

        input()

        cookies = driver.get_cookies()
        user_agent = driver.execute_script("return navigator.userAgent")

        driver.quit()

        if not cookies:
            return CookieLoginResult(
                success=False,
                cookie="",
                user_agent="",
                error="未获取到 Cookie，请确保已登录",
            )

        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        cookie_dict = {c["name"]: c["value"] for c in cookies}
        cookie_json_path = os.path.join(os.getcwd(), "douyin_cookies.json")
        with open(cookie_json_path, "w", encoding="utf-8") as f:
            json.dump(cookie_dict, f, ensure_ascii=False, indent=2)
        logger.info(f"Cookie 已保存到 {cookie_json_path}")

        logger.success(f"成功获取 {len(cookies)} 条 Cookie")

        return CookieLoginResult(
            success=True,
            cookie=cookie_str,
            user_agent=user_agent,
            error="",
        )

    except ImportError as e:
        error_msg = f"缺少依赖: {e}。请运行: pip install selenium webdriver-manager"
        logger.error(error_msg)
        return CookieLoginResult(
            success=False,
            cookie="",
            user_agent="",
            error=error_msg,
        )
    except Exception as e:
        error_msg = f"获取 Cookie 失败: {str(e)}"
        logger.error(error_msg)
        return CookieLoginResult(
            success=False,
            cookie="",
            user_agent="",
            error=error_msg,
        )


def get_cookie_by_login() -> CookieLoginResult:
    """
    通过登录获取 Cookie（使用 Selenium 自动化）

    Returns:
        CookieLoginResult: 登录结果对象
    """
    return get_cookie_by_selenium(headless=False)


def get_cookie_manual() -> CookieLoginResult:
    """
    手动获取 Cookie（打开浏览器让用户手动复制）

    Returns:
        CookieLoginResult: 登录结果对象
    """
    try:
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

        return CookieLoginResult(
            success=True,
            cookie="",
            user_agent="",
            error="已打开登录页面，请手动获取 Cookie",
        )

    except Exception as e:
        return CookieLoginResult(
            success=False,
            cookie="",
            user_agent="",
            error=f"打开登录页面失败：{str(e)}",
        )
