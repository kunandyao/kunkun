"""
定时任务管理器

用于管理热榜评论的定时爬取任务
"""

import threading
import time
import datetime
from typing import Optional, Callable
from loguru import logger


class SchedulerManager:
    """定时任务管理器（单例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.scheduler_thread: Optional[threading.Thread] = None
            self.stop_event = threading.Event()
            self.is_running = False
            self.last_run_time: Optional[datetime.datetime] = None
            self.next_run_time: Optional[datetime.datetime] = None
            self.total_runs = 0
            self.total_comments = 0
            self._task_func: Optional[Callable] = None
    
    def start(
        self,
        task_func: Callable,
        interval_hours: int = 2,
        video_count: int = 10,
        comments_per_video: int = 100,
        **task_kwargs
    ) -> bool:
        """
        启动定时任务
        
        Args:
            task_func: 爬取任务函数
            interval_hours: 间隔小时数
            video_count: 视频数量
            comments_per_video: 每视频评论数
            **task_kwargs: 传递给任务函数的其他参数
            
        Returns:
            bool: 是否启动成功
        """
        with self._lock:
            if self.is_running:
                logger.warning("定时任务已在运行中")
                return False
            
            self.stop_event.clear()
            self.is_running = True
            self._task_func = task_func
            
            # 设置任务参数
            self.interval_hours = interval_hours
            self.video_count = video_count
            self.comments_per_video = comments_per_video
            self.task_kwargs = task_kwargs
            
            # 启动线程
            self.scheduler_thread = threading.Thread(
                target=self._run_scheduler,
                daemon=True,
                args=(interval_hours, video_count, comments_per_video, task_kwargs)
            )
            self.scheduler_thread.start()
            
            logger.info(f"定时任务已启动（间隔：{interval_hours}小时）")
            return True
    
    def stop(self) -> bool:
        """停止定时任务"""
        with self._lock:
            if not self.is_running:
                logger.warning("定时任务未运行")
                return False
            
            self.stop_event.set()
            self.is_running = False
            
            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=5)
                self.scheduler_thread = None
            
            logger.info("定时任务已停止")
            return True
    
    def _run_scheduler(self, interval_hours: int, video_count: int, comments_per_video: int, task_kwargs: dict):
        """定时任务执行器"""
        logger.info("定时任务执行器已启动")
        
        while not self.stop_event.is_set():
            try:
                # 执行爬取任务
                if self._task_func:
                    logger.info(f"开始执行爬取任务：视频数={video_count}, 评论数={comments_per_video}")
                    result = self._task_func(video_count, comments_per_video, **task_kwargs)
                    
                    if result and result.get('success'):
                        self.total_runs += 1
                        self.total_comments += result.get('total_comments', 0)
                        self.last_run_time = datetime.datetime.now()
                        logger.info(f"爬取成功：{result.get('total_comments')} 条评论")
                    else:
                        logger.error(f"爬取失败：{result.get('error', '未知错误')}")
                
                # 计算下次运行时间
                self.next_run_time = datetime.datetime.now() + datetime.timedelta(hours=interval_hours)
                logger.info(f"下次爬取时间：{self.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 等待指定时间
                wait_seconds = interval_hours * 3600
                self.stop_event.wait(wait_seconds)
                
            except Exception as e:
                logger.error(f"定时任务执行异常：{e}", exc_info=True)
                # 即使出错也继续等待下次执行
                self.stop_event.wait(60)
        
        logger.info("定时任务执行器已退出")
    
    def get_status(self) -> dict:
        """获取定时任务状态"""
        return {
            "is_running": self.is_running,
            "interval_hours": getattr(self, 'interval_hours', 0),
            "video_count": getattr(self, 'video_count', 0),
            "comments_per_video": getattr(self, 'comments_per_video', 0),
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "next_run_time": self.next_run_time.isoformat() if self.next_run_time else None,
            "total_runs": self.total_runs,
            "total_comments": self.total_comments,
        }


# 全局定时任务管理器实例
scheduler_manager = SchedulerManager()
