"""
数据库初始化脚本

使用方法：
    python -m backend.lib.database.init
"""

import pymysql
from loguru import logger

from .config import db_config
from .models import (
    HotSearchModel, VideoModel, CommentModel, 
    SchedulerHistoryModel, HotCommentAnalysisModel
)


def create_database():
    """创建数据库（如果不存在）"""
    try:
        # 先连接到 MySQL 服务器（不指定数据库）
        connection = pymysql.connect(
            host=db_config.host,
            port=db_config.port,
            user=db_config.user,
            password=db_config.password,
            charset=db_config.charset
        )
        
        with connection.cursor() as cursor:
            # 创建数据库
            cursor.execute(f"""
                CREATE DATABASE IF NOT EXISTS {db_config.database}
                CHARACTER SET {db_config.charset}
                COLLATE utf8mb4_unicode_ci
            """)
            logger.info(f"数据库 '{db_config.database}' 创建成功（如果不存在）")
        
        connection.close()
        return True
    except Exception as e:
        logger.error(f"创建数据库失败：{e}")
        return False


def init_tables():
    """初始化所有数据表"""
    try:
        from .connection import db_manager
        
        # 创建所有表
        tables = [
            ("hot_search", HotSearchModel.create_table),
            ("videos", VideoModel.create_table),
            ("comments", CommentModel.create_table),
            ("scheduler_history", SchedulerHistoryModel.create_table),
            ("hot_comment_analysis", HotCommentAnalysisModel.create_table),
        ]
        
        for table_name, create_func in tables:
            with db_manager.get_cursor() as cursor:
                cursor.execute(create_func())
                logger.info(f"数据表 '{table_name}' 创建成功")
        
        logger.info("=" * 60)
        logger.info("✓ 数据库初始化完成")
        logger.info(f"  - 数据库：{db_config.database}")
        logger.info(f"  - 主机：{db_config.host}:{db_config.port}")
        logger.info(f"  - 用户：{db_config.user}")
        logger.info("=" * 60)
        
        return True
    except Exception as e:
        logger.error(f"初始化数据表失败：{e}")
        return False


def drop_all_tables():
    """删除所有数据表（危险操作！）"""
    try:
        from .connection import db_manager
        
        tables = ["hot_search", "videos", "comments", "scheduler_history", "hot_comment_analysis"]
        
        for table_name in tables:
            with db_manager.get_cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.info(f"数据表 '{table_name}' 已删除")
        
        logger.warning("所有数据表已删除")
        return True
    except Exception as e:
        logger.error(f"删除数据表失败：{e}")
        return False


def test_connection():
    """测试数据库连接"""
    from .connection import db_manager
    
    try:
        if db_manager.test_connection():
            logger.info("✓ 数据库连接测试成功")
            return True
        else:
            logger.error("✗ 数据库连接测试失败")
            return False
    except Exception as e:
        logger.error(f"✗ 数据库连接测试失败：{e}")
        return False


def main():
    """主函数"""
    import sys
    
    print("=" * 60)
    print("抖音热榜评论 MySQL 数据库初始化工具")
    print("=" * 60)
    print()
    print(f"数据库配置:")
    print(f"  - 主机：{db_config.host}:{db_config.port}")
    print(f"  - 用户：{db_config.user}")
    print(f"  - 数据库：{db_config.database}")
    print()
    
    # 解析命令行参数
    action = "init"
    if len(sys.argv) > 1:
        action = sys.argv[1]
    
    if action == "init":
        # 初始化数据库
        print("正在初始化数据库...")
        if create_database():
            if init_tables():
                print()
                print("✓ 数据库初始化成功！")
                print()
                print("下一步:")
                print("1. 修改后端配置，启用 MySQL 存储")
                print("2. 重启后端服务")
                print("3. 在 frontend 中配置数据库连接")
            else:
                print("✗ 初始化数据表失败")
                sys.exit(1)
        else:
            print("✗ 创建数据库失败")
            sys.exit(1)
    
    elif action == "test":
        # 测试连接
        print("正在测试数据库连接...")
        if test_connection():
            print("✓ 数据库连接正常")
        else:
            print("✗ 数据库连接失败")
            sys.exit(1)
    
    elif action == "drop":
        # 删除所有表
        confirm = input("⚠️  警告：这将删除所有数据表！输入 'yes' 确认：")
        if confirm.lower() == 'yes':
            if drop_all_tables():
                print("✓ 所有数据表已删除")
            else:
                print("✗ 删除数据表失败")
                sys.exit(1)
        else:
            print("操作已取消")
    
    else:
        print("用法:")
        print("  python -m backend.lib.database.init [init|test|drop]")
        print()
        print("命令说明:")
        print("  init  - 初始化数据库和表")
        print("  test  - 测试数据库连接")
        print("  drop  - 删除所有数据表（危险！）")
        sys.exit(1)


if __name__ == "__main__":
    main()
