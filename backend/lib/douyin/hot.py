#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音热榜爬取工具（独立版本）
支持在任何项目中使用
"""

import requests
import json
import time
import random
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

class DouyinHotFetcher:
    """抖音热榜爬取器"""

    def __init__(self, proxy_url: Optional[str] = None):
        """初始化爬取器
        
        Args:
            proxy_url: 代理 URL，可选
        """
        self.proxy_url = proxy_url
        self.douyin_id = "douyin"
        self.douyin_name = "抖音"

    def fetch_douyin_hot(self, max_retries: int = 2) -> Optional[Dict]:
        """获取抖音热榜数据（合并 newsnow 和抖音原生接口）
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            抖音热榜数据字典，失败返回 None
        """
        try:
            # 1. 从 newsnow 获取热榜列表（带视频 URL）
            newsnow_url = "https://newsnow.busiyi.world/api/s?id=douyin&latest"
            newsnow_data = self._fetch_with_retry(newsnow_url, max_retries)
            
            if not newsnow_data:
                print("获取 newsnow 热榜失败")
                return None
            
            news_list = newsnow_data.get("items", [])
            
            # 2. 从抖音原生接口获取热值
            douyin_hot_map, douyin_time_map = self._fetch_douyin_hot_values(max_retries)
            
            # 3. 合并数据
            return self._merge_hot_data(news_list, douyin_hot_map, douyin_time_map)
            
        except Exception as e:
            print(f"获取抖音热榜失败：{e}")
            return None
    
    def _fetch_with_retry(self, url: str, max_retries: int) -> Optional[Dict]:
        """带重试的 HTTP 请求"""
        proxies = None
        if self.proxy_url:
            proxies = {"http": self.proxy_url, "https": self.proxy_url}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }
        
        retries = 0
        while retries <= max_retries:
            try:
                response = requests.get(url, proxies=proxies, headers=headers, timeout=30)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    base_wait = random.uniform(3, 5)
                    additional_wait = (retries - 1) * random.uniform(1, 2)
                    wait_time = base_wait + additional_wait
                    print(f"请求 {url} 失败：{e}. {wait_time:.2f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"请求 {url} 失败：{e}")
                    return None
        return None
    
    def _fetch_douyin_hot_values(self, max_retries: int) -> Tuple[Dict[str, str], Dict[str, str]]:
        """从抖音原生接口获取热值和事件时间
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            (热值映射，事件时间映射)
        """
        # 获取 cookie
        try:
            cookie_response = requests.get("https://login.douyin.com/", timeout=10)
            cookies = cookie_response.headers.getSetCookie()
            cookie_str = "; ".join(cookies)
        except Exception as e:
            print(f"获取抖音 cookie 失败：{e}")
            cookie_str = ""
        
        douyin_url = "https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Cookie": cookie_str,
        }
        
        hot_map = {}
        time_map = {}
        
        try:
            data = self._fetch_with_retry(douyin_url, max_retries)
            if data and "data" in data and "word_list" in data["data"]:
                for item in data["data"]["word_list"]:
                    word = item.get("word", "")
                    hot_value = item.get("hot_value", "0")
                    event_time = item.get("event_time", "")
                    
                    if word:
                        hot_map[word] = str(hot_value)
                        time_map[word] = event_time if event_time else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"从抖音原生接口获取到 {len(hot_map)} 条热榜数据")
        except Exception as e:
            print(f"获取抖音热值失败：{e}")
        
        return hot_map, time_map
    
    def _merge_hot_data(self, news_list: list, hot_map: Dict[str, str], time_map: Dict[str, str]) -> Dict:
        """合并热榜数据
        
        Args:
            news_list: newsnow 热榜列表
            hot_map: 热值映射
            time_map: 事件时间映射
            
        Returns:
            合并后的热榜数据字典
        """
        douyin_data = {}
        
        for idx, item in enumerate(news_list, 1):
            title = item.get("title", "")
            url = item.get("url", "")
            
            if not title:
                continue
            
            douyin_data[title] = {
                "ranks": [idx],
                "url": url,
                "mobileUrl": url,
                "hotValue": hot_map.get(title, "0"),
                "eventTime": time_map.get(title, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            }
        
        print(f"合并热榜数据成功，共 {len(douyin_data)} 条")
        return douyin_data

    def save_to_txt(self, douyin_data: Dict, output_dir: Optional[str] = None) -> str:
        """保存抖音热榜到文本文件
        
        Args:
            douyin_data: 抖音热榜数据
            output_dir: 输出目录，默认当前目录
            
        Returns:
            保存的文件路径
        """
        if not output_dir:
            output_dir = Path.cwd() / "douyin_output"
        else:
            output_dir = Path(output_dir)
            
        output_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M")

        txt_dir = output_dir / date_str / "txt"
        txt_dir.mkdir(parents=True, exist_ok=True)

        txt_file = txt_dir / f"douyin_hot_{date_str}_{time_str}.txt"

        try:
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(f"{self.douyin_name}热榜\n")
                f.write(f"时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总数：{len(douyin_data)}\n\n")

                for rank, (title, data) in enumerate(douyin_data.items(), 1):
                    url = data.get("url", "")
                    mobile_url = data.get("mobileUrl", "")
                    link_url = mobile_url or url

                    f.write(f"{rank}. {title}")
                    if link_url:
                        f.write(f" [URL:{link_url}]")
                    f.write("\n")

            print(f"抖音热榜已保存到：{txt_file}")
            return str(txt_file)
        except Exception as e:
            print(f"保存文本文件失败：{e}")
            # 降级到当前目录
            txt_file = Path(f"douyin_hot_{date_str}_{time_str}.txt")
            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(f"{self.douyin_name}热榜\n")
                f.write(f"时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总数：{len(douyin_data)}\n\n")

                for rank, (title, data) in enumerate(douyin_data.items(), 1):
                    url = data.get("url", "")
                    mobile_url = data.get("mobileUrl", "")
                    link_url = mobile_url or url

                    f.write(f"{rank}. {title}")
                    if link_url:
                        f.write(f" [URL:{link_url}]")
                    f.write("\n")

            print(f"抖音热榜已保存到：{txt_file}")
            return str(txt_file)


def main():
    """主函数"""
    fetcher = DouyinHotFetcher()
    douyin_data = fetcher.fetch_douyin_hot()
    
    if douyin_data:
        print(f"获取到 {len(douyin_data)} 条热榜数据")
        for rank, (title, data) in enumerate(list(douyin_data.items())[:5], 1):
            print(f"{rank}. {title} (热度：{data.get('hotValue', 'N/A')})")
    else:
        print("获取热榜数据失败")


if __name__ == "__main__":
    main()
