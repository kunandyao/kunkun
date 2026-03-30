#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音热榜评论定时爬取器

功能：
- 每 2 小时自动爬取热榜视频评论
- 自动保存评论数据到 CSV
- 自动记录爬取日志
- 支持后台运行
"""

import datetime
import os
import sys
import time
from pathlib import Path
from typing import Optional

from backend.lib.douyin.hot_comment import DouyinHotCommentFetcher
from backend.lib.douyin.hot import DouyinHotFetcher
from backend.settings import settings
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    "logs/hot_comment_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO",
    rotation="1 day",
    retention="7 days",
    encoding="utf-8"
)
logger.add(
    sys.stdout,
    format="{time:HH:mm:ss} | {level} | {message}",
    level="INFO"
)


class HotCommentScheduler:
    """热榜评论定时爬取器"""

    def __init__(
        self,
        interval_hours: int = 2,
        video_count: int = 10,
        comments_per_video: int = 100,
        save_to_csv: bool = True,
        output_dir: Optional[str] = None,
    ):
        """
        初始化定时爬取器

        Args:
            interval_hours: 爬取间隔（小时），默认 2 小时
            video_count: 每次爬取多少个热榜视频
            comments_per_video: 每个视频爬取多少条评论
            save_to_csv: 是否保存到 CSV
            output_dir: 输出目录，默认 downloads/hot_comments
        """
        self.interval_hours = interval_hours
        self.video_count = video_count
        self.comments_per_video = comments_per_video
        self.save_to_csv = save_to_csv
        self.output_dir = output_dir or os.path.join("downloads", "hot_comments")
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 获取配置
        cookie = settings.get("cookie")
        user_agent = settings.get("userAgent")
        
        if not cookie:
            raise ValueError("请先在设置中配置 Cookie")
        
        # 创建爬取器
        self.fetcher = DouyinHotCommentFetcher(cookie=cookie, user_agent=user_agent)
        
        logger.info(f"定时爬取器已初始化")
        logger.info(f"  爬取间隔：{interval_hours} 小时")
        logger.info(f"  热榜视频数：{video_count}")
        logger.info(f"  每视频评论数：{comments_per_video}")
        logger.info(f"  输出目录：{self.output_dir}")

    def run_once(self) -> dict:
        """
        执行一次爬取任务

        Returns:
            dict: 爬取结果
        """
        logger.info("=" * 60)
        logger.info(f"开始执行爬取任务：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 爬取热榜视频评论
            result = self.fetcher.crawl_hot_videos_comments(
                video_count=self.video_count,
                comments_per_video=self.comments_per_video,
                save_to_csv=self.save_to_csv,
                output_dir=self.output_dir,
            )
            
            if result.get("success"):
                logger.info(f"✓ 爬取成功")
                logger.info(f"  总评论数：{result.get('total_comments', 0)}")
                logger.info(f"  成功视频数：{sum(1 for v in result.get('videos', []) if v.get('success'))}")
                logger.info(f"  失败视频数：{sum(1 for v in result.get('videos', []) if not v.get('success'))}")
                
                # 保存爬取结果摘要
                self._save_summary(result)
            else:
                logger.error(f"✗ 爬取失败：{result.get('error', '未知错误')}")
            
            return result
            
        except Exception as e:
            logger.error(f"✗ 爬取异常：{e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _save_summary(self, result: dict):
        """保存爬取结果摘要"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_file = os.path.join(self.output_dir, f"summary_{timestamp}.txt")
            
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(f"爬取时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总评论数：{result.get('total_comments', 0)}\n")
                f.write(f"成功视频数：{sum(1 for v in result.get('videos', []) if v.get('success'))}\n")
                f.write(f"失败视频数：{sum(1 for v in result.get('videos', []) if not v.get('success'))}\n\n")
                
                f.write("视频详情:\n")
                for idx, video in enumerate(result.get("videos", []), 1):
                    status = "✓" if video.get("success") else "✗"
                    title = video.get("title", f"视频{idx}")
                    aweme_id = video.get("aweme_id", "N/A")
                    comments_count = video.get("comments_count", 0)
                    error = video.get("error", "")
                    
                    f.write(f"{idx}. {status} {title}\n")
                    f.write(f"   视频 ID: {aweme_id}\n")
                    f.write(f"   评论数：{comments_count}\n")
                    if error:
                        f.write(f"   错误：{error}\n")
                    f.write("\n")
            
            logger.info(f"  摘要已保存：{summary_file}")
            
        except Exception as e:
            logger.warning(f"保存摘要失败：{e}")

    def run_forever(self):
        """持续运行，定时执行爬取任务"""
        logger.info("=" * 60)
        logger.info("定时爬取器已启动")
        logger.info(f"下次爬取时间：{self._get_next_run_time()}")
        logger.info("按 Ctrl+C 停止")
        
        next_run = datetime.datetime.now()
        
        while True:
            try:
                now = datetime.datetime.now()
                
                # 检查是否到达爬取时间
                if now >= next_run:
                    # 执行爬取任务
                    self.run_once()
                    
                    # 计算下次爬取时间
                    next_run = now + datetime.timedelta(hours=self.interval_hours)
                    logger.info("=" * 60)
                    logger.info(f"下次爬取时间：{next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 等待 1 分钟
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("\n收到停止信号，正在退出...")
                break
            except Exception as e:
                logger.error(f"运行异常：{e}", exc_info=True)
                time.sleep(60)

    def _get_next_run_time(self) -> str:
        """获取下次爬取时间"""
        next_run = datetime.datetime.now() + datetime.timedelta(hours=self.interval_hours)
        return next_run.strftime("%Y-%m-%d %H:%M:%S")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="抖音热榜评论定时爬取器")
    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="爬取间隔（小时），默认 2 小时"
    )
    parser.add_argument(
        "--video-count",
        type=int,
        default=10,
        help="每次爬取多少个热榜视频，默认 10 个"
    )
    parser.add_argument(
        "--comments-per-video",
        type=int,
        default=100,
        help="每个视频爬取多少条评论，默认 100 条"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存到 CSV"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="输出目录"
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="只运行一次，不定时执行"
    )
    
    args = parser.parse_args()
    
    try:
        # 创建定时爬取器
        scheduler = HotCommentScheduler(
            interval_hours=args.interval,
            video_count=args.video_count,
            comments_per_video=args.comments_per_video,
            save_to_csv=not args.no_save,
            output_dir=args.output_dir,
        )
        
        if args.run_once:
            # 只运行一次
            scheduler.run_once()
        else:
            # 持续运行
            scheduler.run_forever()
            
    except Exception as e:
        logger.error(f"启动失败：{e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
