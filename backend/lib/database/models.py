"""
数据库模型定义
"""

from datetime import datetime
from typing import Optional, List, Dict, Any


class UserModel:
    """用户数据模型"""
    
    @staticmethod
    def create_table() -> str:
        return """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户 ID',
            username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
            password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
            email VARCHAR(100) UNIQUE COMMENT '邮箱',
            phone VARCHAR(20) UNIQUE COMMENT '手机号',
            avatar VARCHAR(500) COMMENT '头像 URL',
            role ENUM('user', 'admin') DEFAULT 'user' COMMENT '角色',
            status ENUM('active', 'inactive', 'banned') DEFAULT 'active' COMMENT '状态',
            last_login DATETIME COMMENT '最后登录时间',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            INDEX idx_username (username),
            INDEX idx_email (email),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
        """
    
    @staticmethod
    def insert_sql(username: str, password_hash: str, email: str = None) -> tuple:
        """生成插入用户的 SQL 语句"""
        sql = """
        INSERT INTO users (username, password_hash, email, status, created_at)
        VALUES (%s, %s, %s, 'active', NOW())
        """
        return sql, (username, password_hash, email)
    
    @staticmethod
    def update_last_login_sql(user_id: int) -> tuple:
        """更新最后登录时间"""
        sql = "UPDATE users SET last_login = NOW() WHERE id = %s"
        return sql, (user_id,)


