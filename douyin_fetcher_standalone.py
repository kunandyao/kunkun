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
            proxy_url: 代理URL，可选
        """
        self.proxy_url = proxy_url
        self.douyin_id = "douyin"
        self.douyin_name = "抖音"

    def fetch_douyin_hot(self, max_retries: int = 2) -> Optional[Dict]:
        """获取抖音热榜数据
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            抖音热榜数据字典，失败返回 None
        """
        url = f"https://newsnow.busiyi.world/api/s?id={self.douyin_id}&latest"

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
                response = requests.get(url, proxies=proxies, headers=headers, timeout=10)
                response.raise_for_status()

                data_text = response.text
                data_json = json.loads(data_text)

                status = data_json.get("status", "未知")
                if status not in ["success", "cache"]:
                    raise ValueError(f"响应状态异常: {status}")

                status_info = "最新数据" if status == "success" else "缓存数据"
                print(f"获取抖音热榜成功（{status_info}）")

                return self._parse_douyin_data(data_json)

            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    base_wait = random.uniform(3, 5)
                    additional_wait = (retries - 1) * random.uniform(1, 2)
                    wait_time = base_wait + additional_wait
                    print(f"请求抖音热榜失败: {e}. {wait_time:.2f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"请求抖音热榜失败: {e}")
                    return None
        return None

    def _parse_douyin_data(self, data_json: Dict) -> Dict:
        """解析抖音热榜数据
        
        Args:
            data_json: API返回的JSON数据
            
        Returns:
            解析后的数据字典
        """
        douyin_data = {}
        for index, item in enumerate(data_json.get("items", []), 1):
            title = item["title"]
            url = item.get("url", "")
            mobile_url = item.get("mobileUrl", "")

            douyin_data[title] = {
                "ranks": [index],
                "url": url,
                "mobileUrl": mobile_url,
                "hotValue": item.get("hotValue", ""),
            }

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
                f.write(f"时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总数: {len(douyin_data)}\n\n")

                for rank, (title, data) in enumerate(douyin_data.items(), 1):
                    url = data.get("url", "")
                    mobile_url = data.get("mobileUrl", "")
                    link_url = mobile_url or url

                    f.write(f"{rank}. {title}")
                    if link_url:
                        f.write(f" [URL:{link_url}]")
                    f.write("\n")

            print(f"抖音热榜已保存到: {txt_file}")
            return str(txt_file)
        except Exception as e:
            print(f"保存文本文件失败: {e}")
            # 降级到当前目录
            fallback_file = output_dir / f"douyin_hot_{date_str}_{time_str}.txt"
            with open(fallback_file, "w", encoding="utf-8") as f:
                f.write(f"{self.douyin_name}热榜\n")
                f.write(f"时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总数: {len(douyin_data)}\n\n")
                
            print(f"已保存到降级路径: {fallback_file}")
            return str(fallback_file)

    def generate_html_report(self, douyin_data: Dict, output_dir: Optional[str] = None) -> str:
        """生成抖音热榜HTML报告
        
        Args:
            douyin_data: 抖音热榜数据
            output_dir: 输出目录，默认当前目录
            
        Returns:
            生成的HTML文件路径
        """
        if not output_dir:
            output_dir = Path.cwd() / "douyin_output"
        else:
            output_dir = Path(output_dir)
            
        output_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        date_str = now.strftime("%Y%m%d")

        html_dir = output_dir / date_str / "html"
        html_dir.mkdir(parents=True, exist_ok=True)

        html_file = html_dir / f"douyin_hot_{date_str}.html"

        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        total_count = len(douyin_data)

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>抖音热点榜</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js" integrity="sha512-BNaRQnYJYiPSqHHDb58B0yaPfCu+Wgds8Gp/gU33kqBtgNS4tSPHuGibyoeqMV/TJlSKda6FXzoEyYGjTe+vXA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            margin: 0; 
            padding: 16px; 
            background: #fafafa;
            color: #333;
            line-height: 1.5;
        }}
        
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 16px rgba(0,0,0,0.06);
        }}
        
        .header {{
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
            color: white;
            padding: 32px 24px;
            text-align: center;
            position: relative;
        }}
        
        .save-buttons {{
            position: absolute;
            top: 16px;
            right: 16px;
            display: flex;
            gap: 8px;
        }}
        
        .save-btn {{
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s ease;
            backdrop-filter: blur(10px);
            white-space: nowrap;
        }}
        
        .save-btn:hover {{
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.5);
            transform: translateY(-1px);
        }}
        
        .header-title {{
            font-size: 22px;
            font-weight: 700;
            margin: 0 0 20px 0;
        }}
        
        .header-info {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            font-size: 14px;
            opacity: 0.95;
        }}
        
        .info-item {{
            text-align: center;
        }}
        
        .info-label {{
            display: block;
            font-size: 12px;
            opacity: 0.8;
            margin-bottom: 4px;
        }}
        
        .info-value {{
            font-weight: 600;
            font-size: 16px;
        }}
        
        .content {{
            padding: 24px;
        }}
        
        .news-item {{
            margin-bottom: 16px;
            padding: 16px;
            border-radius: 8px;
            background: #f8f9fa;
            position: relative;
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }}
        
        .news-rank {{
            color: #ff6b6b;
            font-size: 18px;
            font-weight: 700;
            min-width: 24px;
            text-align: center;
            flex-shrink: 0;
        }}
        
        .news-rank.top {{
            color: #dc2626;
            font-size: 20px;
        }}
        
        .news-content {{
            flex: 1;
            min-width: 0;
        }}
        
        .news-title {{
            font-size: 15px;
            line-height: 1.4;
            color: #1a1a1a;
            margin: 0 0 8px 0;
        }}
        
        .news-link {{
            color: #2563eb;
            text-decoration: none;
        }}
        
        .news-link:hover {{
            text-decoration: underline;
        }}
        
        .footer {{
            margin-top: 32px;
            padding: 20px 24px;
            background: #f8f9fa;
            border-top: 1px solid #e5e7eb;
            text-align: center;
        }}
        
        .footer-content {{
            font-size: 13px;
            color: #6b7280;
            line-height: 1.6;
        }}
        
        .project-name {{
            font-weight: 600;
            color: #374151;
        }}
        
        @media (max-width: 480px) {{
            body {{ padding: 12px; }}
            .header {{ padding: 24px 20px; }}
            .content {{ padding: 20px; }}
            .footer {{ padding: 16px 20px; }}
            .header-info {{ grid-template-columns: 1fr; gap: 12px; }}
            .save-buttons {{
                position: static;
                margin-bottom: 16px;
                display: flex;
                gap: 8px;
                justify-content: center;
                flex-direction: column;
                width: 100%;
            }}
            .save-btn {{
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="save-buttons">
                <button class="save-btn" onclick="saveAsImage()">保存为图片</button>
            </div>
            <h1 class="header-title">抖音热点榜</h1>
            <div class="header-info">
                <div class="info-item">
                    <span class="info-label">更新时间</span>
                    <span class="info-value">{now_str}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">热点数量</span>
                    <span class="info-value">{total_count}</span>
                </div>
            </div>
        </div>
        
        <div class="content">
"""

        for rank, (title, data) in enumerate(douyin_data.items(), 1):
            url = data.get("url", "")
            mobile_url = data.get("mobileUrl", "")
            link_url = mobile_url or url

            rank_class = "top" if rank <= 3 else ""

            if link_url:
                title_html = f'<a href="{link_url}" target="_blank" class="news-link">{title}</a>'
            else:
                title_html = title

            html_content += f"""
            <div class="news-item">
                <div class="news-rank {rank_class}">{rank}</div>
                <div class="news-content">
                    <h3 class="news-title">{title_html}</h3>
                </div>
            </div>
"""

        html_content += f"""
        </div>
        
        <div class="footer">
            <div class="footer-content">
                <span class="project-name">抖音热榜爬取工具</span>
                <br>
                数据来源：抖音热榜 | 更新时间：{now_str}
            </div>
        </div>
    </div>
    
    <script>
        function saveAsImage() {{
            const container = document.querySelector('.container');
            html2canvas(container, {{
                scale: 2,
                useCORS: true,
                backgroundColor: '#fafafa'
            }}).then(canvas => {{
                const link = document.createElement('a');
                link.download = '抖音热点榜_' + new Date().toISOString().slice(0,10) + '.png';
                link.href = canvas.toDataURL('image/png');
                link.click();
            }});
        }}
    </script>
</body>
</html>
"""

        try:
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"抖音热榜HTML已生成: {html_file}")
            return str(html_file)
        except Exception as e:
            print(f"生成HTML报告失败: {e}")
            # 降级到当前目录
            fallback_file = output_dir / f"douyin_hot_{date_str}.html"
            with open(fallback_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print(f"已保存到降级路径: {fallback_file}")
            return str(fallback_file)


def get_douyin_hot(proxy_url: Optional[str] = None) -> Optional[Dict]:
    """获取抖音热榜的便捷函数
    
    Args:
        proxy_url: 代理URL，可选
        
    Returns:
        抖音热榜数据字典，失败返回 None
    """
    fetcher = DouyinHotFetcher(proxy_url=proxy_url)
    return fetcher.fetch_douyin_hot()


def save_douyin_hot(douyin_data: Dict, output_dir: Optional[str] = None) -> str:
    """保存抖音热榜的便捷函数
    
    Args:
        douyin_data: 抖音热榜数据
        output_dir: 输出目录，可选
        
    Returns:
        保存的文件路径
    """
    fetcher = DouyinHotFetcher()
    return fetcher.save_to_txt(douyin_data, output_dir=output_dir)


def generate_douyin_report(douyin_data: Dict, output_dir: Optional[str] = None) -> str:
    """生成抖音热榜报告的便捷函数
    
    Args:
        douyin_data: 抖音热榜数据
        output_dir: 输出目录，可选
        
    Returns:
        生成的HTML文件路径
    """
    fetcher = DouyinHotFetcher()
    return fetcher.generate_html_report(douyin_data, output_dir=output_dir)


def main():
    """主函数"""
    print("抖音热榜爬取工具")
    print("=" * 50)

    fetcher = DouyinHotFetcher()

    print("正在获取抖音热榜...")
    douyin_data = fetcher.fetch_douyin_hot()

    if douyin_data:
        print(f"成功获取 {len(douyin_data)} 条抖音热榜")

        print("正在保存到文本文件...")
        txt_file = fetcher.save_to_txt(douyin_data)

        print("正在生成HTML报告...")
        html_file = fetcher.generate_html_report(douyin_data)

        print("\n" + "=" * 50)
        print("抖音热榜爬取完成！")
        print(f"文本文件: {txt_file}")
        print(f"HTML报告: {html_file}")
    else:
        print("抖音热榜获取失败")


if __name__ == "__main__":
    main()