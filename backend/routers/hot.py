"""
热搜路由模块

提供抖音热榜相关的 API 接口。
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Optional, Any
from backend.lib.douyin import DouyinHotFetcher
from backend.lib.douyin.hot_comment import DouyinHotCommentFetcher
from backend.lib.cookies import CookieManager
from backend.settings import settings
from loguru import logger

router = APIRouter(prefix="/api/hot", tags=["hot"])


@router.get("/douyin", summary="获取抖音热榜")
async def get_douyin_hot(proxy_url: Optional[str] = None, max_retries: int = 2) -> Dict:
    """
    获取抖音热榜数据
    
    - **proxy_url**: 可选的代理URL
    - **max_retries**: 最大重试次数，默认为2
    
    返回抖音热榜数据，格式为：
    ```json
    {
        "标题": {
            "ranks": [排名],
            "url": "PC端链接",
            "mobileUrl": "移动端链接",
            "hotValue": "热度值"
        }
    }
    ```
    """
    try:
        fetcher = DouyinHotFetcher(proxy_url=proxy_url)
        douyin_data = fetcher.fetch_douyin_hot(max_retries=max_retries)
        
        if douyin_data:
            return douyin_data
        else:
            raise HTTPException(status_code=500, detail="获取抖音热榜失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取抖音热榜失败: {str(e)}")


@router.post("/douyin/save", summary="保存抖音热榜")
async def save_douyin_hot(output_dir: str = "output") -> Dict:
    """
    保存抖音热榜到文本文件和HTML报告
    
    - **output_dir**: 输出目录，默认为"output"
    
    返回保存结果，包含文本文件和HTML报告的路径。
    """
    try:
        fetcher = DouyinHotFetcher()
        douyin_data = fetcher.fetch_douyin_hot()
        
        if douyin_data:
            txt_file = fetcher.save_to_txt(douyin_data, output_dir=output_dir)
            html_file = fetcher.generate_html_report(douyin_data, output_dir=output_dir)
            
            return {
                "success": True,
                "txt_file": txt_file,
                "html_file": html_file,
                "count": len(douyin_data)
            }
        else:
            raise HTTPException(status_code=500, detail="获取抖音热榜失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存抖音热榜失败：{str(e)}")


@router.post("/douyin/refresh-db", summary="刷新抖音热榜到数据库")
async def refresh_douyin_hot_to_db() -> Dict[str, Any]:
    """
    刷新抖音热榜数据并保存到数据库
    
    获取最新的抖音热榜数据，提取视频 ID，并保存到数据库的热搜表中。
    同时会保存每个热榜话题对应的第一个视频信息到 videos 表。
    
    返回：
    - success: 是否成功
    - count: 保存的热榜数据条数
    - videos_count: 保存的视频信息条数
    - message: 提示信息
    """
    try:
        # 使用 DouyinHotCommentFetcher 来获取热榜并保存
        cookie = (settings.get("cookie") or "").strip()
        if not CookieManager.validate_cookie(cookie):
            raise HTTPException(status_code=400, detail="Cookie 无效或未配置，请在设置中填写 Cookie")
        
        ua = (settings.get("userAgent") or "").strip()
        fetcher = DouyinHotCommentFetcher(cookie=cookie, user_agent=ua if ua else None)
        
        # 获取热榜数据
        hot_videos = fetcher.get_hot_videos(count=30)
        
        if not hot_videos:
            raise HTTPException(status_code=500, detail="获取热榜数据失败")
        
        # 保存到数据库
        fetcher.save_hot_search_to_db(hot_videos)
        
        # 尝试获取每个热榜话题的视频 ID 并保存视频信息
        videos_saved = 0
        for video in hot_videos[:10]:  # 只处理前 10 个，避免耗时太长
            try:
                if video.get('url'):
                    aweme_id = fetcher.get_video_from_hot_url(video['url'], video['title'])
                    if aweme_id:
                        video_info = {
                            "aweme_id": aweme_id,
                            "title": video['title'],
                            "source": "hot_search",
                            "hot_rank": video.get('rank', 0),
                            "hot_value": video.get('hot_value', ''),
                        }
                        fetcher.save_video_info_to_db(video_info)
                        videos_saved += 1
            except Exception as e:
                logger.warning(f"保存视频信息失败 {video.get('title')}: {e}")
                continue
        
        logger.info(f"热榜数据已刷新到数据库：{len(hot_videos)} 条热榜，{videos_saved} 个视频")
        
        return {
            "success": True,
            "count": len(hot_videos),
            "videos_count": videos_saved,
            "message": f"已刷新 {len(hot_videos)} 条热榜数据，{videos_saved} 个视频信息"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新热榜到数据库失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"刷新热榜失败：{str(e)}")


@router.get("/douyin/from-db", summary="从数据库获取抖音热榜")
async def get_douyin_hot_from_db(limit: int = 30) -> Dict[str, Any]:
    """
    从数据库获取抖音热榜数据
    
    - **limit**: 返回多少条数据，默认 30 条
    
    如果数据库中没有数据或数据过期（超过 2 小时），会返回提示。
    """
    try:
        from backend.lib.database import db_manager
        from backend.lib.database.models import HotSearchModel
        
        # 从数据库查询最新的热榜数据
        with db_manager.get_cursor() as cursor:
            # 获取最新一次的爬取时间
            cursor.execute("""
                SELECT DISTINCT crawl_time 
                FROM hot_search 
                ORDER BY crawl_time DESC 
                LIMIT 1
            """)
            latest_result = cursor.fetchone()
            
            if not latest_result:
                return {
                    "success": False,
                    "from_db": False,
                    "message": "数据库中暂无热榜数据，请先刷新",
                    "data": []
                }
            
            latest_time = latest_result.get('crawl_time')
            
            # 检查数据是否过期（超过 2 小时）
            import datetime
            time_diff = datetime.datetime.now() - latest_time
            is_stale = time_diff.total_seconds() > 2 * 3600
            
            # 获取该时间点的所有热榜数据
            cursor.execute("""
                SELECT id, `rank`, title, hot_value, video_id, cover_url, crawl_time
                FROM hot_search
                WHERE crawl_time = %s
                ORDER BY `rank`
                LIMIT %s
            """, (latest_time, limit))
            
            rows = cursor.fetchall()
            
            hot_list = []
            for row in rows:
                hot_list.append({
                    "id": row['id'],
                    "rank": row['rank'],
                    "title": row['title'],
                    "hot_value": row['hot_value'],
                    "url": f"https://www.douyin.com/hot/{row['rank']}",  # 临时 URL
                    "mobileUrl": f"https://www.douyin.com/hot/{row['rank']}",
                    "video_id": row['video_id'],
                    "cover_url": row['cover_url'],  # 添加封面图 URL
                    "crawl_time": row['crawl_time'].isoformat() if row['crawl_time'] else None,
                })
            
            return {
                "success": True,
                "from_db": True,
                "is_stale": is_stale,
                "latest_time": latest_time.isoformat(),
                "time_ago": f"{int(time_diff.total_seconds() / 60)}分钟前",
                "data": hot_list
            }
            
    except Exception as e:
        logger.error(f"从数据库获取热榜失败：{e}", exc_info=True)
        return {
            "success": False,
            "from_db": False,
            "error": str(e),
            "data": []
        }


@router.get("/douyin/history", summary="获取热榜历史数据（用于热度趋势图）")
async def get_douyin_hot_history(title_limit: int = 10) -> Dict[str, Any]:
    """
    获取热榜历史数据，用于展示热度趋势图
    
    - **title_limit**: 返回前多少个热门话题的历史数据，默认 10 个
    
    返回每个热门话题在不同时间点的热度值。
    """
    try:
        from backend.lib.database import db_manager
        
        with db_manager.get_cursor() as cursor:
            # 1. 先获取最新热榜的前 N 个话题
            cursor.execute("""
                SELECT DISTINCT crawl_time 
                FROM hot_search 
                ORDER BY crawl_time DESC 
                LIMIT 1
            """)
            latest_result = cursor.fetchone()
            
            if not latest_result:
                return {
                    "success": False,
                    "message": "数据库中暂无热榜数据",
                    "data": []
                }
            
            latest_time = latest_result.get('crawl_time')
            
            # 获取最新热榜的前 N 个话题
            cursor.execute("""
                SELECT title 
                FROM hot_search
                WHERE crawl_time = %s
                ORDER BY `rank`
                LIMIT %s
            """, (latest_time, title_limit))
            
            top_titles = [row['title'] for row in cursor.fetchall()]
            
            if not top_titles:
                return {
                    "success": False,
                    "message": "没有找到热门话题",
                    "data": []
                }
            
            # 2. 获取这些话题的所有历史数据
            placeholders = ', '.join(['%s'] * len(top_titles))
            cursor.execute(f"""
                SELECT title, hot_value, crawl_time
                FROM hot_search
                WHERE title IN ({placeholders})
                ORDER BY crawl_time, `rank`
            """, top_titles)
            
            rows = cursor.fetchall()
            
            # 3. 整理数据格式
            history_data = {}
            all_times = set()
            
            for row in rows:
                title = row['title']
                hot_value = row['hot_value']
                crawl_time = row['crawl_time'].isoformat() if row['crawl_time'] else ''
                
                if crawl_time:
                    all_times.add(crawl_time)
                
                if title not in history_data:
                    history_data[title] = {}
                
                history_data[title][crawl_time] = hot_value
            
            # 4. 整理成 ECharts 需要的格式
            sorted_times = sorted(list(all_times))
            series = []
            
            for title in top_titles:
                if title in history_data:
                    data = []
                    for time in sorted_times:
                        hot_val = history_data[title].get(time, None)
                        if hot_val:
                            # 尝试将热度值转换为数字
                            try:
                                hot_val_num = float(hot_val.replace('万', '0000').replace('w', '0000').replace('W', '0000'))
                                data.append(hot_val_num)
                            except:
                                data.append(None)
                        else:
                            data.append(None)
                    
                    series.append({
                        "name": title,
                        "data": data
                    })
            
            return {
                "success": True,
                "times": sorted_times,
                "series": series
            }
            
    except Exception as e:
        logger.error(f"获取热榜历史数据失败：{e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": []
        }
