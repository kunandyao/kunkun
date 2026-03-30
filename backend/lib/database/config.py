"""
MySQL 数据库配置
"""

from pydantic import BaseModel
from typing import Optional


class MySQLConfig(BaseModel):
    """MySQL 数据库配置"""
    
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "ROOT"  # 本地数据库密码
    database: str = "douyin_hot_comments"
    charset: str = "utf8mb4"
    
    @property
    def connection_url(self) -> str:
        """获取数据库连接 URL"""
        return (
            f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"
        )
    
    @property
    def connection_dict(self) -> dict:
        """获取数据库连接参数字典"""
        import pymysql.cursors
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "charset": self.charset,
            "cursorclass": pymysql.cursors.DictCursor
        }


# 全局数据库配置实例
db_config = MySQLConfig()
