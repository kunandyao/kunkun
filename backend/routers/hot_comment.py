"""
热榜评论接口

提供从抖音热榜爬取视频评论并进行数据分析的功能。
所有评论爬取后会自动进行 Spark 数据清洗。
"""

import csv
import datetime
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from ..constants import DOWNLOAD_DIR
from ..state import state
from ..lib.cookies import CookieManager
from ..lib.douyin.hot_comment import DouyinHotCommentFetcher
from ..lib.comment_analyzer import CommentAnalyzer, analyze_comments
from ..lib.preprocessing import SparkPreprocessor
from ..lib.scheduler import scheduler_manager
from ..lib.database.models import HotCommentAnalysisModel
from ..lib.database.connection import db_manager
from ..settings import settings

router = APIRouter(prefix="/api/hot-comment", tags=["热榜评论"])


# ============================================================================
# 请求/响应模型
# ============================================================================


class HotCommentCrawlRequest(BaseModel):
    """热榜评论爬取请求"""

    video_count: int = 10  # 爬取多少个热榜视频
    comments_per_video: int = 100  # 每个视频爬取多少条评论
    save_to_csv: bool = True
    save_to_db: bool = False  # 是否保存到数据库
    video_ids: Optional[List[str]] = None  # 手动提供的视频 ID 列表（可选）
    video_urls: Optional[List[str]] = None  # 手动提供的视频 URL 列表（可选，推荐使用）
    video_titles: Optional[Dict[str, str]] = None  # 视频 ID 到标题的映射（可选）
    start_rank: Optional[int] = None  # 起始排名（用于指定排名范围）
    end_rank: Optional[int] = None  # 结束排名（用于指定排名范围）


class AnalyzeHotCommentsRequest(BaseModel):
    """热榜评论分析请求"""

    csv_files: Optional[List[str]] = None
    generate_report: bool = True


class HotCommentAnalyzeResponse(BaseModel):
    """热榜评论分析响应"""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# 辅助函数
# ============================================================================


def _get_fetcher() -> DouyinHotCommentFetcher:
    """从当前配置构建爬取器"""
    cookie = (settings.get("cookie") or "").strip()
    if not CookieManager.validate_cookie(cookie):
        raise HTTPException(status_code=400, detail="Cookie 无效或未配置，请在设置中填写 Cookie")
    ua = (settings.get("userAgent") or "").strip()
    return DouyinHotCommentFetcher(cookie=cookie, user_agent=ua if ua else None)


def _run_spark_cleaning(csv_path: str, source_id: str) -> Tuple[str, int]:
    """
    对评论 CSV 文件进行 Spark 清洗
    
    Args:
        csv_path: 原始 CSV 文件路径
        source_id: 来源标识（视频ID或热榜标识）
        
    Returns:
        Tuple[str, int]: (清洗后的 CSV 路径, 清洗后的记录数)
    """
    try:
        cleaned_dir = os.path.join(DOWNLOAD_DIR, "comments", "cleaned")
        os.makedirs(cleaned_dir, exist_ok=True)
        
        # 从原始文件名提取标题
        original_filename = os.path.basename(csv_path)
        title_part = source_id  # 默认使用 source_id
        
        if original_filename.startswith("comments_"):
            # 尝试从文件名提取标题（格式：comments_{标题}_{时间戳}.csv）
            name_without_ext = original_filename.replace(".csv", "")
            parts = name_without_ext.split("_", 2)  # 只分割前两个下划线
            if len(parts) >= 3:
                # 格式：comments_{标题或ID}_{时间戳}
                # 检查第三部分是否是时间戳（格式：YYYYMMDD_HHMMSS）
                if len(parts[2]) == 15 and parts[2][:8].isdigit() and parts[2][8] == '_':
                    # 第三部分是时间戳格式，第二部分就是标题或ID
                    title_part = parts[1]
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        cleaned_path = os.path.join(cleaned_dir, f"cleaned_{title_part}_{ts}")
        
        logger.info(f"开始 Spark 数据清洗: {csv_path}")
        preprocessor = SparkPreprocessor()
        n, _ = preprocessor.process_and_save_csv(csv_path, cleaned_path, save_parquet=False)
        
        cleaned_csv_path = f"{cleaned_path}.csv"
        logger.success(f"✓ Spark 清洗完成: {n} 条记录 -> {cleaned_csv_path}")
        
        return cleaned_csv_path, n
    except Exception as e:
        logger.error(f"Spark 清洗失败: {e}")
        return None, 0


