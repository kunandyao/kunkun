"""
MySQL 数据库连接管理（带连接池）
"""

import pymysql
from dbutils.pooled_db import PooledDB
from typing import Optional, Any
from contextlib import contextmanager
from loguru import logger

from .config import db_config


class DatabaseManager:
    """数据库管理器（单例模式 + 连接池）"""
    
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            import threading
            if cls._lock is None:
                cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            # 初始化连接池
            self._pool = PooledDB(
                creator=pymysql,
                maxconnections=20,  # 最大连接数
                mincached=5,  # 初始化时创建的空闲连接数
                maxcached=10,  # 连接池最大空闲连接数
                blocking=True,  # 连接池满时是否阻塞
                host=db_config.connection_dict.get('host', 'localhost'),
                port=db_config.connection_dict.get('port', 3306),
                user=db_config.connection_dict.get('user', 'root'),
                password=db_config.connection_dict.get('password', ''),
                database=db_config.connection_dict.get('database', 'douyin_hot_comments'),
                charset=db_config.connection_dict.get('charset', 'utf8mb4'),
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,  # 自动提交
            )
            logger.info(f"MySQL 连接池初始化成功 (max=20, min=5)")
    
    def connect(self) -> Any:
        """从连接池获取连接"""
        try:
            connection = self._pool.connection()
            return connection
        except Exception as e:
            logger.error(f"从连接池获取连接失败：{e}")
            raise
    
    def close(self):
        """关闭连接池"""
        if self._pool:
            # PooledDB 没有直接的 close 方法，这里只是清理引用
            self._pool = None
            logger.info("MySQL 连接池已关闭")
    
    @contextmanager
    def get_cursor(self):
        """获取数据库游标（上下文管理器）"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败，已回滚：{e}")
            raise
        finally:
            cursor.close()
    
    def execute(self, sql: str, params: Optional[tuple] = None) -> int:
        """执行 SQL 语句（INSERT/UPDATE/DELETE）"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.rowcount
    
    def fetch_one(self, sql: str, params: Optional[tuple] = None) -> Optional[dict]:
        """查询单条记录"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone()
    
    def fetch_all(self, sql: str, params: Optional[tuple] = None) -> list:
        """查询多条记录"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            self.connect()
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败：{e}")
            return False


# 全局数据库管理器实例
db_manager = DatabaseManager()
