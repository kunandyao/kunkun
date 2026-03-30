"""
数据库迁移脚本：为 hot_search 表添加 cover_url 字段

使用方法：
    python -m backend.lib.database.migrate_add_cover_url
"""

from loguru import logger
from .connection import db_manager


def add_cover_url_column():
    """为 hot_search 表添加 cover_url 字段"""
    try:
        with db_manager.get_cursor() as cursor:
            # 检查字段是否已存在
            cursor.execute("""
                SELECT COUNT(*) as cnt 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'hot_search' 
                AND COLUMN_NAME = 'cover_url'
            """)
            result = cursor.fetchone()
            
            if result['cnt'] > 0:
                logger.info("✓ cover_url 字段已存在，无需迁移")
                return True
            
            # 添加字段
            cursor.execute("""
                ALTER TABLE hot_search 
                ADD COLUMN cover_url VARCHAR(500) COMMENT '封面 URL' 
                AFTER video_id
            """)
            
            logger.info("✓ 成功为 hot_search 表添加 cover_url 字段")
            return True
            
    except Exception as e:
        logger.error(f"添加字段失败：{e}")
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("开始数据库迁移：添加 cover_url 字段")
    logger.info("=" * 60)
    
    success = add_cover_url_column()
    
    if success:
        logger.info("=" * 60)
        logger.info("✓ 数据库迁移完成")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error("✗ 数据库迁移失败")
        logger.error("=" * 60)
