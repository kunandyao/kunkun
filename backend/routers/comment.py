"""
评论接口

提供作品评论列表（单页）与多页爬取（导出 CSV）。
支持浏览器自动化爬取和数据分析功能。

所有评论爬取后会自动进行 Spark 数据清洗。
"""

import csv
import datetime
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from ..constants import DOWNLOAD_DIR, PROJECT_ROOT
from ..lib.cookies import CookieManager
from ..lib.douyin.client import DouyinClient
from ..lib.douyin.request import Request
from ..lib.comment_analyzer import CommentAnalyzer, analyze_comments
from ..lib.preprocessing import SparkPreprocessor
from ..lib.cover_utils import download_cover
from ..lib.database.models import HotCommentAnalysisModel
from ..settings import settings
import json

router = APIRouter(prefix="/api/comment", tags=["评论"])


# ============================================================================
# 请求/响应模型
# ============================================================================


class CommentCrawlRequest(BaseModel):
    """评论爬取请求"""

    aweme_id: str
    max_count: int = 500  # 最多爬取条数，0 表示不限制（按页直到 has_more=0）
    title: Optional[str] = None  # 作品标题（可选，用于API限流时作为备选）
    cover_url: Optional[str] = None  # 封面URL（可选，用于API限流时作为备选）


class BrowserCrawlRequest(BaseModel):
    """浏览器自动化爬取请求"""

    aweme_id: str
    video_url: Optional[str] = None
    max_count: Optional[int] = 500


class AnalyzeRequest(BaseModel):
    """评论分析请求"""

    csv_file: Optional[str] = None
    generate_report: bool = True


def _resolve_comment_csv_path(explicit: Optional[str]) -> Optional[str]:
    """
    评论 CSV 路径：绝对路径 / 相对 download / 相对项目根；未指定则在
    download/comments/*.csv 与 download 根目录下名称含 comment 的 *.csv 中取最新修改时间。
    """
    if explicit:
        p = explicit.strip()
        if os.path.isfile(p):
            return os.path.normpath(p)
        for base in (DOWNLOAD_DIR, PROJECT_ROOT):
            cand = os.path.normpath(os.path.join(base, p))
            if os.path.isfile(cand):
                return cand
        return None

    candidates: List[str] = []
    sub = os.path.join(DOWNLOAD_DIR, "comments")
    if os.path.isdir(sub):
        for name in os.listdir(sub):
            if name.lower().endswith(".csv"):
                candidates.append(os.path.join(sub, name))
    if os.path.isdir(DOWNLOAD_DIR):
        for name in os.listdir(DOWNLOAD_DIR):
            if not name.lower().endswith(".csv"):
                continue
            low = name.lower()
            if low.startswith("comments") or "comment" in low:
                candidates.append(os.path.join(DOWNLOAD_DIR, name))
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def _normalize_comment(raw: dict) -> dict:
    """将接口返回的单条评论转为前端使用的结构"""
    cid = raw.get("cid") or str(raw.get("id", ""))
    user = raw.get("user") or {}
    create_time = raw.get("create_time") or 0
    try:
        dt = datetime.datetime.fromtimestamp(create_time)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        time_str = str(create_time)
    return {
        "id": cid,
        "nickname": user.get("nickname", "未知用户"),
        "text": (raw.get("text") or "").strip(),
        "create_time": time_str,
        "digg_count": raw.get("digg_count", 0),
        "reply_count": raw.get("reply_comment_total", 0),
        "ip_label": raw.get("ip_label", ""),
        "is_top": bool(raw.get("stick_position", 0)),
        "is_hot": bool(raw.get("is_hot_comment", 0)),
    }


def _get_client() -> DouyinClient:
    """从当前配置构建 Request + DouyinClient"""
    cookie = (settings.get("cookie") or "").strip()
    if not CookieManager.validate_cookie(cookie):
        raise HTTPException(status_code=400, detail="Cookie 无效或未配置，请在设置中填写 Cookie")
    ua = (settings.get("userAgent") or "").strip()
    req = Request(cookie=cookie, UA=ua)
    return DouyinClient(req)


