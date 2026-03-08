"""
浏览器自动化评论爬取模块

基于 DrissionPage 的浏览器自动化方案，作为 API 爬取的备用方案
当 API 方式受限时，使用此模块模拟浏览器行为获取评论
"""

import csv
import datetime
import os
import re
import threading
import time
from typing import Dict, List, Optional, Set

from loguru import logger


class BrowserCommentCrawler:
    """浏览器自动化评论爬虫"""

    def __init__(
        self,
        video_url: Optional[str] = None,
        aweme_id: Optional[str] = None,
        max_comments: Optional[int] = None,
        use_normal_mode: bool = True,
    ):
        """
        初始化爬虫

        Args:
            video_url: 视频URL
            aweme_id: 作品ID
            max_comments: 最大爬取评论数，None表示不限制
            use_normal_mode: 是否使用正常模式（带缓存）
        """
        self.video_url = video_url
        self.aweme_id = aweme_id or self._extract_video_id(video_url)
        self.max_comments = max_comments
        self.use_normal_mode = use_normal_mode
        self.comments: List[Dict] = []
        self.comment_ids: Set[str] = set()
        self.driver = None
        self.output_file = None

    def _extract_video_id(self, url: Optional[str]) -> str:
        """从URL中提取视频ID"""
        if not url:
            raise ValueError("需要提供视频URL或视频ID")

        url = url.replace("：", ":").strip()
        url_match = re.search(r'https?://[^\s]+', url)
        if url_match:
            url = url_match.group(0)

        if not url.startswith("http"):
            url = "https://" + url.lstrip(":/")

        # 处理短链接
        if "v.douyin.com" in url:
            parts = url.split("/")
            for part in reversed(parts):
                if part.strip():
                    return part.strip()

        # 处理标准链接
        try:
            parts = url.split("/")
            for part in parts:
                if part.strip().isdigit():
                    return part.strip()
            return parts[-1].split("?")[0]
        except:
            return url.split("/")[-1].split("?")[0]

    def _init_driver(self):
        """初始化浏览器驱动"""
        try:
            from DrissionPage import ChromiumPage

            if self.use_normal_mode:
                self.driver = ChromiumPage()
                logger.info("已启用正常浏览模式")
            else:
                try:
                    self.driver = ChromiumPage(chromium_options={"headless": False, "incognito": True})
                    logger.info("使用无痕模式")
                except:
                    self.driver = ChromiumPage()
                    logger.info("无法使用无痕模式，回退到默认模式")
        except ImportError:
            raise ImportError("请先安装 DrissionPage: pip install DrissionPage")
        except Exception as e:
            logger.error(f"初始化浏览器失败: {e}")
            raise

    def _scroll_page(self, method: int = 1):
        """执行页面滚动"""
        try:
            if method == 1:
                # 滚动到底部
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            elif method == 2:
                # 先向下滚动，再到底部
                self.driver.run_js("window.scrollBy(0, 300);")
                time.sleep(0.3)
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            elif method == 3:
                # 波浪式滚动
                self.driver.run_js("window.scrollBy(0, 300);")
                time.sleep(0.3)
                self.driver.run_js("window.scrollBy(0, -50);")
                time.sleep(0.3)
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            else:
                self.driver.run_js("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"滚动失败: {e}")

    def _try_expand_replies(self):
        """尝试展开更多回复"""
        try:
            # 查找"查看回复"按钮
            more_btns = self.driver.find_elements(
                xpath='//span[contains(text(), "查看") and contains(text(), "回复")]'
            )
            for btn in more_btns[:3]:
                try:
                    self.driver.run_js("arguments[0].scrollIntoView();", btn)
                    time.sleep(0.3)
                    self.driver.run_js("arguments[0].click();", btn)
                    time.sleep(0.5)
                except:
                    continue
        except Exception as e:
            logger.debug(f"展开回复失败: {e}")

    def _parse_comment(self, comment_element) -> Optional[Dict]:
        """解析单个评论元素"""
        try:
            # 尝试多种选择器获取评论信息
            comment_id = comment_element.attr("data-e2e") or comment_element.attr("data-cid") or str(int(time.time() * 1000))

            # 获取用户昵称
            nickname = ""
            try:
                nickname_elem = comment_element.ele('xpath:.//a[contains(@class, "user-name") or contains(@class, "nickname")]', timeout=1)
                nickname = nickname_elem.text
            except:
                try:
                    nickname_elem = comment_element.ele('css:.lC6iS6P0, .avatar img', timeout=1)
                    nickname = nickname_elem.attr("alt") or ""
                except:
                    nickname = "未知用户"

            # 获取评论内容
            text = ""
            try:
                text_elem = comment_element.ele('xpath:.//span[contains(@class, "comment-content") or contains(@class, "content")]', timeout=1)
                text = text_elem.text
            except:
                try:
                    text_elem = comment_element.ele('css:.VD5Aa1A1, span[class*="content"]', timeout=1)
                    text = text_elem.text
                except:
                    text = ""

            # 获取点赞数
            digg_count = 0
            try:
                digg_elem = comment_element.ele('xpath:.//span[contains(@class, "like-count") or contains(@class, "digg")]', timeout=1)
                digg_text = digg_elem.text
                digg_count = self._parse_count(digg_text)
            except:
                pass

            # 获取时间
            create_time = ""
            try:
                time_elem = comment_element.ele('xpath:.//span[contains(@class, "time") or contains(@class, "date")]', timeout=1)
                create_time = time_elem.text
            except:
                create_time = datetime.datetime.now().strftime("%Y-%m-%d")

            # 获取IP属地
            ip_label = ""
            try:
                ip_elem = comment_element.ele('xpath:.//span[contains(text(), "IP")]', timeout=1)
                ip_label = ip_elem.text.replace("IP属地：", "").replace("IP: ", "")
            except:
                pass

            return {
                "id": comment_id,
                "nickname": nickname.strip() or "未知用户",
                "text": text.strip(),
                "create_time": create_time,
                "digg_count": digg_count,
                "reply_count": 0,
                "ip_label": ip_label,
                "is_top": False,
                "is_hot": False,
            }
        except Exception as e:
            logger.debug(f"解析评论失败: {e}")
            return None

    def _parse_count(self, text: str) -> int:
        """解析数量文本"""
        if not text:
            return 0
        text = text.strip()
        try:
            if "万" in text:
                num = float(text.replace("万", ""))
                return int(num * 10000)
            return int(text)
        except:
            return 0

    def _extract_comments_from_page(self) -> List[Dict]:
        """从页面提取所有评论"""
        comments = []
        try:
            # 尝试多种选择器查找评论元素
            selectors = [
                '//div[contains(@class, "comment-item")]',
                '//div[@data-e2e="comment-item"]',
                '//div[contains(@class, "CommentItem")]',
                '//div[contains(@class, "comment-mainContent")]',
            ]

            comment_elements = []
            for selector in selectors:
                try:
                    comment_elements = self.driver.find_elements(xpath=selector)
                    if comment_elements:
                        break
                except:
                    continue

            for elem in comment_elements:
                comment = self._parse_comment(elem)
                if comment and comment["id"] not in self.comment_ids:
                    self.comment_ids.add(comment["id"])
                    comments.append(comment)

        except Exception as e:
            logger.error(f"提取评论失败: {e}")

        return comments

    def crawl(self) -> Dict:
        """
        执行爬取

        Returns:
            Dict: 包含 comments, total, output_file
        """
        logger.info(f"开始浏览器自动化爬取视频 {self.aweme_id} 的评论")

        # 初始化浏览器
        self._init_driver()

        try:
            # 设置输出文件
            comments_dir = os.path.join(os.getcwd(), "downloads", "comments")
            os.makedirs(comments_dir, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_file = os.path.join(comments_dir, f"comments_browser_{self.aweme_id}_{ts}.csv")

            # 访问视频页面
            if self.video_url:
                url = self.video_url
            else:
                url = f"https://www.douyin.com/video/{self.aweme_id}"

            logger.info(f"访问页面: {url}")
            self.driver.get(url)
            time.sleep(3)

            # 等待评论区加载
            time.sleep(2)

            # 滚动策略
            scroll_methods = [1, 2, 3, 1, 2, 1]
            method_index = 0
            no_new_count = 0
            max_no_new = 5

            while no_new_count < max_no_new:
                # 提取当前页面评论
                new_comments = self._extract_comments_from_page()

                if new_comments:
                    self.comments.extend(new_comments)
                    no_new_count = 0
                    logger.info(f"已获取 {len(self.comments)} 条评论")
                else:
                    no_new_count += 1

                # 检查是否达到最大数量
                if self.max_comments and len(self.comments) >= self.max_comments:
                    self.comments = self.comments[: self.max_comments]
                    break

                # 尝试展开回复
                self._try_expand_replies()

                # 滚动页面
                self._scroll_page(scroll_methods[method_index % len(scroll_methods)])
                method_index += 1

                time.sleep(1)

            # 保存到CSV
            self._save_to_csv()

            return {
                "comments": self.comments,
                "total": len(self.comments),
                "output_file": self.output_file,
            }

        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

    def _save_to_csv(self):
        """保存评论到CSV"""
        if not self.comments:
            return

        fieldnames = [
            "id", "nickname", "text", "create_time", "digg_count",
            "reply_count", "ip_label", "is_top", "is_hot",
        ]

        try:
            with open(self.output_file, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for comment in self.comments:
                    writer.writerow({k: comment.get(k, "") for k in fieldnames})
            logger.info(f"评论已保存到: {self.output_file}")
        except Exception as e:
            logger.error(f"保存CSV失败: {e}")


def crawl_comments_browser(
    aweme_id: Optional[str] = None,
    video_url: Optional[str] = None,
    max_comments: Optional[int] = None,
) -> Dict:
    """
    便捷函数：使用浏览器自动化爬取评论

    Args:
        aweme_id: 作品ID
        video_url: 视频URL
        max_comments: 最大评论数

    Returns:
        Dict: 爬取结果
    """
    crawler = BrowserCommentCrawler(
        aweme_id=aweme_id,
        video_url=video_url,
        max_comments=max_comments,
    )
    return crawler.crawl()
