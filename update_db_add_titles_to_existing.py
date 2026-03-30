import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.lib.database import db_manager

def update_existing_titles():
    try:
        # 获取所有没有标题的分析记录
        sql_get = """
        SELECT id, aweme_id 
        FROM hot_comment_analysis 
        WHERE title IS NULL OR title = ''
        """
        
        with db_manager.get_cursor() as cursor:
            cursor.execute(sql_get)
            rows = cursor.fetchall()
        
        print(f"找到 {len(rows)} 条没有标题的记录")
        
        updated_count = 0
        for row in rows:
            analysis_id = row['id']
            aweme_id = row['aweme_id']
            
            # 从热榜表查找对应的标题
            sql_title = """
            SELECT title 
            FROM hot_search 
            WHERE video_id = %s 
            ORDER BY crawl_time DESC 
            LIMIT 1
            """
            
            with db_manager.get_cursor() as cursor:
                cursor.execute(sql_title, (aweme_id,))
                title_result = cursor.fetchone()
            
            if title_result and title_result.get('title'):
                title = title_result['title']
                # 更新标题
                sql_update = "UPDATE hot_comment_analysis SET title = %s WHERE id = %s"
                with db_manager.get_cursor() as cursor:
                    cursor.execute(sql_update, (title, analysis_id))
                print(f"  更新 ID {analysis_id}: {title}")
                updated_count += 1
            else:
                print(f"  未找到 ID {analysis_id} (aweme_id: {aweme_id}) 的标题")
        
        print(f"\n✅ 完成！共更新了 {updated_count} 条记录")
        
        # 验证
        sql_check = "SELECT id, aweme_id, title FROM hot_comment_analysis ORDER BY id DESC LIMIT 5"
        with db_manager.get_cursor() as cursor:
            cursor.execute(sql_check)
            latest = cursor.fetchall()
        
        print("\n最新的 5 条记录:")
        for item in latest:
            print(f"  ID: {item['id']}, 标题: {item['title'] or '(无)'}")
            
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_existing_titles()
