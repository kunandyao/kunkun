import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.lib.database import db_manager

def add_title_column():
    try:
        # 先检查列是否存在
        sql_check_exists = "SHOW COLUMNS FROM hot_comment_analysis LIKE 'title'"
        with db_manager.get_cursor() as cursor:
            cursor.execute(sql_check_exists)
            exists = cursor.fetchone()
        
        if exists:
            print("ℹ️ title 列已存在")
        else:
            sql = """
            ALTER TABLE hot_comment_analysis 
            ADD COLUMN title VARCHAR(500) COMMENT '热搜标题' 
            AFTER aweme_id
            """
            with db_manager.get_cursor() as cursor:
                cursor.execute(sql)
            print("✅ 成功添加 title 列")
        
        # 验证
        sql_check = "DESCRIBE hot_comment_analysis"
        with db_manager.get_cursor() as cursor:
            cursor.execute(sql_check)
            columns = cursor.fetchall()
        print("\n当前表结构:")
        for col in columns:
            print(f"  {col['Field']} - {col['Type']}")
            
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_title_column()
