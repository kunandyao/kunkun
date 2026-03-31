"""
抖音热榜评论爬取器

从抖音热榜获取视频 ID，然后爬取每个视频的评论数据
"""

import csv
import datetime
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .client import DouyinClient
from .request import Request
from .target import TargetHandler


class DouyinHotCommentFetcher:
    """抖音热榜评论爬取器"""

    def __init__(self, cookie: str, user_agent: Optional[str] = None):
        """
        初始化爬取器

        Args:
            cookie: 抖音 cookie
            user_agent: User-Agent
        """
        self.cookie = cookie
        self.user_agent = user_agent or ""
        self.request = Request(cookie=cookie, UA=self.user_agent)
        self.client = DouyinClient(self.request)

    def get_hot_videos(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        获取热榜视频列表（直接使用 uapis.cn 接口）

        Args:
            count: 获取热榜视频数量

        Returns:
            List[Dict]: 热榜视频信息列表
        """
        try:
            import requests
            
            # 直接从 uapis.cn 获取完整的热榜数据（包含热值、封面、video_count、sentence_id）
            uapi_url = "https://uapis.cn/api/v1/misc/hotboard?type=douyin"
            logger.info(f"获取 uapis.cn 热榜数据：{uapi_url}")
            uapi_response = requests.get(uapi_url, timeout=30)
            uapi_data = uapi_response.json()
            uapi_list = uapi_data.get("list", [])
            
            logger.info(f"uapis.cn 获取到 {len(uapi_list)} 条热榜数据")
            
            # 直接转换数据格式
            hot_videos = []
            for item in uapi_list[:count]:
                sentence_id = item.get("extra", {}).get("sentence_id", "")
                title = item.get("title", "")
                
                if not sentence_id or not title:
                    continue
                
                # 构建标准的热榜链接
                url = f"https://www.douyin.com/hot/{sentence_id}"
                
                hot_videos.append({
                    "title": title,
                    "hot_value": str(item.get("hot_value", "0")),
                    "cover": item.get("extra", {}).get("cover", ""),
                    "video_count": item.get("extra", {}).get("video_count", 0),
                    "sentence_id": sentence_id,
                    "rank": item.get("index", 0),
                    "url": url,
                    "mobile_url": url,
                    "hot_id": sentence_id,
                    # 不预先获取 aweme_id，等爬取评论时再获取
                })
            
            logger.info(f"获取到 {len(hot_videos)} 个热榜视频")
            for video in hot_videos[:3]:
                logger.info(f"  - {video['rank']}. {video['title']} (热度：{video.get('hot_value', 'N/A')})")
            # 打印完整的视频数据用于调试
            for idx, video in enumerate(hot_videos):
                logger.info(f"视频 {idx+1} 完整数据：{video}")
            
            return hot_videos
        except Exception as e:
            logger.error(f"获取热榜视频失败：{e}", exc_info=True)
            return []
    
    def _fetch_uapi_hot_data(self) -> dict:
        """从 uapis.cn 获取热值、封面、video_count（使用 sentence_id 精准匹配）
        
        Returns:
            热值映射，key 为 sentence_id，value 为 {hot_value, cover, video_count}
        """
        uapi_url = "https://uapis.cn/api/v1/misc/hotboard?type=douyin"
        
        hot_map = {}  # sentence_id -> {hot_value, cover, video_count}
        
        try:
            response = requests.get(uapi_url, timeout=30)
            data = response.json()
            
            if data and "list" in data:
                for item in data["list"]:
                    sentence_id = item.get("extra", {}).get("sentence_id", "")
                    if sentence_id:
                        hot_map[sentence_id] = {
                            "hot_value": str(item.get("hot_value", "0")),
                            "cover": item.get("extra", {}).get("cover", ""),
                            "video_count": item.get("extra", {}).get("video_count", 0),
                        }
                
                logger.info(f"从 uapis.cn 获取到 {len(hot_map)} 条热榜数据（按 sentence_id）")
        except Exception as e:
            logger.warning(f"获取 uapis 热值失败：{e}")
        
        return hot_map
    
    def _fetch_douyin_hot_values(self) -> tuple:
        """从抖音原生接口获取热值和事件时间（使用 sentence_id 精准匹配）
        
        Returns:
            (热值映射，事件时间映射)，key 为 sentence_id
        """
        from datetime import datetime
        
        # 获取 cookie
        try:
            cookie_response = requests.get("https://login.douyin.com/", timeout=10)
            cookies = cookie_response.headers.getSetCookie()
            cookie_str = "; ".join(cookies)
        except Exception as e:
            logger.warning(f"获取抖音 cookie 失败：{e}")
            cookie_str = ""
        
        douyin_url = "https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Cookie": cookie_str,
        }
        
        hot_map = {}  # sentence_id -> {hot_value, event_time}
        
        try:
            response = requests.get(douyin_url, headers=headers, timeout=30)
            data = response.json()
            
            if data and "data" in data and "word_list" in data["data"]:
                for item in data["data"]["word_list"]:
                    sentence_id = item.get("sentence_id", "")
                    word = item.get("word", "")
                    hot_value = item.get("hot_value", "0")
                    event_time = item.get("event_time", "")
                    
                    if sentence_id:
                        hot_map[sentence_id] = {
                            "hot_value": str(hot_value),
                            "event_time": event_time if event_time else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                
                logger.info(f"从抖音原生接口获取到 {len(hot_map)} 条热榜数据（按 sentence_id）")
        except Exception as e:
            logger.warning(f"获取抖音热值失败：{e}")
        
        return hot_map, {}

    def get_video_from_hot_url(self, hot_url: str, hot_title: str) -> Optional[str]:
        """
        从热榜 URL 获取相关视频 ID
        
        方案：访问热榜话题页面，提取第一个视频的 URL
        
        Args:
            hot_url: 热榜话题 URL（如 https://www.douyin.com/hot/2444287）
            hot_title: 热榜标题

        Returns:
            Optional[str]: 视频 aweme_id
        """
        try:
            # 访问热榜话题页面
            logger.info(f"访问热榜话题页面：{hot_url}")
            text = self.request.getHTML(hot_url)
            
            if not text:
                logger.warning(f"热榜话题页面内容为空：{hot_url}")
                return None
            
            # 从页面中提取第一个视频 URL
            # 抖音话题页面的视频 URL 格式：/video/7123456789012345678
            import re
            
            # 匹配视频 URL 模式
            video_url_pattern = r'/video/(\d{19})'
            matches = re.findall(video_url_pattern, text)
            
            if matches:
                # 取第一个视频 ID
                aweme_id = matches[0]
                logger.info(f"从热榜话题页面提取到视频 ID: {aweme_id}")
                return aweme_id
            
            # 如果没有找到，尝试其他模式
            # 可能是 note 类型
            note_url_pattern = r'/note/(\d{19})'
            note_matches = re.findall(note_url_pattern, text)
            
            if note_matches:
                aweme_id = note_matches[0]
                logger.info(f"从热榜话题页面提取到笔记 ID: {aweme_id}")
                return aweme_id
            
            logger.warning(f"未从热榜话题页面找到视频：{hot_title}")
            return None
        except Exception as e:
            logger.error(f"从热榜 URL 获取视频 ID 失败：{e}", exc_info=True)
            return None

    def extract_aweme_id_from_url(self, url: str) -> Optional[str]:
        """
        从 URL 中提取 aweme_id

        Args:
            url: 抖音视频 URL

        Returns:
            Optional[str]: aweme_id
        """
        if not url:
            return None
            
        # 匹配各种抖音 URL 格式
        patterns = [
            r'/video/(\d+)',              # https://www.douyin.com/video/1234567890
            r'aweme_id=(\d+)',            # https://v.douyin.com/?aweme_id=1234567890
            r'douyin\.com/s/([^?#/]+)',   # https://www.douyin.com/s/xxxxx
            r'iesdouyin\.com/s/([^?#/]+)', # https://v.iesdouyin.com/s/xxxxx
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                aweme_id = match.group(1)
                logger.debug(f"从 URL 提取 aweme_id: {aweme_id} (URL: {url})")
                return aweme_id
        
        logger.warning(f"无法从 URL 提取 aweme_id: {url}")
        return None

    def crawl_video_comments(
        self,
        aweme_id: str,
        max_count: int = 100,
        save_to_csv: bool = False,
        save_to_db: bool = False,
        output_dir: str = "downloads",
        video_title: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        爬取单个视频的评论

        Args:
            aweme_id: 视频 ID
            max_count: 最多爬取评论数量
            save_to_csv: 是否保存到 CSV
            save_to_db: 是否保存到数据库
            output_dir: 输出目录

        Returns:
            Tuple[List[Dict], Optional[str]]: (评论列表, CSV文件路径)
        """
        all_comments = []
        cursor = 0
        count = 20  # 每次请求的评论数量
        csv_file_path = None

        try:
            logger.info(f"开始爬取视频 {aweme_id} 的评论")
            while True:
                # 获取评论列表
                result = self.client.fetch_comment_list(aweme_id, cursor=cursor, count=count)
                logger.debug(f"评论 API 返回结果：{result}")
                comments = result.get("comments", [])
                
                if not comments:
                    logger.warning(f"未获取到评论，aweme_id: {aweme_id}, cursor: {cursor}")
                    break

                # 处理评论
                for comment in comments:
                    normalized = self._normalize_comment(comment)
                    normalized['aweme_id'] = aweme_id  # 添加视频 ID
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
                csv_file_path = self._save_to_csv(all_comments, aweme_id, output_dir, video_title)

            # 保存到数据库
            if save_to_db and all_comments:
                self.save_comments_to_db(all_comments)

            return all_comments, csv_file_path
        except Exception as e:
            logger.error(f"爬取评论失败：{e}")
            return [], None

    def save_comments_to_db(self, comments: List[Dict[str, Any]]):
        """
        保存评论数据到数据库
        
        Args:
            comments: 评论列表
        """
        try:
            from backend.lib.database import db_manager
            from backend.lib.database.models import CommentModel
            
            saved_count = 0
            logger.info(f"开始保存 {len(comments)} 条评论到数据库")
            
            for comment in comments:
                try:
                    sql, params = CommentModel.insert_sql(comment)
                    
                    with db_manager.get_cursor() as cursor:
                        cursor.execute(sql, params)
                    saved_count += 1
                except Exception as e:
                    logger.debug(f"保存单条评论失败 (ID: {comment.get('cid')}): {e}")
                    continue
            
            logger.success(f"已将 {saved_count}/{len(comments)} 条评论保存到数据库")
            
        except Exception as e:
            logger.error(f"保存评论到数据库失败：{e}", exc_info=True)

    def search_video_by_keyword(self, keyword: str, count: int = 1) -> List[str]:
        """
        通过关键词搜索视频
        
        Args:
            keyword: 搜索关键词
            count: 返回结果数量

        Returns:
            List[str]: aweme_id 列表
        """
        try:
            from backend.lib.douyin.types import APIEndpoint
            import json
            from urllib.parse import quote
            
            # 构建 filter_selected JSON
            filter_selected = json.dumps({
                "sort_type": "0",  # 0 综合 1 最热 2 最新
                "publish_time": "0",
                "content_type": "1",  # 1=视频
                "filter_duration": "0",
                "search_range": "0",
            }, ensure_ascii=False)
            
            # 构建参数 - 使用正确的编码
            params = {
                "search_channel": "aweme_general",
                "enable_history": 1,
                "filter_selected": filter_selected,
                "keyword": keyword,  # 不使用 quote，让 requests 自动处理
                "search_source": "tab_search",
                "query_correct_type": 1,
                "is_filter_search": 1,
                "from_group_id": "",
                "disable_rs": 0,
                "offset": 0,
                "count": count * 2,  # 多请求一些，然后过滤
                "need_filter_settings": 0,
                "list_type": "multi",
            }
            
            url = APIEndpoint.SEARCH_GENERAL
            
            logger.info(f"搜索关键词：{keyword}")
            # 直接调用 API
            resp = self.request.getJSON(url, params)
            
            # 调试：打印响应结构
            logger.debug(f"搜索响应 keys: {list(resp.keys()) if resp else 'None'}")
            
            # 解析搜索结果
            video_ids = []
            if resp and resp.get("status_code") == 0:
                search_data = resp.get("data", {})
                
                # 打印 data 的完整结构用于调试
                if isinstance(search_data, dict):
                    logger.debug(f"data 字段：{list(search_data.keys())}")
                
                # data 可能是列表或字典
                if isinstance(search_data, list):
                    result_list = search_data
                else:
                    # 尝试多个可能的字段
                    result_list = search_data.get("result_list") or search_data.get("data") or search_data.get("list") or []
                
                logger.debug(f"result_list 长度：{len(result_list) if isinstance(result_list, list) else 'N/A'}")
                
                # 遍历结果
                for idx, item in enumerate(result_list[:10]):  # 只检查前 10 个
                    if isinstance(item, dict):
                        item_type = item.get("type")
                        logger.debug(f"item[{idx}] type={item_type}")
                        
                        if item_type == 1:  # 1 表示视频
                            aweme_info = item.get("aweme_info", {})
                            aweme_id = aweme_info.get("aweme_id")
                            if aweme_id:
                                video_ids.append(aweme_id)
                                logger.info(f"找到视频：{aweme_id}")
                                if len(video_ids) >= count:
                                    break
            
            logger.info(f"搜索到 {len(video_ids)} 个视频")
            return video_ids
            
        except Exception as e:
            logger.error(f"搜索视频失败：{e}", exc_info=True)
            return []

    def extract_aweme_id_from_url(self, video_url: str) -> Optional[str]:
        """
        从抖音视频 URL 中提取 aweme_id
        
        使用项目已有的 TargetHandler 来识别 URL 并提取 ID
        支持的 URL 格式：
        - https://www.douyin.com/video/7123456789012345678
        - https://v.douyin.com/xxxxxx
        - 复制的分享链接（含标题和 URL）

        Args:
            video_url: 抖音视频 URL

        Returns:
            Optional[str]: aweme_id，如果提取失败返回 None
        """
        try:
            # 创建临时的 TargetHandler 来解析 URL
            # 注意：我们只需要解析 URL，不需要真正发起请求
            handler = TargetHandler(
                request=self.request,
                target=video_url.strip(),
                type="aweme",
                down_path="temp"
            )
            
            # 解析目标 ID
            handler.parse_target_id()
            
            # 如果是视频类型，返回 ID
            if handler.type == "aweme" and handler.id:
                logger.info(f"从 URL 提取视频 ID: {video_url} -> {handler.id}")
                return handler.id
            
            logger.warning(f"URL 不是有效的抖音视频链接：{video_url}")
            return None
            
        except Exception as e:
            logger.error(f"提取视频 ID 失败：{e}")
            return None

    def crawl_videos_by_urls(
        self,
        video_urls: List[str],
        comments_per_video: int = 100,
        save_to_csv: bool = True,
        output_dir: str = "downloads",
    ) -> Dict[str, Any]:
        """
        通过视频 URL 列表爬取评论
        
        这是更可靠的方式，用户可以直接从热榜页面复制视频 URL
        
        Args:
            video_urls: 抖音视频 URL 列表
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
            "message": "",
        }

        try:
            logger.info(f"开始处理 {len(video_urls)} 个视频 URL")
            
            # 处理每个视频 URL
            for idx, video_url in enumerate(video_urls, 1):
                logger.info(f"[{idx}/{len(video_urls)}] 处理：{video_url}")
                
                # 从 URL 提取视频 ID
                aweme_id = self.extract_aweme_id_from_url(video_url)
                
                if not aweme_id:
                    logger.warning(f"无法从 URL 提取视频 ID，跳过：{video_url}")
                    video_info = {
                        "title": f"视频 {idx}",
                        "url": video_url,
                        "success": False,
                        "error": "无法提取视频 ID",
                        "comments_count": 0,
                    }
                    result["videos"].append(video_info)
                    continue

                logger.info(f"  提取到视频 ID: {aweme_id}")
                
                # 爬取评论
                comments, csv_file = self.crawl_video_comments(
                    aweme_id=aweme_id,
                    max_count=comments_per_video,
                    save_to_csv=save_to_csv,
                    output_dir=output_dir,
                )

                video_info = {
                    "title": f"视频 {idx}",
                    "url": video_url,
                    "aweme_id": aweme_id,
                    "comments_count": len(comments),
                    "csv_file": csv_file,
                    "success": True,
                }
                result["videos"].append(video_info)
                result["total_comments"] += len(comments)

                # 添加延迟，避免请求过快
                import time
                time.sleep(1.0)

            result["message"] = f"爬取完成，共 {result['total_comments']} 条评论"
            logger.info(result["message"])
            return result
            
        except Exception as e:
            logger.error(f"爬取视频评论失败：{e}", exc_info=True)
            result["success"] = False
            result["error"] = str(e)
            return result

    def get_video_from_hot_url(self, hot_url: str, hot_title: str) -> Optional[str]:
        """
        从热榜 URL 获取相关视频 ID
        
        方案：访问热榜话题页面，提取第一个视频的 URL
        
        Args:
            hot_url: 热榜话题 URL（如 https://www.douyin.com/hot/2444287）
            hot_title: 热榜标题

        Returns:
            Optional[str]: 视频 aweme_id
        """
        try:
            # 访问热榜话题页面
            logger.info(f"访问热榜话题页面：{hot_url}")
            text = self.request.getHTML(hot_url)
            
            if not text:
                logger.warning(f"热榜话题页面内容为空：{hot_url}")
                return None
            
            # 从页面中提取第一个视频 URL
            # 抖音话题页面的视频 URL 格式：/video/7123456789012345678
            import re
            
            # 匹配视频 URL 模式
            video_url_pattern = r'/video/(\d{19})'
            matches = re.findall(video_url_pattern, text)
            
            if matches:
                # 取第一个视频 ID
                aweme_id = matches[0]
                logger.info(f"从热榜话题页面提取到视频 ID: {aweme_id}")
                return aweme_id
            
            # 如果没有找到，尝试其他模式
            # 可能是 note 类型
            note_url_pattern = r'/note/(\d{19})'
            note_matches = re.findall(note_url_pattern, text)
            
            if note_matches:
                aweme_id = note_matches[0]
                logger.info(f"从热榜话题页面提取到笔记 ID: {aweme_id}")
                return aweme_id
            
            logger.warning(f"未从热榜话题页面找到视频：{hot_title}")
            return None
            
        except Exception as e:
            logger.error(f"获取热榜视频失败：{e}", exc_info=True)
            return None

    def crawl_hot_videos_comments(
        self,
        video_count: int = 10,
        comments_per_video: int = 100,
        save_to_csv: bool = True,
        output_dir: str = "downloads",
        video_ids: Optional[List[str]] = None,  # 新增：手动提供的视频 ID 列表
    ) -> Dict[str, Any]:
        """
        爬取热榜视频的评论
        
        流程：
        1. 获取热榜话题榜单（或手动提供视频 ID）
        2. 访问每个话题页面，提取第一个视频 ID
        3. 爬取该视频的评论

        Args:
            video_count: 爬取多少个热榜视频
            comments_per_video: 每个视频爬取多少条评论
            save_to_csv: 是否保存到 CSV
            output_dir: 输出目录
            video_ids: 手动提供的视频 ID 列表（可选）

        Returns:
            Dict: 爬取结果
        """
        result = {
            "success": True,
            "videos": [],
            "total_comments": 0,
            "timestamp": datetime.datetime.now().isoformat(),
            "message": "",
        }

        try:
            # 如果有手动提供的视频 ID，直接使用
            if video_ids:
                logger.info(f"使用手动提供的 {len(video_ids)} 个视频 ID")
                hot_videos = [
                    {"title": f"视频 {idx}", "url": "", "aweme_id": vid}
                    for idx, vid in enumerate(video_ids, 1)
                ]
            else:
                # 获取热榜视频
                hot_videos = self.get_hot_videos(count=video_count)
                if not hot_videos:
                    result["success"] = False
                    result["error"] = "获取热榜视频失败"
                    return result

            # 处理每个热榜话题
            for idx, video in enumerate(hot_videos, 1):
                logger.info(f"[{idx}/{len(hot_videos)}] 处理：{video['title']}")
                
                # 如果已经有 aweme_id，直接使用
                aweme_id = video.get("aweme_id")
                
                if not aweme_id:
                    hot_url = video.get('url') or video.get('mobile_url')
                    if not hot_url:
                        logger.warning(f"热榜 '{video['title']}' 没有 URL，跳过")
                        video["success"] = False
                        video["error"] = "无 URL"
                        video["comments_count"] = 0
                        result["videos"].append(video)
                        continue

                    # 从热榜页面获取视频 ID
                    aweme_id = self.get_video_from_hot_url(hot_url, video['title'])
                
                if not aweme_id:
                    logger.warning(f"未找到视频 ID，跳过：{video['title']}")
                    video["success"] = False
                    video["error"] = "未找到视频"
                    video["comments_count"] = 0
                    result["videos"].append(video)
                    continue

                logger.info(f"  视频 ID: {aweme_id}")
                
                # 爬取评论
                comments, csv_file = self.crawl_video_comments(
                    aweme_id=aweme_id,
                    max_count=comments_per_video,
                    save_to_csv=save_to_csv,
                    output_dir=output_dir,
                )

                video["comments_count"] = len(comments)
                video["csv_file"] = csv_file
                video["success"] = True
                video["aweme_id"] = aweme_id
                result["videos"].append(video)
                result["total_comments"] += len(comments)

                # 添加延迟，避免请求过快
                import time
                time.sleep(1.5)

            result["message"] = f"爬取完成，共 {result['total_comments']} 条评论"
            logger.info(result["message"])
            return result
        except Exception as e:
            logger.error(f"爬取热榜评论失败：{e}", exc_info=True)
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
        video_title: Optional[str] = None,
    ) -> Optional[str]:
        """保存评论到 CSV
        
        Args:
            comments: 评论列表
            aweme_id: 视频 ID
            output_dir: 输出目录
            video_title: 视频标题（用于文件名，可选）
        
        Returns:
            Optional[str]: 保存的文件路径，失败返回 None
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 如果有标题，使用标题生成文件名
            if video_title:
                logger.info(f"使用标题生成文件名：{video_title}")
                # 清理标题中的非法字符
                safe_title = "".join(c for c in video_title if c not in r'\/:*?"<>|')
                safe_title = safe_title[:50]  # 限制标题长度
                filename = f"comments_{safe_title}_{timestamp}.csv"
            else:
                logger.info(f"没有标题，使用视频 ID 生成文件名：{aweme_id}")
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
            return filepath
        except Exception as e:
            logger.error(f"保存 CSV 失败：{e}")
            return None

    def _save_to_database(self, comments: List[Dict[str, Any]], aweme_id: str):
        """
        保存评论到 MySQL 数据库
        
        Args:
            comments: 评论列表
            aweme_id: 视频 ID
        """
        try:
            from backend.lib.database import db_manager
            from backend.lib.database.models import CommentModel
            
            if not comments:
                return
            
            # 批量插入评论
            sql, params = CommentModel.batch_insert_sql(comments)
            
            with db_manager.get_cursor() as cursor:
                cursor.execute(sql, params)
            
            logger.info(f"已将 {len(comments)} 条评论保存到数据库 (aweme_id: {aweme_id})")
            
        except Exception as e:
            logger.error(f"保存到数据库失败：{e}")

    def get_aweme_id_from_hot_id(self, hot_id: str) -> Optional[str]:
        """
        从数据库查询 hot_id 对应的 aweme_id
        
        Args:
            hot_id: 热榜话题 ID（sentence_id）
            
        Returns:
            Optional[str]: 视频 aweme_id，如果未找到返回 None
        """
        try:
            from backend.lib.database import db_manager
            from backend.lib.database.models import HotSearchModel
            from sqlalchemy import select
            
            with db_manager.get_session() as session:
                stmt = select(HotSearchModel).where(HotSearchModel.hot_id == hot_id)
                result = session.execute(stmt).scalars().first()
                
                if result and result.aweme_id:
                    return result.aweme_id
                
                logger.warning(f"数据库中未找到 hot_id {hot_id} 对应的 aweme_id")
                return None
        except Exception as e:
            logger.error(f"查询 hot_id 失败：{e}", exc_info=True)
            return None

    def save_hot_search_to_db(self, hot_videos: List[Dict[str, Any]]):
        """
        保存热榜数据到数据库
        
        Args:
            hot_videos: 热榜视频列表
        """
        try:
            from backend.lib.database import db_manager
            from backend.lib.database.models import HotSearchModel
            from backend.lib.cover_utils import download_cover
            
            crawl_time = datetime.datetime.now()
            saved_count = 0
            
            logger.info(f"开始保存 {len(hot_videos)} 条热榜数据到数据库")
            
            for video in hot_videos:
                # 保存原始的 hot_value 字符串（如 "100 万"、"100w" 等）
                hot_value_raw = video.get("hot_value", "")
                hot_value = str(hot_value_raw).strip() if hot_value_raw else None
                
                # 下载封面到本地
                cover_url = video.get("cover", "")
                local_cover_path = None
                if cover_url:
                    # 使用 hot_id 作为文件名
                    hot_id = video.get("hot_id", "")
                    local_cover_path = download_cover(cover_url, filename=hot_id if hot_id else None)
                
                data = {
                    "rank": video.get("rank", 0),
                    "title": video.get("title", ""),
                    "hot_value": hot_value,
                    "video_id": video.get("hot_id"),  # 使用话题 ID 作为 video_id
                    "cover_url": local_cover_path or cover_url,  # 优先使用本地路径
                    "crawl_time": crawl_time,
                }
                
                try:
                    sql, params = HotSearchModel.insert_sql(data)
                    
                    with db_manager.get_cursor() as cursor:
                        cursor.execute(sql, params)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"保存单条热榜数据失败 (排名{video.get('rank')}): {e}")
                    continue
            
            logger.success(f"已将 {saved_count}/{len(hot_videos)} 条热榜数据保存到数据库")
            
        except Exception as e:
            logger.error(f"保存热榜数据到数据库失败：{e}", exc_info=True)

    def save_video_info_to_db(self, video_info: Dict[str, Any]):
        """
        保存视频信息到数据库
        
        Args:
            video_info: 视频信息
        """
        try:
            from backend.lib.database import db_manager
            from backend.lib.database.models import VideoModel
            
            # 转换字段名以匹配 VideoModel.insert_sql 的期望格式
            data = {
                "id": video_info.get("aweme_id"),  # aweme_id → id
                "desc": video_info.get("title"),  # title → desc
                "author_nickname": video_info.get("author"),  # author → author_nickname
                "duration": video_info.get("duration"),
                "cover": video_info.get("cover_url"),  # cover_url → cover
                "play_count": video_info.get("play_count"),
                "digg_count": video_info.get("digg_count"),
                "comment_count": video_info.get("comment_count"),
                "share_count": video_info.get("share_count"),
                "crawl_time": datetime.datetime.now(),
            }
            
            sql, params = VideoModel.insert_sql(data)
            
            with db_manager.get_cursor() as cursor:
                cursor.execute(sql, params)
            
            logger.info(f"已将视频信息保存到数据库 (aweme_id: {video_info.get('aweme_id')})")
            
        except Exception as e:
            logger.error(f"保存视频信息到数据库失败：{e}")

    def crawl_hot_comments(
        self,
        video_count: int = 10,
        comments_per_video: int = 100,
        save_to_csv: bool = True,
        save_to_db: bool = False,
        output_dir: Optional[str] = None,
        video_ids: Optional[List[str]] = None,
        start_rank: Optional[int] = None,
        end_rank: Optional[int] = None,
        video_titles: Optional[Dict[str, str]] = None,  # 视频 ID 到标题的映射
    ) -> Dict[str, Any]:
        """
        爬取热榜视频评论（支持数据库）
        
        Args:
            video_count: 爬取多少个视频
            comments_per_video: 每个视频爬取多少条评论
            save_to_csv: 是否保存到 CSV
            save_to_db: 是否保存到数据库
            output_dir: 输出目录
            video_ids: 手动提供的视频 ID 列表（可选）
            start_rank: 起始排名（用于指定排名范围）
            end_rank: 结束排名（用于指定排名范围）
            video_titles: 视频 ID 到标题的映射（可选）

        Returns:
            Dict: 爬取结果
        """
        result = {
            "success": True,
            "videos": [],
            "total_comments": 0,
            "timestamp": datetime.datetime.now().isoformat(),
            "message": "",
        }

        try:
            # 如果有手动提供的视频 ID，先判断是 hot_id 还是 aweme_id
            if video_ids:
                logger.info(f"使用手动提供的 {len(video_ids)} 个视频 ID")
                hot_videos = []
                for idx, vid in enumerate(video_ids, 1):
                    # 判断是否是 hot_id（sentence_id，较短的数字）
                    if len(vid) < 19:
                        # 这是 hot_id，直接访问热榜页面获取视频 ID
                        hot_url = f"https://www.douyin.com/hot/{vid}"
                        # 优先使用传递的标题
                        title = video_titles.get(vid) if video_titles else None
                        if not title:
                            title = f"热榜 {idx}"
                        aweme_id = self.get_video_from_hot_url(hot_url, title)
                        
                        if aweme_id:
                            logger.info(f"从热榜页面 {vid} 获取到 aweme_id: {aweme_id}")
                            hot_videos.append({
                                "title": title,
                                "url": hot_url,
                                "aweme_id": aweme_id,
                                "hot_id": vid,
                            })
                        else:
                            logger.warning(f"未从热榜页面 {vid} 找到视频")
                            hot_videos.append({
                                "title": title,
                                "url": "",
                                "aweme_id": None,
                                "hot_id": vid,
                            })
                    else:
                        # 这是 aweme_id，直接使用
                        title = video_titles.get(vid) if video_titles else None
                        if not title:
                            title = f"视频 {idx}"
                        hot_videos.append({
                            "title": title,
                            "url": "",
                            "aweme_id": vid,
                        })
            else:
                # 获取热榜视频
                # 如果指定了排名范围，需要获取所有热榜然后筛选
                if start_rank is not None and end_rank is not None:
                    logger.info(f"获取热榜视频：第 {start_rank} 到第 {end_rank} 名")
                    # 获取前 end_rank 个热榜
                    all_hot_videos = self.get_hot_videos(count=end_rank)
                    # 筛选出指定排名范围的热榜
                    hot_videos = all_hot_videos[start_rank - 1:end_rank]
                else:
                    hot_videos = self.get_hot_videos(count=video_count)
                
                if not hot_videos:
                    result["success"] = False
                    result["error"] = "获取热榜视频失败"
                    return result
                
                # 注意：热榜评论采集不更新热榜数据，只获取视频 ID 用于爬取评论
                # 热榜数据更新由抖音热榜页面负责

            # 处理每个热榜话题
            for idx, video in enumerate(hot_videos, 1):
                logger.info(f"[{idx}/{len(hot_videos)}] 处理：{video['title']}")
                
                # 如果已经有 aweme_id，直接使用
                aweme_id = video.get("aweme_id")
                
                if not aweme_id:
                    hot_url = video.get('url') or video.get('mobile_url')
                    if not hot_url:
                        logger.warning(f"热榜 '{video['title']}' 没有 URL，跳过")
                        video["success"] = False
                        video["error"] = "无 URL"
                        video["comments_count"] = 0
                        result["videos"].append(video)
                        continue

                    # 从热榜页面获取视频 ID
                    aweme_id = self.get_video_from_hot_url(hot_url, video['title'])
                
                if not aweme_id:
                    logger.warning(f"热榜 '{video['title']}' 没有获取到视频 ID，跳过")
                    video["success"] = False
                    video["error"] = "无视频 ID"
                    video["comments_count"] = 0
                    result["videos"].append(video)
                    continue

                logger.info(f"视频 ID: {aweme_id}")
                video["aweme_id"] = aweme_id

                logger.info(f"准备爬取评论，标题：{video['title']}")
                # 爬取评论
                comments, csv_file = self.crawl_video_comments(
                    aweme_id=aweme_id,
                    max_count=comments_per_video,
                    save_to_csv=save_to_csv,
                    save_to_db=save_to_db,
                    output_dir=output_dir,
                    video_title=video['title'],
                )

                video_info = {
                    "title": f"视频 {idx}",
                    "url": video.get("url", ""),
                    "aweme_id": aweme_id,
                    "comments_count": len(comments),
                    "csv_file": csv_file,
                    "success": True,
                }
                result["videos"].append(video_info)
                result["total_comments"] += len(comments)

                # 添加延迟，避免请求过快
                import time
                time.sleep(1.0)

            result["message"] = f"爬取完成，共 {result['total_comments']} 条评论"
            logger.info(result["message"])
            return result
            
        except Exception as e:
            logger.error(f"爬取视频评论失败：{e}", exc_info=True)
            result["success"] = False
            result["error"] = str(e)
            return result