def _run_spark_cleaning_batch(csv_paths: List[str], source_id: str) -> List[Dict[str, Any]]:
    """
    批量对多个评论 CSV 文件进行 Spark 清洗
    
    Args:
        csv_paths: 原始 CSV 文件路径列表
        source_id: 来源标识
        
    Returns:
        List[Dict]: 每个文件的清洗结果
    """
    results = []
    for csv_path in csv_paths:
        if csv_path and os.path.exists(csv_path):
            cleaned_path, cleaned_count = _run_spark_cleaning(csv_path, source_id)
            results.append({
                "original_file": csv_path,
                "cleaned_file": cleaned_path,
                "cleaned_count": cleaned_count,
                "success": cleaned_path is not None,
            })
    return results


# ============================================================================
# API 接口
# ============================================================================


@router.post("/data-preprocess")
def data_preprocess() -> Dict[str, Any]:
    """
    手动触发数据预处理（Spark 清洗）
    对最新爬取的评论文件进行 Spark 清洗
    """
    try:
        if not state.latest_hot_comment_files:
            raise HTTPException(status_code=404, detail="没有找到最新的评论文件，请先爬取评论")
        
        cleaned_results = []
        for csv_file in state.latest_hot_comment_files:
            if csv_file and os.path.exists(csv_file):
                filename = os.path.basename(csv_file)
                aweme_id = "unknown"
                if filename.startswith("comments_"):
                    parts = filename.split("_")
                    if len(parts) >= 2:
                        aweme_id = parts[1]
                
                cleaned_path, cleaned_count = _run_spark_cleaning(csv_file, aweme_id)
                cleaned_results.append({
                    "original_file": csv_file,
                    "cleaned_file": cleaned_path,
                    "cleaned_count": cleaned_count,
                    "success": cleaned_path is not None,
                })
        
        return {
            "success": True,
            "data": {
                "cleaned_results": cleaned_results,
                "total_files": len(cleaned_results),
            },
            "message": f"数据预处理完成，共处理 {len(cleaned_results)} 个文件",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"数据预处理失败：{e}")
        raise HTTPException(status_code=500, detail=f"预处理失败：{str(e)}")


@router.post("/crawl")
def crawl_hot_comments(request: HotCommentCrawlRequest) -> Dict[str, Any]:
    """
    爬取热榜视频评论，并自动进行 Spark 清洗

    支持三种方式：
    1. video_urls: 手动提供视频 URL 列表（推荐，最可靠）
    2. video_ids: 手动提供视频 ID 列表
    3. video_count: 自动从热榜获取（使用搜索 API，可能不可靠）

    - video_count: 爬取多少个热榜视频（当 video_ids 和 video_urls 为空时使用）
    - comments_per_video: 每个视频爬取多少条评论
    - save_to_csv: 是否保存到 CSV
    - video_ids: 手动提供的视频 ID 列表（可选）
    - video_urls: 手动提供的视频 URL 列表（可选，推荐使用）
    """
    try:
        fetcher = _get_fetcher()
        
        # 优先级：video_urls > video_ids > video_count
        if request.video_urls:
            # 使用视频 URL 列表爬取（推荐方式）
            result = fetcher.crawl_videos_by_urls(
                video_urls=request.video_urls,
                comments_per_video=request.comments_per_video,
                save_to_csv=request.save_to_csv,
                output_dir=DOWNLOAD_DIR,
            )
        else:
            # 使用原有的热榜爬取逻辑
            result = fetcher.crawl_hot_comments(
                video_count=request.video_count,
                comments_per_video=request.comments_per_video,
                save_to_csv=request.save_to_csv,
                save_to_db=request.save_to_db,
                output_dir=DOWNLOAD_DIR,
                video_ids=request.video_ids,
                start_rank=request.start_rank,
                end_rank=request.end_rank,
                video_titles=request.video_titles,  # 传递标题映射
            )

        # 自动进行 Spark 清洗
        cleaned_results = []
        state.latest_hot_comment_files = []
        if result.get("success") and result.get("videos"):
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            for video_info in result.get("videos", []):
                csv_file = video_info.get("csv_file")
                aweme_id = video_info.get("aweme_id", "unknown")
                if csv_file and os.path.exists(csv_file):
                    # 保存原始文件到状态
                    state.latest_hot_comment_files.append(csv_file)
                    
                    cleaned_path, cleaned_count = _run_spark_cleaning(csv_file, aweme_id)
                    video_info["cleaned_file"] = cleaned_path
                    video_info["cleaned_count"] = cleaned_count
                    cleaned_results.append({
                        "aweme_id": aweme_id,
                        "original_file": csv_file,
                        "cleaned_file": cleaned_path,
                        "cleaned_count": cleaned_count,
                    })

        return {
            "success": result.get("success", False),
            "data": result,
            "cleaned_results": cleaned_results,
            "message": "爬取完成" if result.get("success") else result.get("error", "爬取失败"),
        }
    except Exception as e:
        logger.error(f"爬取热榜评论失败：{e}")
        raise HTTPException(status_code=500, detail=f"爬取失败：{str(e)}")


