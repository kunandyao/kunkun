"""
数据库迁移脚本 - 添加用户系统

执行此脚本将创建用户表并初始化默认管理员账户。

使用方法:
    python -m backend.lib.database.migrations.add_user_system
"""

from backend.lib.database import db_manager
from backend.lib.database.models import UserModel
from backend.lib.auth import get_password_hash


def migrate():
    """执行数据库迁移"""
    print("=" * 60)
    print("开始执行数据库迁移 - 用户系统")
    print("=" * 60)
    
    conn = None
    cursor = None
    
    try:
        conn = db_manager.connect()
        cursor = conn.cursor()
        
        # 禁用外键检查
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # 删除已存在的表（避免字段不匹配）
        print("\n🗑️  检查并清理已存在的表...")
        cursor.execute("DROP TABLE IF EXISTS reports")
        cursor.execute("DROP TABLE IF EXISTS alert_configs")
        cursor.execute("DROP TABLE IF EXISTS monitor_configs")
        cursor.execute("DROP TABLE IF EXISTS tasks")
        cursor.execute("DROP TABLE IF EXISTS api_logs")
        cursor.execute("DROP TABLE IF EXISTS notifications")
        cursor.execute("DROP TABLE IF EXISTS user_profiles")
        cursor.execute("DROP TABLE IF EXISTS users")
        conn.commit()
        
        # 启用外键检查
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        print("✓ 已清理已存在的表")
        
        # 创建用户表
        print("\n📋 正在创建 users 表...")
        cursor.execute(UserModel.create_table())
        print("✓ users 表创建成功")
        
        # 创建通知表
        print("\n📋 正在创建 notifications 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '通知 ID',
                user_id INT NOT NULL COMMENT '用户 ID',
                title VARCHAR(200) NOT NULL COMMENT '通知标题',
                content TEXT COMMENT '通知内容',
                type ENUM('alert', 'system', 'task') NOT NULL COMMENT '通知类型',
                is_read BOOLEAN DEFAULT FALSE COMMENT '是否已读',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                INDEX idx_user_id (user_id),
                INDEX idx_is_read (is_read),
                INDEX idx_type (type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户通知表';
        """)
        print("✓ notifications 表创建成功")
        
        # 创建 API 日志表
        print("\n📋 正在创建 api_logs 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_logs (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '日志 ID',
                user_id INT COMMENT '用户 ID',
                endpoint VARCHAR(200) COMMENT 'API 端点',
                method VARCHAR(10) COMMENT '请求方法',
                status_code INT COMMENT '状态码',
                ip_address VARCHAR(50) COMMENT 'IP 地址',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                INDEX idx_user_id (user_id),
                INDEX idx_endpoint (endpoint),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API 日志表';
        """)
        print("✓ api_logs 表创建成功")
        
        # 创建任务历史表
        print("\n📋 正在创建 tasks 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '任务 ID',
                user_id INT NOT NULL COMMENT '用户 ID',
                type VARCHAR(50) NOT NULL COMMENT '任务类型',
                target TEXT COMMENT '任务目标',
                status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending' COMMENT '任务状态',
                progress INT DEFAULT 0 COMMENT '进度（0-100）',
                result_count INT DEFAULT 0 COMMENT '结果数量',
                error_message TEXT COMMENT '错误信息',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX idx_user_id (user_id),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务历史表';
        """)
        print("✓ tasks 表创建成功")
        
        # 创建监测配置表
        print("\n📋 正在创建 monitor_configs 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitor_configs (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '配置 ID',
                user_id INT NOT NULL COMMENT '用户 ID',
                name VARCHAR(100) NOT NULL COMMENT '配置名称',
                type ENUM('keyword', 'topic', 'blogger', 'video') NOT NULL COMMENT '监测类型',
                target TEXT NOT NULL COMMENT '监测目标',
                filters JSON COMMENT '过滤条件',
                enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX idx_user_id (user_id),
                INDEX idx_type (type),
                INDEX idx_enabled (enabled)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='舆情监测配置表';
        """)
        print("✓ monitor_configs 表创建成功")
        
        # 创建预警配置表
        print("\n📋 正在创建 alert_configs 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_configs (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '预警配置 ID',
                user_id INT NOT NULL COMMENT '用户 ID',
                name VARCHAR(100) NOT NULL COMMENT '配置名称',
                rule_type ENUM('sentiment', 'keyword', 'volume') NOT NULL COMMENT '规则类型',
                config_data JSON NOT NULL COMMENT '触发条件',
                notification_method ENUM('email', 'sms', 'in_app') DEFAULT 'in_app' COMMENT '通知方式',
                enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                INDEX idx_user_id (user_id),
                INDEX idx_rule_type (rule_type),
                INDEX idx_enabled (enabled)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预警配置表';
        """)
        print("✓ alert_configs 表创建成功")
        
        # 创建报告表
        print("\n📋 正在创建 reports 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '报告 ID',
                user_id INT NOT NULL COMMENT '用户 ID',
                title VARCHAR(200) NOT NULL COMMENT '报告标题',
                report_type ENUM('sentiment', 'hot_words', 'trend') NOT NULL COMMENT '报告类型',
                content JSON COMMENT '报告内容',
                file_path VARCHAR(500) COMMENT '文件路径',
                status ENUM('generating', 'completed', 'failed') DEFAULT 'generating' COMMENT '状态',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                INDEX idx_user_id (user_id),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='舆情报告表';
        """)
        print("✓ reports 表创建成功")
        
        conn.commit()
        
        # 创建默认管理员账户
        print("\n👤 正在创建默认管理员账户...")
        try:
            cursor.execute("""
                INSERT INTO users (username, password_hash, email, role, status, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (
                'admin',
                get_password_hash('admin123'),
                'admin@example.com',
                'admin',
                'active'
            ))
            conn.commit()
            print("✓ 默认管理员账户创建成功")
            print("\n" + "=" * 60)
            print("🎉 默认管理员账户信息：")
            print("   用户名：admin")
            print("   密码：admin123")
            print("   ⚠️  请在首次登录后立即修改密码！")
            print("=" * 60)
        except Exception as e:
            if "Duplicate entry" in str(e):
                print("⚠️  默认管理员账户已存在，跳过创建")
            else:
                raise
        
        print("\n" + "=" * 60)
        print("✅ 数据库迁移完成！")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 迁移失败：{e}")
        print("=" * 60)
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    migrate()
