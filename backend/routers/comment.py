"""
评论接口

提供作品评论列表（单页）与多页爬取（导出 CSV）。
支持浏览器自动化爬取和数据分析功能。
"""

import csv
import datetime
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from ..constants import DOWNLOAD_DIR
from ..lib.cookies import CookieManager
from ..lib.douyin.client import DouyinClient
from ..lib.douyin.request import Request
from ..lib.comment_analyzer import CommentAnalyzer, analyze_comments
from ..settings import settings

router = APIRouter(prefix="/api/comment", tags=["评论"])


# ============================================================================
# 请求/响应模型
# ============================================================================


class CommentCrawlRequest(BaseModel):
    """评论爬取请求"""

    aweme_id: str
    max_count: int = 500  # 最多爬取条数，0 表示不限制（按页直到 has_more=0）


class BrowserCrawlRequest(BaseModel):
    """浏览器自动化爬取请求"""

    aweme_id: str
    video_url: Optional[str] = None
    max_count: Optional[int] = 500


class AnalyzeRequest(BaseModel):
    """评论分析请求"""

    csv_file: Optional[str] = None
    generate_report: bool = True


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
    多页爬取评论，返回列表并可选导出 CSV

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

    # 导出 CSV 到下载目录
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
    except Exception as e:
        logger.warning("评论 CSV 写入失败: {}", e)
        csv_path = None

    return {
        "comments": all_comments,
        "total": len(all_comments),
        "file": csv_path,
        "filename": csv_filename if csv_path else None,
    }


@router.post("/crawl-browser")
def crawl_comments_browser(request: BrowserCrawlRequest) -> Dict[str, Any]:
    """
    使用浏览器自动化爬取评论（API方式的备用方案）

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

        return {
            "comments": result["comments"],
            "total": result["total"],
            "file": result["output_file"],
            "method": "browser",
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


@router.get("/analysis-report")
def get_analysis_report(report_type: str = "html") -> Dict[str, Any]:
    """
    获取最新的分析报告

    - report_type: 报告类型 (html, wordcloud)
    """
    analysis_dir = os.path.join(DOWNLOAD_DIR, "analysis")
    if not os.path.exists(analysis_dir):
        raise HTTPException(status_code=404, detail="未找到分析报告")

    if report_type == "html":
        files = [f for f in os.listdir(analysis_dir) if f.startswith("comment_analysis") and f.endswith(".html")]
    elif report_type == "wordcloud":
        files = [f for f in os.listdir(analysis_dir) if f.startswith("comment_wordcloud") and f.endswith(".png")]
    else:
        raise HTTPException(status_code=400, detail="不支持的报告类型")

    if not files:
        raise HTTPException(status_code=404, detail=f"未找到{report_type}报告")

    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(analysis_dir, f)))
    file_path = os.path.join(analysis_dir, latest_file)

    return {
        "file_path": file_path,
        "filename": latest_file,
        "created_at": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
    }