def _run_spark_cleaning(csv_path: str, aweme_id: str) -> Tuple[str, int]:
    """
    对评论 CSV 文件进行 Spark 清洗
    
    Args:
        csv_path: 原始 CSV 文件路径
        aweme_id: 视频 ID
        
    Returns:
        Tuple[str, int]: (清洗后的 CSV 路径, 清洗后的记录数)
    """
    try:
        cleaned_dir = os.path.join(DOWNLOAD_DIR, "comments", "cleaned")
        os.makedirs(cleaned_dir, exist_ok=True)
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        cleaned_path = os.path.join(cleaned_dir, f"cleaned_{aweme_id}_{ts}")
        
        logger.info(f"开始 Spark 数据清洗: {csv_path}")
        preprocessor = SparkPreprocessor()
        n, _ = preprocessor.process_and_save_csv(csv_path, cleaned_path, save_parquet=False)
        
        cleaned_csv_path = f"{cleaned_path}.csv"
        logger.success(f"✓ Spark 清洗完成: {n} 条记录 -> {cleaned_csv_path}")
        
        return cleaned_csv_path, n
    except Exception as e:
        logger.error(f"Spark 清洗失败: {e}")
        return None, 0


@router.get("/list")
def get_comment_list(
    aweme_id: str,
    cursor: int = 0,
    count: int = 20,
) -> Dict[str, Any]:
    """
    获取评论列表（单页）

    - aweme_id: 作品 ID
    - cursor: 分页游标，0 为第一页
    - count: 每页条数
    """
    if not aweme_id.strip():
        raise HTTPException(status_code=400, detail="aweme_id 不能为空")
    try:
        client = _get_client()
        resp = client.fetch_comment_list(aweme_id=aweme_id, cursor=cursor, count=count)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("评论列表请求失败")
        raise HTTPException(status_code=500, detail=str(e))

    if not resp:
        return {"comments": [], "cursor": 0, "has_more": False}

    raw_list = resp.get("comments") or []
    comments = [_normalize_comment(c) for c in raw_list]
    next_cursor = resp.get("cursor", 0)
    has_more = bool(resp.get("has_more", 0))

    return {
        "comments": comments,
        "cursor": next_cursor,
        "has_more": has_more,
    }


