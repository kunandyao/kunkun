import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.lib.database import db_manager

def check_data():
    try:
        # 检查热榜表
        sql = "SELECT COUNT(*) as count FROM hot_search"
        with db_manager.get_cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()
        print(f"hot_search 表共有 {result['count']} 条记录")
        
        if result['count'] > 0:
            sql = "SELECT * FROM hot_search ORDER BY crawl_time DESC LIMIT 5"
            with db_manager.get_cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
            print("\n最新的 5 条热榜记录:")
            for row in rows:
                print(f"  排名: {row['rank']}, 标题: {row['title']}, video_id: {row['video_id']}")
        
        # 检查分析表
        sql = "SELECT COUNT(*) as count FROM hot_comment_analysis"
        with db_manager.get_cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()
        print(f"\nhot_comment_analysis 表共有 {result['count']} 条记录")
        
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_data()