def _get_all_comments_files() -> List[str]:
    """获取所有评论文件"""
    try:
        files = []
        if os.path.exists(DOWNLOAD_DIR):
            for filename in os.listdir(DOWNLOAD_DIR):
                if filename.startswith("comments_") and filename.endswith(".csv"):
                    filepath = os.path.join(DOWNLOAD_DIR, filename)
                    files.append(filepath)
        
        # 按修改时间倒序
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return files
    except Exception as e:
        logger.error(f"获取所有评论文件失败：{e}")
        return []


@router.post("/analyze")
def analyze_hot_comments(request: AnalyzeHotCommentsRequest) -> Dict[str, Any]:
    """
    分析热榜评论数据

    - csv_files: CSV 文件列表
    - generate_report: 是否生成报告
    """
    try:
        # 如果没有指定文件，优先使用最新爬取的文件列表，否则使用所有可用的评论文件
        csv_files = request.csv_files or []
        if not csv_files:
            # 优先使用最新爬取的所有文件
            if state.latest_hot_comment_files:
                csv_files = state.latest_hot_comment_files
                logger.info(f"使用最新爬取的 {len(csv_files)} 个文件进行分析")
            else:
                # 查找所有可用的评论文件
                all_files = _get_all_comments_files()
                if all_files:
                    csv_files = all_files
                    logger.info(f"找到 {len(csv_files)} 个评论文件")
                else:
                    raise HTTPException(status_code=404, detail="未找到评论数据文件")

        # 对每个视频单独分析
        video_analyses = []
        total_all_comments = 0
        
        for csv_file in csv_files:
            filepath = os.path.join(DOWNLOAD_DIR, csv_file) if not os.path.isabs(csv_file) else csv_file
            if not os.path.exists(filepath):
                logger.warning(f"文件不存在，跳过：{filepath}")
                continue
            
            try:
                # 读取单个视频的评论
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    comments = list(reader)
                
                if not comments:
                    logger.warning(f"文件没有评论数据，跳过：{filepath}")
                    continue
                
                total_all_comments += len(comments)
                
                # 分析单个视频的评论
                analyzer = CommentAnalyzer(comments=comments)
                analysis_result = analyzer.analyze()
                
                # 生成报告
                report = None
                if request.generate_report:
                    report = _generate_report(analysis_result)
                
                # 提取视频 ID 从文件名
                filename = os.path.basename(filepath)
                aweme_id = "unknown"
                if filename.startswith("comments_"):
                    parts = filename.split("_")
                    if len(parts) >= 2:
                        aweme_id = parts[1]
                
                video_analyses.append({
                    "file": filename,
                    "filepath": filepath,
                    "aweme_id": aweme_id,
                    "analysis": analysis_result,
                    "report": report,
                    "total_comments": len(comments),
                })
                
            except Exception as e:
                logger.error(f"分析文件失败 {filepath}: {e}", exc_info=True)

        if not video_analyses:
            raise HTTPException(status_code=400, detail="没有评论数据可分析")

        # 将分析结果写入数据库
        try:
            from datetime import datetime
            from backend.lib.cover_utils import download_cover
            
            for analysis in video_analyses:
                # 从热榜表获取 hot_id、标题和封面图（通过标题关联）
                hot_id = None
                title = None
                cover_url = None
                
                # 先尝试从文件名提取标题
                filename = analysis.get('file', '')
                extracted_title = None
                if filename.startswith('comments_'):
                    import re
                    name = filename[9:-4]  # 去掉 "comments_" 和 ".csv"
                    match = re.match(r'(.+)_(\d{8})_(\d{6})$', name)
                    if match:
                        extracted_title = match.group(1)
                
                # 通过标题在 hot_search 表中查找 - 尝试多种匹配方式
                if extracted_title:
                    try:
                        # 方式1: 精确匹配
                        sql_info = "SELECT video_id, title, cover_url FROM hot_search WHERE title = %s ORDER BY crawl_time DESC LIMIT 1"
                        info_result = db_manager.fetch_one(sql_info, (extracted_title,))
                        
                        # 方式2: LIKE 匹配
                        if not info_result:
                            sql_info = "SELECT video_id, title, cover_url FROM hot_search WHERE title LIKE %s ORDER BY crawl_time DESC LIMIT 1"
                            info_result = db_manager.fetch_one(sql_info, (f'%{extracted_title}%',))
                        
                        if info_result:
                            hot_id = info_result.get('video_id')
                            title = info_result.get('title')
                            cover_url = info_result.get('cover_url')
                            logger.info(f"通过标题 '{extracted_title}' 关联到 hot_id: {hot_id}, cover_url: {cover_url[:60] if cover_url else 'None'}")
                            
                            # 如果 cover_url 不是本地路径，尝试下载
                            if cover_url and not cover_url.startswith('/static/covers/') and hot_id:
                                local_cover = download_cover(cover_url, filename=hot_id)
                                if local_cover:
                                    cover_url = local_cover
                                    logger.info(f"已下载封面到本地: {local_cover}")
                    except Exception as e_info:
                        logger.warning(f"获取热榜信息失败 '{extracted_title}': {e_info}")
                
                # 更新 video_analyses 中的标题和封面图
                analysis['title'] = title or extracted_title
                analysis['cover_url'] = cover_url
                analysis['hot_id'] = hot_id
                
                analysis_data = {
                    'aweme_id': analysis['aweme_id'],
                    'hot_id': hot_id,
                    'title': title or extracted_title,
                    'cover_url': cover_url,
                    'filename': analysis['file'],
                    'filepath': analysis['filepath'],
                    'total_comments': analysis['total_comments'],
                    'sentiment_positive': analysis['analysis']['sentiment']['positive'],
                    'sentiment_neutral': analysis['analysis']['sentiment']['neutral'],
                    'sentiment_negative': analysis['analysis']['sentiment']['negative'],
                    'sentiment_positive_rate': analysis['analysis']['sentiment']['positive_rate'],
                    'sentiment_neutral_rate': analysis['analysis']['sentiment']['neutral_rate'],
                    'sentiment_negative_rate': analysis['analysis']['sentiment']['negative_rate'],
                    'hot_words': analysis['analysis']['hot_words'],
                    'location_distribution': analysis['analysis']['location_distribution'],
                    'time_distribution': analysis['analysis']['time_distribution'],
                    'user_activity': analysis['analysis']['user_activity'],
                    'top_comments': analysis['analysis']['top_comments'],
                    'created_time': datetime.now()
                }
                sql, params = HotCommentAnalysisModel.insert_sql(analysis_data)
                with db_manager.get_cursor() as cursor:
                    cursor.execute(sql, params)
            logger.info(f"成功将 {len(video_analyses)} 个分析结果写入数据库")
        except Exception as e:
            logger.error(f"写入数据库失败: {e}", exc_info=True)

        return {
            "success": True,
            "data": {
                "video_analyses": video_analyses,
                "total_videos": len(video_analyses),
                "total_all_comments": total_all_comments,
            },
            "message": f"分析完成，共分析 {len(video_analyses)} 个视频",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析热榜评论失败：{e}")
        raise HTTPException(status_code=500, detail=f"分析失败：{str(e)}")


@router.get("/list")
def get_hot_comments_list() -> Dict[str, Any]:
    """
    获取已爬取的评论文件列表
    """
    try:
        files = []
        if os.path.exists(DOWNLOAD_DIR):
            for filename in os.listdir(DOWNLOAD_DIR):
                if filename.startswith("comments_") and filename.endswith(".csv"):
                    filepath = os.path.join(DOWNLOAD_DIR, filename)
                    stat = os.stat(filepath)
                    files.append({
                        "filename": filename,
                        "filepath": filepath,
                        "size": stat.st_size,
                        "created_time": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_time": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
        
        # 按修改时间倒序
        files.sort(key=lambda x: x["modified_time"], reverse=True)

        return {
            "success": True,
            "files": files,
        }
    except Exception as e:
        logger.error(f"获取评论文件列表失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取失败：{str(e)}")


@router.get("/proxy-cover")
def proxy_cover_image(url: str):
    """
    代理封面图（解决防盗链问题）
    
    - url: 封面图 URL
    """
    try:
        if not url:
            raise HTTPException(status_code=400, detail="URL 不能为空")
        
        # 设置 Referer 伪装成抖音
        headers = {
            "Referer": "https://www.douyin.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        response = requests.get(url, headers=headers, timeout=10, stream=True)
        
        if response.status_code != 200:
            logger.debug(f"获取封面图失败：{url}, status: {response.status_code}")
            raise HTTPException(status_code=404, detail="图片加载失败")
        
        # 获取图片类型
        content_type = response.headers.get("Content-Type", "image/jpeg")
        
        return StreamingResponse(
            response.iter_content(chunk_size=8192),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # 缓存 1 小时
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"代理封面图失败：{e}")
        raise HTTPException(status_code=500, detail=f"加载失败：{str(e)}")


@router.get("/report")
def get_analysis_report(csv_file: Optional[str] = None) -> Dict[str, Any]:
    """
    获取评论分析报告

    - csv_file: CSV 文件名，不传则使用最新文件
    """
    try:
        # 获取文件
        filepath = csv_file
        if not filepath:
            filepath = _get_latest_comments_file()
        
        if not filepath or not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="未找到评论数据文件")

        # 加载数据
        comments = []
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            comments = list(reader)

        if not comments:
            raise HTTPException(status_code=400, detail="评论数据为空")

        # 分析
        analyzer = CommentAnalyzer(comments=comments)
        analysis_result = analyzer.analyze()

        # 生成报告
        report = _generate_report(analysis_result)

        return {
            "success": True,
            "data": {
                "analysis": analysis_result,
                "report": report,
                "total_comments": len(comments),
                "file": os.path.basename(filepath),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成分析报告失败：{e}")
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")


# ============================================================================
# 内部辅助函数
# ============================================================================


def _get_latest_comments_file() -> Optional[str]:
    """获取最新的评论文件"""
    try:
        latest_file = None
        latest_time = 0
        
        if os.path.exists(DOWNLOAD_DIR):
            for filename in os.listdir(DOWNLOAD_DIR):
                if filename.startswith("comments_") and filename.endswith(".csv"):
                    filepath = os.path.join(DOWNLOAD_DIR, filename)
                    stat = os.stat(filepath)
                    if stat.st_mtime > latest_time:
                        latest_time = stat.st_mtime
                        latest_file = filepath
        
        return latest_file
    except Exception as e:
        logger.error(f"获取最新评论文件失败：{e}")
        return None


def _generate_report(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """生成分析报告"""
    report = {
        "summary": {
            "total_comments": analysis_result.get("total", 0),
            "hot_words_count": len(analysis_result.get("hot_words", [])),
            "locations_count": len(analysis_result.get("location_distribution", [])),
        },
        "highlights": [],
    }

    # 热门词汇
    hot_words = analysis_result.get("hot_words", [])
    if hot_words:
        report["highlights"].append({
            "title": "热门词汇",
            "content": f"Top 5: {', '.join([f'{w}({c})' for w, c in hot_words[:5]])}",
        })

    # 地区分布
    locations = analysis_result.get("location_distribution", [])
    if locations:
        report["highlights"].append({
            "title": "地区分布",
            "content": f"Top 3: {', '.join([f'{loc}({c})' for loc, c in locations[:3]])}",
        })

    # 热门评论
    top_comments = analysis_result.get("top_comments", [])
    if top_comments:
        report["highlights"].append({
            "title": "热门评论",
            "content": f"最高赞：{top_comments[0].get('text', '')[:50]}... ({top_comments[0].get('digg_count', 0)}赞)",
        })

    return report


# ============================================================================
# 定时任务 API
# ============================================================================


class SchedulerStartRequest(BaseModel):
    """定时任务启动请求"""

    interval_hours: int = 2  # 间隔小时数
    video_count: int = 10  # 视频数量
    comments_per_video: int = 100  # 每视频评论数
    save_to_db: bool = False  # 是否保存到数据库


class SchedulerStatusResponse(BaseModel):
    """定时任务状态响应"""
    
    success: bool
    is_running: bool
    interval_hours: int = 0
    video_count: int = 0
    comments_per_video: int = 0
    last_run_time: Optional[str] = None
    next_run_time: Optional[str] = None
    total_runs: int = 0
    total_comments: int = 0


def _crawl_task(video_count: int, comments_per_video: int, save_to_db: bool = False) -> dict:
    """定时爬取任务函数，爬取后自动进行 Spark 清洗"""
    try:
        fetcher = _get_fetcher()
        
        # 先刷新热榜数据到数据库
        try:
            hot_videos = fetcher.get_hot_videos(count=30)
            if hot_videos:
                fetcher.save_hot_search_to_db(hot_videos)
                logger.info(f"定时任务已刷新热榜数据：{len(hot_videos)} 条")
        except Exception as e:
            logger.warning(f"定时任务刷新热榜失败：{e}")
        
        # 爬取评论
        result = fetcher.crawl_hot_comments(
            video_count=video_count,
            comments_per_video=comments_per_video,
            save_to_csv=True,
            save_to_db=save_to_db,
            output_dir=DOWNLOAD_DIR,
        )
        
        # 自动进行 Spark 清洗
        cleaned_count = 0
        if result.get("success") and result.get("videos"):
            for video_info in result.get("videos", []):
                csv_file = video_info.get("csv_file")
                aweme_id = video_info.get("aweme_id", "unknown")
                if csv_file and os.path.exists(csv_file):
                    try:
                        cleaned_path, count = _run_spark_cleaning(csv_file, aweme_id)
                        video_info["cleaned_file"] = cleaned_path
                        video_info["cleaned_count"] = count
                        cleaned_count += count if count else 0
                    except Exception as e:
                        logger.error(f"定时任务 Spark 清洗失败 {csv_file}: {e}")
        
        result["cleaned_count"] = cleaned_count
        return result
    except Exception as e:
        logger.error(f"定时爬取任务失败：{e}")
        return {"success": False, "error": str(e)}


@router.post("/scheduler/start")
def start_scheduler(request: SchedulerStartRequest) -> Dict[str, Any]:
    """
    启动定时爬取任务
    
    - interval_hours: 间隔小时数，默认 2 小时
    - video_count: 每次爬取多少个视频，默认 10 个
    - comments_per_video: 每个视频爬取多少条评论，默认 100 条
    - save_to_db: 是否保存到数据库
    """
    try:
        success = scheduler_manager.start(
            task_func=_crawl_task,
            interval_hours=request.interval_hours,
            video_count=request.video_count,
            comments_per_video=request.comments_per_video,
            save_to_db=request.save_to_db,
        )
        
        if success:
            return {
                "success": True,
                "message": "定时任务已启动",
                "data": scheduler_manager.get_status(),
            }
        else:
            return {
                "success": False,
                "message": "定时任务已在运行中",
            }
    except Exception as e:
        logger.error(f"启动定时任务失败：{e}")
        raise HTTPException(status_code=500, detail=f"启动失败：{str(e)}")


@router.post("/scheduler/stop")
def stop_scheduler() -> Dict[str, Any]:
    """停止定时爬取任务"""
    try:
        success = scheduler_manager.stop()
        
        return {
            "success": success,
            "message": "定时任务已停止" if success else "定时任务未运行",
        }
    except Exception as e:
        logger.error(f"停止定时任务失败：{e}")
        raise HTTPException(status_code=500, detail=f"停止失败：{str(e)}")


@router.get("/scheduler/status")
def get_scheduler_status() -> Dict[str, Any]:
    """获取定时任务状态"""
    try:
        status = scheduler_manager.get_status()
        
        return {
            "success": True,
            "data": status,
        }
    except Exception as e:
        logger.error(f"获取定时任务状态失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取失败：{str(e)}")


# ============================================================================
# 数据库相关接口
# ============================================================================


@router.post("/database/init")
def init_database() -> Dict[str, Any]:
    """
    初始化 MySQL 数据库
    """
    try:
        from backend.lib.database.init import create_database, init_tables
        
        # 创建数据库
        if not create_database():
            raise HTTPException(status_code=500, detail="创建数据库失败")
        
        # 初始化表
        if not init_tables():
            raise HTTPException(status_code=500, detail="初始化数据表失败")
        
        return {
            "success": True,
            "message": "数据库初始化成功",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"初始化数据库失败：{e}")
        raise HTTPException(status_code=500, detail=f"初始化失败：{str(e)}")


@router.get("/database/status")
def get_database_status() -> Dict[str, Any]:
    """
    获取数据库连接状态
    """
    try:
        from backend.lib.database import db_manager
        
        is_connected = db_manager.test_connection()
        
        if is_connected:
            # 获取统计信息
            with db_manager.get_cursor() as cursor:
                # 热榜数据总数
                cursor.execute("SELECT COUNT(*) as count FROM hot_search")
                hot_search_count = cursor.fetchone().get('count', 0)
                
                # 视频总数
                cursor.execute("SELECT COUNT(*) as count FROM videos")
                video_count = cursor.fetchone().get('count', 0)
                
                # 评论总数
                cursor.execute("SELECT COUNT(*) as count FROM comments")
                comment_count = cursor.fetchone().get('count', 0)
                
                # 定时任务执行次数
                cursor.execute("SELECT COUNT(*) as count FROM scheduler_history")
                scheduler_count = cursor.fetchone().get('count', 0)
            
            return {
                "success": True,
                "data": {
                    "connected": True,
                    "statistics": {
                        "hot_search_count": hot_search_count,
                        "video_count": video_count,
                        "comment_count": comment_count,
                        "scheduler_count": scheduler_count,
                    }
                },
                "message": "数据库连接正常",
            }
        else:
            return {
                "success": False,
                "data": {
                    "connected": False,
                },
                "message": "数据库未连接",
            }
    except Exception as e:
        logger.error(f"获取数据库状态失败：{e}")
        return {
            "success": False,
            "data": {
                "connected": False,
            },
            "message": f"数据库连接失败：{str(e)}",
        }


@router.get("/database/comments")
def get_comments_from_db(
    aweme_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "digg_count",
) -> Dict[str, Any]:
    """
    从数据库获取评论数据
    
    - aweme_id: 视频 ID（可选，不传则获取所有评论）
    - limit: 返回数量限制
    - offset: 偏移量
    - order_by: 排序字段（digg_count/create_time）
    """
    try:
        from backend.lib.database import db_manager
        
        if aweme_id:
            sql = f"""
                SELECT * FROM comments 
                WHERE aweme_id = %s 
                ORDER BY {order_by} DESC 
                LIMIT %s OFFSET %s
            """
            params = (aweme_id, limit, offset)
        else:
            sql = f"""
                SELECT * FROM comments 
                ORDER BY {order_by} DESC 
                LIMIT %s OFFSET %s
            """
            params = (limit, offset)
        
        comments = db_manager.fetch_all(sql, params)
        
        # 获取总数
        if aweme_id:
            count_sql = "SELECT COUNT(*) as count FROM comments WHERE aweme_id = %s"
            count_params = (aweme_id,)
        else:
            count_sql = "SELECT COUNT(*) as count FROM comments"
            count_params = None
        
        total = db_manager.fetch_one(count_sql, count_params).get('count', 0)
        
        return {
            "success": True,
            "data": {
                "comments": comments,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "message": "查询成功",
        }
    except Exception as e:
        logger.error(f"查询评论失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.get("/database/statistics")
def get_database_statistics() -> Dict[str, Any]:
    """
    获取数据库统计信息
    """
    try:
        from backend.lib.database import db_manager
        
        with db_manager.get_cursor() as cursor:
            # 热榜数据总数
            cursor.execute("SELECT COUNT(*) as count FROM hot_search")
            hot_search_count = cursor.fetchone().get('count', 0)
            
            # 视频总数
            cursor.execute("SELECT COUNT(*) as count FROM videos")
            video_count = cursor.fetchone().get('count', 0)
            
            # 评论总数
            cursor.execute("SELECT COUNT(*) as count FROM comments")
            comment_count = cursor.fetchone().get('count', 0)
            
            # 定时任务执行次数
            cursor.execute("SELECT COUNT(*) as count FROM scheduler_history")
            scheduler_count = cursor.fetchone().get('count', 0)
            
            # 最新评论
            cursor.execute("""
                SELECT aweme_id, nickname, text, create_time, digg_count 
                FROM comments 
                ORDER BY crawl_time DESC 
                LIMIT 10
            """)
            latest_comments = cursor.fetchall()
            
            # 最热门评论（点赞最多）
            cursor.execute("""
                SELECT aweme_id, nickname, text, digg_count 
                FROM comments 
                ORDER BY digg_count DESC 
                LIMIT 10
            """)
            top_comments = cursor.fetchall()
        
        return {
            "success": True,
            "data": {
                "total": {
                    "hot_search": hot_search_count,
                    "videos": video_count,
                    "comments": comment_count,
                    "scheduler_runs": scheduler_count,
                },
                "latest_comments": latest_comments,
                "top_comments": top_comments,
            },
            "message": "统计成功",
        }
    except Exception as e:
        logger.error(f"获取统计信息失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败：{str(e)}")


@router.get("/analysis/list")
def get_analysis_list() -> Dict[str, Any]:
    """
    从数据库获取所有热榜评论分析结果
    """
    try:
        import json
        
        sql = """
        SELECT id, aweme_id, hot_id, title, cover_url, filename, filepath, total_comments,
               sentiment_positive, sentiment_neutral, sentiment_negative,
               sentiment_positive_rate, sentiment_neutral_rate, sentiment_negative_rate,
               hot_words, location_distribution, time_distribution, 
               user_activity, top_comments, created_time
        FROM hot_comment_analysis
        ORDER BY created_time DESC
        """
        
        with db_manager.get_cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        
        video_analyses = []
        for row in rows:
            video_analyses.append({
                "file": row['filename'],
                "filepath": row['filepath'],
                "title": row.get('title'),
                "aweme_id": row['aweme_id'],
                "hot_id": row.get('hot_id'),
                "cover_url": row.get('cover_url'),
                "analysis": {
                    "total": row['total_comments'],
                    "hot_words": json.loads(row['hot_words']) if row['hot_words'] else [],
                    "location_distribution": json.loads(row['location_distribution']) if row['location_distribution'] else [],
                    "sentiment": {
                        "positive": row['sentiment_positive'],
                        "neutral": row['sentiment_neutral'],
                        "negative": row['sentiment_negative'],
                        "positive_rate": float(row['sentiment_positive_rate']) if row['sentiment_positive_rate'] else 0,
                        "neutral_rate": float(row['sentiment_neutral_rate']) if row['sentiment_neutral_rate'] else 0,
                        "negative_rate": float(row['sentiment_negative_rate']) if row['sentiment_negative_rate'] else 0,
                    },
                    "time_distribution": json.loads(row['time_distribution']) if row['time_distribution'] else {},
                    "user_activity": json.loads(row['user_activity']) if row['user_activity'] else {},
                    "top_comments": json.loads(row['top_comments']) if row['top_comments'] else [],
                },
                "report": None,
                "total_comments": row['total_comments'],
            })
        
        return {
            "success": True,
            "data": {
                "video_analyses": video_analyses,
                "total_videos": len(video_analyses),
                "total_all_comments": sum([v['total_comments'] for v in video_analyses]),
            },
        }
    except Exception as e:
        logger.error(f"从数据库获取分析结果失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取失败：{str(e)}")


@router.post("/database/clear")
def clear_database_data(table: Optional[str] = None) -> Dict[str, Any]:
    """
    清空数据库数据
    
    - table: 表名（可选，不传则清空所有表）
      可选值：hot_search, videos, comments, scheduler_history, hot_comment_analysis
    """
    try:
        from backend.lib.database import db_manager
        
        tables = ["hot_search", "videos", "comments", "scheduler_history", "hot_comment_analysis"]
        
        if table:
            if table not in tables:
                raise HTTPException(status_code=400, detail=f"无效的表名：{table}")
            tables_to_clear = [table]
        else:
            tables_to_clear = tables
        
        with db_manager.get_cursor() as cursor:
            for table_name in tables_to_clear:
                cursor.execute(f"TRUNCATE TABLE {table_name}")
                logger.info(f"已清空表：{table_name}")
        
        return {
            "success": True,
            "message": f"已清空 {len(tables_to_clear)} 个表",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清空数据失败：{e}")
        raise HTTPException(status_code=500, detail=f"清空失败：{str(e)}")