@router.post("/crawl")
def crawl_comments(request: CommentCrawlRequest) -> Dict[str, Any]:
    """
    多页爬取评论，返回列表并导出 CSV，然后自动进行 Spark 清洗

    - aweme_id: 作品 ID
    - max_count: 最多爬取条数，默认 500；0 表示不限制
    """
    aweme_id = request.aweme_id.strip()
    if not aweme_id:
        raise HTTPException(status_code=400, detail="aweme_id 不能为空")

    max_count = request.max_count
    if max_count < 0:
        max_count = 500

    try:
        client = _get_client()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    all_comments: List[dict] = []
    cursor = 0
    page_size = 20
    max_no_data = 5
    no_data_count = 0

    while no_data_count < max_no_data:
        resp = client.fetch_comment_list(
            aweme_id=aweme_id, cursor=cursor, count=page_size
        )
        if not resp:
            no_data_count += 1
            time.sleep(0.5)
            continue

        raw_list = resp.get("comments") or []
        if not raw_list:
            no_data_count += 1
            if not resp.get("has_more", False):
                break
            cursor = resp.get("cursor", cursor)
            time.sleep(0.3)
            continue

        no_data_count = 0
        for c in raw_list:
            all_comments.append(_normalize_comment(c))
            if max_count and len(all_comments) >= max_count:
                break

        if max_count and len(all_comments) >= max_count:
            break

        if not resp.get("has_more", False):
            break
        cursor = resp.get("cursor", cursor)
        time.sleep(0.3)

    # 导出原始 CSV 到下载目录
    comments_dir = os.path.join(DOWNLOAD_DIR, "comments")
    os.makedirs(comments_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"comments_{aweme_id}_{ts}.csv"
    csv_path = os.path.join(comments_dir, csv_filename)

    fieldnames = [
        "id", "nickname", "text", "create_time", "digg_count",
        "reply_count", "ip_label", "is_top", "is_hot",
    ]
    try:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in all_comments:
                w.writerow({k: row.get(k, "") for k in fieldnames})
        logger.info(f"✓ 原始评论已保存: {csv_path}")
    except Exception as e:
        logger.warning("评论 CSV 写入失败: {}", e)
        csv_path = None

    # 自动进行 Spark 清洗
    cleaned_csv_path = None
    cleaned_count = 0
    if csv_path and os.path.exists(csv_path):
        cleaned_csv_path, cleaned_count = _run_spark_cleaning(csv_path, aweme_id)

    return {
        "comments": all_comments,
        "total": len(all_comments),
        "file": csv_path,
        "filename": csv_filename if csv_path else None,
        "cleaned_file": cleaned_csv_path,
        "cleaned_count": cleaned_count,
    }


@router.post("/crawl-browser")
def crawl_comments_browser(request: BrowserCrawlRequest) -> Dict[str, Any]:
    """
    使用浏览器自动化爬取评论（API方式的备用方案）
    爬取后自动进行 Spark 清洗

    - aweme_id: 作品 ID
    - video_url: 可选的视频URL
    - max_count: 最多爬取条数
    """
    aweme_id = request.aweme_id.strip()
    if not aweme_id:
        raise HTTPException(status_code=400, detail="aweme_id 不能为空")

    try:
        from ..lib.comment_browser_crawler import BrowserCommentCrawler
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"浏览器自动化功能需要安装 DrissionPage: pip install DrissionPage"
        )

    try:
        crawler = BrowserCommentCrawler(
            aweme_id=aweme_id,
            video_url=request.video_url,
            max_comments=request.max_count,
        )
        result = crawler.crawl()

        # 自动进行 Spark 清洗
        cleaned_csv_path = None
        cleaned_count = 0
        if result.get("output_file") and os.path.exists(result["output_file"]):
            cleaned_csv_path, cleaned_count = _run_spark_cleaning(
                result["output_file"], aweme_id
            )

        return {
            "comments": result["comments"],
            "total": result["total"],
            "file": result["output_file"],
            "method": "browser",
            "cleaned_file": cleaned_csv_path,
            "cleaned_count": cleaned_count,
        }
    except Exception as e:
        logger.exception("浏览器自动化爬取失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
def analyze_comments_endpoint(request: AnalyzeRequest) -> Dict[str, Any]:
    """
    分析评论数据并生成报告

    - csv_file: CSV文件路径，如果不提供则使用最近爬取的评论
    - generate_report: 是否生成HTML报告
    """
    csv_file = request.csv_file

    # 如果没有提供CSV文件，尝试查找最新的
    if not csv_file:
        comments_dir = os.path.join(DOWNLOAD_DIR, "comments")
        if os.path.exists(comments_dir):
            csv_files = [
                os.path.join(comments_dir, f)
                for f in os.listdir(comments_dir)
                if f.endswith(".csv")
            ]
            if csv_files:
                csv_file = max(csv_files, key=os.path.getmtime)

    if not csv_file or not os.path.exists(csv_file):
        raise HTTPException(status_code=404, detail="未找到评论数据文件")

    try:
        output_dir = os.path.join(DOWNLOAD_DIR, "analysis") if request.generate_report else None
        results = analyze_comments(
            csv_file=csv_file,
            output_dir=output_dir,
        )

        return {
            "analysis": results,
            "csv_file": csv_file,
            "html_report": results.get("html_report"),
            "wordcloud": results.get("wordcloud"),
        }
    except Exception as e:
        logger.exception("评论分析失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preprocess")
def preprocess_comments(request: AnalyzeRequest) -> Dict[str, Any]:
    """
    使用 Spark 预处理评论数据

    - csv_file: CSV文件路径，如果不提供则使用最近爬取的评论
    """
    csv_path = _resolve_comment_csv_path(request.csv_file)
    if not csv_path:
        raise HTTPException(status_code=404, detail="未找到评论数据文件")

    output_dir = os.path.join(DOWNLOAD_DIR, "preprocessed")
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"preprocessed_{ts}")

    # 禁止在此 with/stop：SparkSession 为进程级单例，stop 会拆掉其它并发请求共用的 Context
    try:
        preprocessor = SparkPreprocessor()
        df = preprocessor.load_data_from_csv(csv_path)
        cleaned_df = preprocessor.clean_data(df)
        tokenized_df = preprocessor.tokenize(cleaned_df)
        corpus_df = preprocessor.generate_corpus(tokenized_df)
        n = preprocessor.save_to_parquet(corpus_df, output_path)

        return {
            "success": True,
            "message": "评论数据预处理成功",
            "input_file": csv_path,
            "output_path": output_path,
            "total_records": n,
            "processed_records": n,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("评论预处理失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl-and-analyze")
def crawl_and_analyze_single_work(request: CommentCrawlRequest) -> Dict[str, Any]:
    """
    爬取单个作品评论并进行分析，保存结果到数据库
    
    - aweme_id: 作品 ID
    - max_count: 最多爬取条数，默认 500
    """
    aweme_id = request.aweme_id.strip()
    if not aweme_id:
        raise HTTPException(status_code=400, detail="aweme_id 不能为空")

    max_count = request.max_count
    if max_count < 0:
        max_count = 500

    try:
        client = _get_client()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 1. 获取作品信息（包括封面）
    logger.info(f"获取作品信息: {aweme_id}")
    cover_url = request.cover_url or ""  # 使用前端传递的封面URL作为默认值
    title = request.title or ""  # 使用前端传递的标题作为默认值
    author = ""
    
    try:
        # 使用request直接获取，避免quit()导致程序退出
        from ..lib.douyin.types import APIEndpoint
        params = {"aweme_id": aweme_id}
        resp = client.request.getJSON(APIEndpoint.AWEME_DETAIL, params)
        work_info = resp.get("aweme_detail", {})
        
        if not work_info:
            logger.warning(f"作品详情API获取失败，使用前端传递的信息: {aweme_id}")
        else:
            logger.info(f"作品信息获取成功: {aweme_id}, keys={list(work_info.keys())}")
            
            # 提取封面URL（抖音的封面在 video.cover.url_list 中）
            video = work_info.get("video", {})
            if video:
                logger.info(f"video字段: {list(video.keys())}")
                cover = video.get("cover", {})
                url_list = cover.get("url_list", [])
                logger.info(f"封面URL列表数量: {len(url_list)}")
                if url_list:
                    cover_url = url_list[0]
                    logger.info(f"封面URL: {cover_url[:80]}...")
            
            # 提取标题和作者
            title = work_info.get("desc", "") or title  # API获取失败时保留前端传递的值
            author_info = work_info.get("author", {})
            author = author_info.get("nickname", "") if author_info else ""
            
            logger.info(f"提取的信息 - 标题: {title[:50] if title else 'None'}, 作者: {author}")
    except Exception as e:
        logger.warning(f"获取作品信息失败，使用前端传递的信息: {e}")
        # 使用前端传递的信息作为备选

    # 2. 下载封面
    local_cover_path = None
    if cover_url:
        logger.info(f"下载作品封面: {aweme_id}")
        local_cover_path = download_cover(cover_url, filename=aweme_id)

    # 3. 爬取评论
    logger.info(f"开始爬取评论: {aweme_id}")
    all_comments: List[dict] = []
    cursor = 0
    page_size = 20
    max_no_data = 5
    no_data_count = 0

    while no_data_count < max_no_data:
        resp = client.fetch_comment_list(
            aweme_id=aweme_id, cursor=cursor, count=page_size
        )
        if not resp:
            no_data_count += 1
            time.sleep(0.5)
            continue

        raw_list = resp.get("comments") or []
        if not raw_list:
            no_data_count += 1
            if not resp.get("has_more", False):
                break
            cursor = resp.get("cursor", cursor)
            time.sleep(0.3)
            continue

        no_data_count = 0
        for c in raw_list:
            all_comments.append(_normalize_comment(c))
            if max_count and len(all_comments) >= max_count:
                break

        if max_count and len(all_comments) >= max_count:
            break

        if not resp.get("has_more", False):
            break
        cursor = resp.get("cursor", cursor)
        time.sleep(0.3)

    total_comments = len(all_comments)
    
    if total_comments == 0:
        return {
            "success": False,
            "message": "未爬取到任何评论",
            "aweme_id": aweme_id,
        }

    logger.info(f"爬取完成: {total_comments} 条评论")

    # 4. 保存评论到CSV
    comments_dir = os.path.join(DOWNLOAD_DIR, "comments")
    os.makedirs(comments_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"comments_{aweme_id}_{ts}.csv"
    csv_path = os.path.join(comments_dir, csv_filename)

    fieldnames = [
        "id", "nickname", "text", "create_time", "digg_count",
        "reply_count", "ip_label", "is_top", "is_hot",
    ]
    try:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in all_comments:
                w.writerow({k: row.get(k, "") for k in fieldnames})
        logger.info(f"评论已保存: {csv_path}")
    except Exception as e:
        logger.warning(f"评论 CSV 写入失败: {e}")
        csv_path = None

    # 5. 分析评论
    logger.info(f"开始分析评论: {aweme_id}")
    try:
        analysis_results = analyze_comments(comments=all_comments)
    except Exception as e:
        logger.error(f"评论分析失败: {e}")
        return {
            "success": False,
            "message": f"评论分析失败: {str(e)}",
            "aweme_id": aweme_id,
            "total_comments": total_comments,
        }

    # 6. 保存分析结果到数据库
    logger.info(f"保存分析结果到数据库: {aweme_id}")
    try:
        from backend.lib.database import db_manager
        
        # 准备数据
        sentiment = analysis_results.get("sentiment", {})
        hot_words = analysis_results.get("hot_words", [])
        location_distribution = analysis_results.get("location_distribution", [])
        time_distribution = analysis_results.get("time_distribution", {})
        user_activity = analysis_results.get("user_activity", {})
        top_comments = analysis_results.get("top_comments", [])
        topics = analysis_results.get("topics", {})
        
        data = {
            "aweme_id": aweme_id,
            "hot_id": None,  # 单个作品没有热榜ID
            "title": title or f"作品-{aweme_id}",
            "cover_url": local_cover_path or cover_url,
            "filename": csv_filename if csv_path else f"comments_{aweme_id}",
            "filepath": csv_path or "",
            "total_comments": total_comments,
            "sentiment_positive": sentiment.get("positive", 0),
            "sentiment_neutral": sentiment.get("neutral", 0),
            "sentiment_negative": sentiment.get("negative", 0),
            "sentiment_positive_rate": sentiment.get("positive_rate", 0),
            "sentiment_neutral_rate": sentiment.get("neutral_rate", 0),
            "sentiment_negative_rate": sentiment.get("negative_rate", 0),
            "hot_words": hot_words,
            "location_distribution": location_distribution,
            "time_distribution": time_distribution,
            "user_activity": user_activity,
            "top_comments": top_comments[:10],  # 只保存前10条
            "topics": topics,
            "created_time": datetime.datetime.now(),
        }
        
        # 使用正确的数据库操作方式
        sql, params = HotCommentAnalysisModel.insert_sql(data)
        with db_manager.get_cursor() as cursor:
            cursor.execute(sql, params)
        
        logger.info(f"✓ 分析结果已保存到数据库: {aweme_id}")
        
    except Exception as e:
        logger.error(f"保存分析结果到数据库失败: {e}", exc_info=True)
        # 不影响返回结果，只是记录错误

    return {
        "success": True,
        "message": "爬取和分析完成",
        "aweme_id": aweme_id,
        "title": title,
        "author": author,
        "cover_url": local_cover_path or cover_url,
        "total_comments": total_comments,
        "csv_file": csv_path,
        "analysis": analysis_results,
    }