class HotSearchModel:
    """热榜数据模型"""
    
    @staticmethod
    def create_table() -> str:
        return """
        CREATE TABLE IF NOT EXISTS hot_search (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
            `rank` INT NOT NULL COMMENT '排名',
            title VARCHAR(500) NOT NULL COMMENT '标题',
            hot_value VARCHAR(50) COMMENT '热度值',
            video_id VARCHAR(50) COMMENT '热榜话题 ID',
            aweme_id VARCHAR(50) COMMENT '真正的视频 ID',
            cover_url VARCHAR(500) COMMENT '封面 URL',
            crawl_time DATETIME NOT NULL COMMENT '爬取时间',
            INDEX idx_rank (`rank`),
            INDEX idx_crawl_time (crawl_time),
            INDEX idx_video_id (video_id),
            INDEX idx_aweme_id (aweme_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='热榜数据表';
        """
    
    @staticmethod
    def insert_sql(data: Dict[str, Any]) -> tuple:
        """
        生成插入热榜数据的 SQL 语句
        
        数据字段映射（从热榜爬取数据到数据库）:
        - ranks[0] → rank (排名)
        - title (字典的 key) → title
        - hotValue → hot_value
        - video_id → 热榜话题 ID
        - aweme_id → 真正的视频 ID
        - cover → cover_url
        """
        sql = """
        INSERT INTO hot_search (`rank`, title, hot_value, video_id, aweme_id, cover_url, crawl_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data.get('rank'),
            data.get('title'),
            data.get('hot_value'),
            data.get('video_id'),
            data.get('aweme_id'),
            data.get('cover_url'),
            data.get('crawl_time', datetime.now())
        )
        return sql, params


class VideoModel:
    """视频数据模型"""

    @staticmethod
    def create_table() -> str:
        return """
        CREATE TABLE IF NOT EXISTS videos (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
            aweme_id VARCHAR(50) UNIQUE NOT NULL COMMENT '视频 ID',
            title VARCHAR(500) COMMENT '视频标题',
            crawl_time DATETIME NOT NULL COMMENT '爬取时间',
            INDEX idx_aweme_id (aweme_id),
            INDEX idx_crawl_time (crawl_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频数据表';
        """

    @staticmethod
    def insert_sql(data: Dict[str, Any]) -> tuple:
        """
        生成插入视频的 SQL 语句

        数据字段映射（从 JSON/爬取数据到数据库）:
        - id (JSON) → aweme_id (数据库)
        - desc → title
        """
        sql = """
        INSERT INTO videos (aweme_id, title, crawl_time)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            crawl_time = VALUES(crawl_time)
        """
        params = (
            data.get('id'),  # JSON 的 id 字段映射到 aweme_id
            data.get('desc'),  # JSON 的 desc 字段映射到 title
            data.get('crawl_time', datetime.now())
        )
        return sql, params


class CommentModel:
    """评论数据模型"""
    
    @staticmethod
    def create_table() -> str:
        return """
        CREATE TABLE IF NOT EXISTS comments (
            id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
            comment_id VARCHAR(50) UNIQUE NOT NULL COMMENT '评论 ID',
            aweme_id VARCHAR(50) NOT NULL COMMENT '视频 ID',
            nickname VARCHAR(200) COMMENT '用户昵称',
            text TEXT COMMENT '评论内容',
            create_time DATETIME COMMENT '评论时间',
            digg_count INT DEFAULT 0 COMMENT '点赞数',
            reply_count INT DEFAULT 0 COMMENT '回复数',
            ip_label VARCHAR(100) COMMENT 'IP 属地',
            is_top BOOLEAN DEFAULT FALSE COMMENT '是否置顶',
            is_hot BOOLEAN DEFAULT FALSE COMMENT '是否热门',
            crawl_time DATETIME NOT NULL COMMENT '爬取时间',
            INDEX idx_aweme_id (aweme_id),
            INDEX idx_comment_id (comment_id),
            INDEX idx_create_time (create_time),
            INDEX idx_digg_count (digg_count),
            INDEX idx_crawl_time (crawl_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评论数据表';
        """
    
    @staticmethod
    def insert_sql(data: Dict[str, Any]) -> tuple:
        """
        生成插入评论的 SQL 语句
        
        数据字段映射（从 CSV/爬取数据到数据库）:
        - id (CSV) → comment_id (数据库)
        - aweme_id → aweme_id
        - nickname → nickname
        - text → text
        - create_time → create_time
        - digg_count → digg_count
        - reply_count → reply_count
        - ip_label → ip_label
        - is_top → is_top
        - is_hot → is_hot
        """
        sql = """
        INSERT INTO comments (comment_id, aweme_id, nickname, text, create_time,
                             digg_count, reply_count, ip_label, is_top, is_hot, crawl_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            nickname = VALUES(nickname),
            text = VALUES(text),
            create_time = VALUES(create_time),
            digg_count = VALUES(digg_count),
            reply_count = VALUES(reply_count),
            ip_label = VALUES(ip_label),
            is_top = VALUES(is_top),
            is_hot = VALUES(is_hot),
            crawl_time = VALUES(crawl_time)
        """
        params = (
            data.get('id'),  # CSV 的 id 字段映射到 comment_id
            data.get('aweme_id'),
            data.get('nickname'),
            data.get('text'),
            data.get('create_time'),
            data.get('digg_count', 0),
            data.get('reply_count', 0),
            data.get('ip_label'),
            data.get('is_top', False),
            data.get('is_hot', False),
            data.get('crawl_time', datetime.now())
        )
        return sql, params
    
    @staticmethod
    def batch_insert_sql(comments: List[Dict[str, Any]]) -> tuple:
        """批量插入评论"""
        values = []
        params = []
        for data in comments:
            values.append("(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            params.extend([
                data.get('id'),  # CSV 的 id 字段映射到 comment_id
                data.get('aweme_id'),
                data.get('nickname'),
                data.get('text'),
                data.get('create_time'),
                data.get('digg_count', 0),
                data.get('reply_count', 0),
                data.get('ip_label'),
                data.get('is_top', False),
                data.get('is_hot', False),
                data.get('crawl_time', datetime.now())
            ])
        
        sql = f"""
        INSERT INTO comments (comment_id, aweme_id, nickname, text, create_time,
                             digg_count, reply_count, ip_label, is_top, is_hot, crawl_time)
        VALUES {', '.join(values)}
        ON DUPLICATE KEY UPDATE
            nickname = VALUES(nickname),
            text = VALUES(text),
            create_time = VALUES(create_time),
            digg_count = VALUES(digg_count),
            reply_count = VALUES(reply_count),
            ip_label = VALUES(ip_label),
            is_top = VALUES(is_top),
            is_hot = VALUES(is_hot),
            crawl_time = VALUES(crawl_time)
        """
        return sql, tuple(params)


class SchedulerHistoryModel:
    """定时任务历史模型"""
    
    @staticmethod
    def create_table() -> str:
        return """
        CREATE TABLE IF NOT EXISTS scheduler_history (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
            run_time DATETIME NOT NULL COMMENT '运行时间',
            video_count INT DEFAULT 0 COMMENT '爬取视频数',
            comment_count INT DEFAULT 0 COMMENT '爬取评论数',
            status VARCHAR(20) NOT NULL COMMENT '状态（success/failed）',
            error_message TEXT COMMENT '错误信息',
            duration INT COMMENT '执行时长（秒）',
            INDEX idx_run_time (run_time),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='定时任务历史表';
        """
    
    @staticmethod
    def insert_sql(data: Dict[str, Any]) -> tuple:
        sql = """
        INSERT INTO scheduler_history (run_time, video_count, comment_count, 
                                       status, error_message, duration)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            data.get('run_time', datetime.now()),
            data.get('video_count', 0),
            data.get('comment_count', 0),
            data.get('status'),
            data.get('error_message'),
            data.get('duration')
        )
        return sql, params


class HotCommentAnalysisModel:
    """热榜评论分析结果模型"""
    
    @staticmethod
    def create_table() -> str:
        return """
        CREATE TABLE IF NOT EXISTS hot_comment_analysis (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键 ID',
            aweme_id VARCHAR(50) NOT NULL COMMENT '视频 ID',
            hot_id VARCHAR(50) COMMENT '热榜话题 ID',
            title VARCHAR(500) COMMENT '热搜标题',
            cover_url VARCHAR(500) COMMENT '封面 URL',
            filename VARCHAR(500) NOT NULL COMMENT '文件名',
            filepath VARCHAR(1000) NOT NULL COMMENT '文件路径',
            total_comments INT NOT NULL COMMENT '评论总数',
            sentiment_positive INT DEFAULT 0 COMMENT '正面评论数',
            sentiment_neutral INT DEFAULT 0 COMMENT '中性评论数',
            sentiment_negative INT DEFAULT 0 COMMENT '负面评论数',
            sentiment_positive_rate DECIMAL(5,2) DEFAULT 0 COMMENT '正面率',
            sentiment_neutral_rate DECIMAL(5,2) DEFAULT 0 COMMENT '中性率',
            sentiment_negative_rate DECIMAL(5,2) DEFAULT 0 COMMENT '负面率',
            hot_words JSON COMMENT '热门词汇列表',
            location_distribution JSON COMMENT 'IP地区分布',
            time_distribution JSON COMMENT '时间分布',
            user_activity JSON COMMENT '用户活跃度',
            top_comments JSON COMMENT '热门评论',
            topics JSON COMMENT 'LDA主题分析结果',
            created_time DATETIME NOT NULL COMMENT '分析时间',
            UNIQUE KEY uk_aweme_id (aweme_id),
            INDEX idx_hot_id (hot_id),
            INDEX idx_created_time (created_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='热榜评论分析结果表';
        """
    
    @staticmethod
    def insert_sql(data: Dict[str, Any]) -> tuple:
        """生成插入分析结果的 SQL 语句"""
        import json
        sql = """
        INSERT INTO hot_comment_analysis (
            aweme_id, hot_id, title, cover_url, filename, filepath, total_comments,
            sentiment_positive, sentiment_neutral, sentiment_negative,
            sentiment_positive_rate, sentiment_neutral_rate, sentiment_negative_rate,
            hot_words, location_distribution, time_distribution, 
            user_activity, top_comments, topics, created_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            hot_id = VALUES(hot_id),
            title = VALUES(title),
            cover_url = VALUES(cover_url),
            filename = VALUES(filename),
            filepath = VALUES(filepath),
            total_comments = VALUES(total_comments),
            sentiment_positive = VALUES(sentiment_positive),
            sentiment_neutral = VALUES(sentiment_neutral),
            sentiment_negative = VALUES(sentiment_negative),
            sentiment_positive_rate = VALUES(sentiment_positive_rate),
            sentiment_neutral_rate = VALUES(sentiment_neutral_rate),
            sentiment_negative_rate = VALUES(sentiment_negative_rate),
            hot_words = VALUES(hot_words),
            location_distribution = VALUES(location_distribution),
            time_distribution = VALUES(time_distribution),
            user_activity = VALUES(user_activity),
            top_comments = VALUES(top_comments),
            topics = VALUES(topics),
            created_time = VALUES(created_time)
        """
        params = (
            data.get('aweme_id'),
            data.get('hot_id'),
            data.get('title'),
            data.get('cover_url'),
            data.get('filename'),
            data.get('filepath'),
            data.get('total_comments'),
            data.get('sentiment_positive'),
            data.get('sentiment_neutral'),
            data.get('sentiment_negative'),
            data.get('sentiment_positive_rate'),
            data.get('sentiment_neutral_rate'),
            data.get('sentiment_negative_rate'),
            json.dumps(data.get('hot_words', []), ensure_ascii=False),
            json.dumps(data.get('location_distribution', []), ensure_ascii=False),
            json.dumps(data.get('time_distribution', {}), ensure_ascii=False),
            json.dumps(data.get('user_activity', {}), ensure_ascii=False),
            json.dumps(data.get('top_comments', []), ensure_ascii=False),
            json.dumps(data.get('topics', {}), ensure_ascii=False),
            data.get('created_time', datetime.now())
        )
        return sql, params
