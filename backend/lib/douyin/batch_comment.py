"""
批量评论爬取器

支持批量爬取多个抖音视频的评论
"""

import csv
import datetime
import os
import re
from typing import Any, Dict, List, Optional

from loguru import logger

from .client import DouyinClient
from .request import Request


class DouyinBatchCommentFetcher:
    """批量评论爬取器"""

    def __init__(self, cookie: str, user_agent: Optional[str] = None):
        """
        初始化爬取器

        Args:
            cookie: 抖音 cookie
            user_agent: User-Agent
        """
        self.request = Request(cookie=cookie, UA=user_agent or "")
        self.client = DouyinClient(self.request)

    def extract_aweme_id(self, input_str: str) -> Optional[str]:
        """
        从各种输入中提取 aweme_id
        
        支持的格式：
        - 纯 aweme_id: 7234567890123456789
        - 视频 URL: https://www.douyin.com/video/7234567890123456789
        - 分享链接：https://v.douyin.com/xxxxx/
        - 短链接：https://v.iesdouyin.com/s/xxxxx

        Args:
            input_str: 输入字符串（ID 或 URL）

        Returns:
            Optional[str]: aweme_id
        """
        input_str = input_str.strip()
        
        # 检查是否是纯数字 ID
        if input_str.isdigit():
            return input_str
        
        # 从 URL 中提取
        patterns = [
            r'/video/(\d+)',              # https://www.douyin.com/video/1234567890
            r'aweme_id=(\d+)',            # https://v.douyin.com/?aweme_id=1234567890
            r'v\.douyin\.com/([^/?]+)',   # https://v.douyin.com/xxxxx/
            r'iesdouyin\.com/s/([^/?]+)', # https://v.iesdouyin.com/s/xxxxx
        ]
        
        for pattern in patterns:
            match = re.search(pattern, input_str)
            if match:
                # 对于短链接，需要进一步处理
                short_code = match.group(1)
                if short_code.isdigit():
                    return short_code
                # 短链接需要重定向获取真实 ID（这里简化处理）
                logger.warning(f"短链接需要重定向获取：{input_str}")
                return None
        
        logger.warning(f"无法提取 aweme_id: {input_str}")
        return None

    def crawl_video_comments(
        self,
        aweme_id: str,
        max_count: int = 100,
        save_to_csv: bool = False,
        output_dir: str = "downloads",
    ) -> List[Dict[str, Any]]:
        """
        爬取单个视频的评论

        Args:
            aweme_id: 视频 ID
            max_count: 最多爬取评论数量
            save_to_csv: 是否保存到 CSV
            output_dir: 输出目录

        Returns:
            List[Dict]: 评论列表
        """
        all_comments = []
        cursor = 0
        count = 20  # 每次请求的评论数量

        try:
            while True:
                # 获取评论列表
                result = self.client.fetch_comment_list(aweme_id, cursor=cursor, count=count)
                comments = result.get("comments", [])
                
                if not comments:
                    break

                # 处理评论
                for comment in comments:
                    normalized = self._normalize_comment(comment)
                    all_comments.append(normalized)

                    # 检查是否达到最大数量
                    if max_count > 0 and len(all_comments) >= max_count:
                        break

                # 检查是否有更多评论
                has_more = result.get("has_more", 0)
                if not has_more:
                    break

                # 更新 cursor
                cursor = result.get("cursor", cursor + count)

                # 检查是否达到最大数量
                if max_count > 0 and len(all_comments) >= max_count:
                    break

                # 添加延迟，避免请求过快
                import time
                time.sleep(0.5)

            logger.info(f"爬取到 {len(all_comments)} 条评论")

            # 保存到 CSV
            if save_to_csv and all_comments:
                self._save_to_csv(all_comments, aweme_id, output_dir)

            return all_comments
        except Exception as e:
            logger.error(f"爬取评论失败：{e}")
            return []

    def crawl_batch(
        self,
        video_inputs: List[str],
        comments_per_video: int = 100,
        save_to_csv: bool = True,
        output_dir: str = "downloads",
    ) -> Dict[str, Any]:
        """
        批量爬取多个视频的评论

        Args:
            video_inputs: 视频 ID 或 URL 列表
            comments_per_video: 每个视频爬取多少条评论
            save_to_csv: 是否保存到 CSV
            output_dir: 输出目录

        Returns:
            Dict: 爬取结果
        """
        result = {
            "success": True,
            "videos": [],
            "total_comments": 0,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        try:
            for idx, video_input in enumerate(video_inputs, 1):
                logger.info(f"[{idx}/{len(video_inputs)}] 处理：{video_input}")
                
                # 提取 aweme_id
                aweme_id = self.extract_aweme_id(video_input)
                
                if not aweme_id:
                    logger.warning(f"无法提取视频 ID: {video_input}，跳过")
                    result["videos"].append({
                        "input": video_input,
                        "success": False,
                        "error": "无法提取视频 ID",
                        "comments_count": 0,
                    })
                    continue

                # 爬取评论
                comments = self.crawl_video_comments(
                    aweme_id=aweme_id,
                    max_count=comments_per_video,
                    save_to_csv=save_to_csv,
                    output_dir=output_dir,
                )

                result["videos"].append({
                    "input": video_input,
                    "aweme_id": aweme_id,
                    "success": True,
                    "comments_count": len(comments),
                })
                result["total_comments"] += len(comments)

                # 添加延迟，避免请求过快
                import time
                time.sleep(1.5)

            logger.info(f"批量爬取完成，共 {result['total_comments']} 条评论")
            return result
        except Exception as e:
            logger.error(f"批量爬取失败：{e}", exc_info=True)
            result["success"] = False
            result["error"] = str(e)
            return result

    def _normalize_comment(self, comment: Dict[str, Any]) -> Dict[str, Any]:
        """标准化评论数据"""
        user = comment.get("user", {})
        create_time = comment.get("create_time", 0)
        
        try:
            dt = datetime.datetime.fromtimestamp(create_time)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            time_str = str(create_time)

        return {
            "id": comment.get("cid") or str(comment.get("id", "")),
            "aweme_id": comment.get("aweme_id", ""),
            "nickname": user.get("nickname", "未知用户"),
            "text": (comment.get("text") or "").strip(),
            "create_time": time_str,
            "digg_count": comment.get("digg_count", 0),
            "reply_count": comment.get("reply_comment_total", 0),
            "ip_label": comment.get("ip_label", ""),
            "is_top": bool(comment.get("stick_position", 0)),
            "is_hot": bool(comment.get("is_hot_comment", 0)),
        }

    def _save_to_csv(
        self,
        comments: List[Dict[str, Any]],
        aweme_id: str,
        output_dir: str,
    ):
        """保存评论到 CSV"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comments_{aweme_id}_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)

            # 写入 CSV
            with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
                if comments:
                    fieldnames = list(comments[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(comments)

            logger.info(f"评论已保存到：{filepath}")
        except Exception as e:
            logger.error(f"保存 CSV 失败：{e}")
