import os
import random
import re
import time
from typing import Union

import requests
import ujson as json
from loguru import logger


def gen_random_str(length: int = 16, lower: bool = False) -> str:
    """生成随机字符串"""
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    if lower:
        chars = chars.lower()
    return "".join(random.choice(chars) for _ in range(length))


def get_timestamp(type: str = "ms") -> int:
    """获取当前时间戳（毫秒）"""
    if type == "ms":
        return str(int(time.time() * 1000))
    elif type == "s":
        return str(int(time.time()))
    else:
        raise ValueError("只支持 'ms' 或 's'（毫秒或秒）")


def extract_valid_urls(input_data: Union[str, list]) -> Union[str, list, None]:
    """
    提取有效的URL

    Args:
        input_data: 字符串或字符串列表

    Returns:
        提取的URL或URL列表
    """
    url_pattern = re.compile(r"https?://[^\s]+")

    if isinstance(input_data, str):
        match = url_pattern.search(input_data)
        return match.group(0) if match else input_data
    elif isinstance(input_data, list):
        return [extract_valid_urls(item) for item in input_data if item]
    return None


def sanitize_filename(
    text: str, max_bytes: int = 100, add_ellipsis: bool = True
) -> str:
    """
    生成安全的文件名

    Args:
        text: 原始文本
        max_bytes: 最大字节数（默认 100，考虑中文字符）
        add_ellipsis: 超长时是否添加省略号

    Returns:
        安全的文件名字符串
    """
    if not text or not isinstance(text, str):
        return "无标题"

    text = text.strip()
    if not text:
        return "无标题"

    # 过滤特殊字符
    # Windows 文件名禁止字符: < > : " / \ | ? *
    # 同时移除控制字符
    # illegal_chars = ["\r", "\n", "\\", "/", ":", "*", "?", '"', "<", ">", "|"]
    safe_text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)

    # 替换多个空格为单个空格
    safe_text = re.sub(r"\s+", " ", safe_text).strip()

    if not safe_text:
        return "无标题"

    # 按字节限制长度（考虑中文字符）
    if len(safe_text.encode("utf-8")) > max_bytes:
        # 按字节截断，避免截断中文字符
        safe_text_bytes = safe_text.encode("utf-8")[:max_bytes]
        # 解码时忽略不完整的字符
        safe_text = safe_text_bytes.decode("utf-8", errors="ignore").strip()
        # 添加省略号标识
        if safe_text and add_ellipsis:
            safe_text = safe_text + "..."

    return safe_text if safe_text else "无标题"


def quit(str: str = ""):
    """
    抛出异常而不是退出程序（适用于GUI应用）
    """
    if str:
        logger.error(str)
    raise Exception(str if str else "程序异常退出")


def url_redirect(url: str) -> str:
    """
    获取URL的最终重定向地址

    Args:
        url: 原始URL

    Returns:
        最终重定向的URL
    """
    r = requests.head(url, allow_redirects=True)
    return r.url


def save_json(filename: str, data: dict) -> None:
    """
    保存字典为 JSON 文件

    Args:
        filename: 文件名（包含路径）
        data: 要保存的字典数据
    """
    path = os.path.dirname(filename)
    if path:
        os.makedirs(path, exist_ok=True)

    final_path = f"{filename}.json"
    temp_path = f"{filename}.tmp"

    # 添加重试机制以处理文件占用问题
    max_retries = 5
    retry_delays = [0.2, 0.5, 1.0, 2.0, 3.0]  # 递增延迟
    
    for attempt in range(max_retries):
        try:
            # 如果目标文件已存在，先删除（避免重命名冲突）
            if os.path.exists(final_path):
                try:
                    os.remove(final_path)
                    time.sleep(0.2)  # 等待文件系统更新
                except Exception:
                    pass
            
            # 清理可能存在的旧临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    time.sleep(0.1)
                except Exception:
                    pass
            
            # 写入临时文件
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 等待写入完成
            time.sleep(0.1)
            
            # 重命名临时文件为目标文件（原子操作）
            os.rename(temp_path, final_path)
            
            logger.debug(f"✓ JSON 文件已保存：{filename}.json")
            return
        except PermissionError as e:
            if attempt < max_retries - 1:
                delay = retry_delays[attempt]
                logger.warning(f"保存文件 {filename}.json 时权限被拒绝，{delay}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                time.sleep(delay)
            else:
                logger.error(f"保存 JSON 文件 {filename} 失败，已达到最大重试次数：{e}")
                # 清理临时文件
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                raise
        except Exception as e:
            logger.error(f"保存 JSON 文件 {filename} 时出错：{e}")
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            raise
