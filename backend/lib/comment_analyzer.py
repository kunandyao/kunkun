"""
评论数据分析模块

提供评论数据的分析和可视化功能：
1. 词云生成
2. 地区分布分析
3. 时间分布分析
4. 热门词汇统计
5. 情感分析
"""

import csv
import os
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from loguru import logger


class CommentAnalyzer:
    """评论分析器"""

    def __init__(self, csv_file: Optional[str] = None, comments: Optional[List[Dict]] = None):
        """
        初始化分析器

        Args:
            csv_file: CSV文件路径
            comments: 评论数据列表
        """
        self.csv_file = csv_file
        self.comments = comments or []
        self.analysis_results = {}

        if csv_file and os.path.exists(csv_file):
            self._load_from_csv()

    def _load_from_csv(self):
        """从CSV加载数据"""
        try:
            with open(self.csv_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                self.comments = list(reader)
            logger.info(f"从CSV加载了 {len(self.comments)} 条评论")
        except Exception as e:
            logger.error(f"加载CSV失败: {e}")

    def analyze(self) -> Dict:
        """
        执行全部分析

        Returns:
            Dict: 分析结果
        """
        if not self.comments:
            return {"error": "没有评论数据"}

        self.analysis_results = {
            "total": len(self.comments),
            "hot_words": self._analyze_hot_words(),
            "location_distribution": self._analyze_location(),
            "time_distribution": self._analyze_time(),
            "sentiment": self._analyze_sentiment(),
            "top_comments": self._get_top_comments(),
            "user_activity": self._analyze_user_activity(),
        }

        return self.analysis_results

    def _analyze_hot_words(self, top_n: int = 30) -> List[Tuple[str, int]]:
        """分析热门词汇"""
        # 加载停用词
        stopwords = self._get_stopwords()

        # 提取所有文本
        all_text = " ".join([c.get("text", "") for c in self.comments])

        # 使用jieba分词
        try:
            import jieba
            words = jieba.lcut(all_text)
        except ImportError:
            # 如果没有jieba，使用简单分词
            words = re.findall(r'\b\w+\b', all_text)

        # 过滤停用词和短词
        filtered_words = [
            w.strip() for w in words
            if len(w.strip()) > 1
            and w.strip() not in stopwords
            and not w.strip().isdigit()
            and not re.match(r'^[a-zA-Z0-9]+$', w.strip())
        ]

        # 统计词频
        word_counts = Counter(filtered_words)
        return word_counts.most_common(top_n)

    def _analyze_location(self) -> List[Tuple[str, int]]:
        """分析地区分布"""
        locations = []
        for comment in self.comments:
            ip_label = comment.get("ip_label", "")
            if ip_label:
                # 提取省份/城市
                location = ip_label.replace("IP属地：", "").replace("IP: ", "").strip()
                if location and location != "未知":
                    locations.append(location)

        location_counts = Counter(locations)
        return location_counts.most_common(20)

    def _analyze_time(self) -> Dict[str, List[Tuple[str, int]]]:
        """分析时间分布"""
        hours = []
        dates = []

        for comment in self.comments:
            time_str = comment.get("create_time", "")
            if time_str:
                try:
                    # 尝试解析时间
                    if ":" in time_str:
                        # 格式: 2024-01-01 12:00:00
                        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                        hours.append(dt.hour)
                        dates.append(dt.strftime("%Y-%m-%d"))
                except:
                    pass

        hour_counts = Counter(hours)
        date_counts = Counter(dates)

        # 按小时排序
        hour_distribution = sorted(hour_counts.items(), key=lambda x: x[0])
        # 按日期排序
        date_distribution = sorted(date_counts.items(), key=lambda x: x[0])

        return {
            "by_hour": hour_distribution,
            "by_date": date_distribution,
        }

    def _analyze_sentiment(self) -> Dict:
        """简单情感分析"""
        positive_words = [
            "好", "棒", "赞", "喜欢", "爱", "优秀", "完美", "不错", "厉害",
            "漂亮", "美", "帅", "可爱", "精彩", "感动", "开心", "快乐",
            "支持", "加油", "太棒了", " awesome", "good", "great", "love",
        ]
        negative_words = [
            "差", "烂", "讨厌", "恶心", "垃圾", "失望", "难看", "丑",
            "糟糕", "烦", "生气", "愤怒", "无语", "呵呵", "bad", "hate",
            "terrible", "awful",
        ]

        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for comment in self.comments:
            text = comment.get("text", "").lower()
            pos_score = sum(1 for word in positive_words if word in text)
            neg_score = sum(1 for word in negative_words if word in text)

            if pos_score > neg_score:
                positive_count += 1
            elif neg_score > pos_score:
                negative_count += 1
            else:
                neutral_count += 1

        total = len(self.comments)
        return {
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
            "positive_rate": round(positive_count / total * 100, 2) if total > 0 else 0,
            "negative_rate": round(negative_count / total * 100, 2) if total > 0 else 0,
            "neutral_rate": round(neutral_count / total * 100, 2) if total > 0 else 0,
        }

    def _get_top_comments(self, n: int = 10) -> List[Dict]:
        """获取热门评论（按点赞数）"""
        sorted_comments = sorted(
            self.comments,
            key=lambda x: int(x.get("digg_count", 0) or 0),
            reverse=True
        )
        return sorted_comments[:n]

    def _analyze_user_activity(self) -> Dict:
        """分析用户活跃度"""
        # 统计评论数最多的用户
        user_comments = Counter([c.get("nickname", "") for c in self.comments])
        top_users = user_comments.most_common(10)

        # 统计总用户数
        unique_users = len(set(c.get("nickname", "") for c in self.comments))

        return {
            "total_users": unique_users,
            "avg_comments_per_user": round(len(self.comments) / unique_users, 2) if unique_users > 0 else 0,
            "top_users": top_users,
        }

    def _get_stopwords(self) -> set:
        """获取停用词表"""
        default_stopwords = {
            "的", "了", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也",
            "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这",
            "那", "啊", "哦", "呢", "吧", "吗", "嘛", "哈", "哈哈", "哈哈哈", "嘻嘻", "嘿嘿",
            "抖音", "视频", "评论", "用户", "作者",
        }
        return default_stopwords

    def _find_chinese_font(self) -> Optional[str]:
        """
        查找系统中可用的中文字体

        Returns:
            字体文件路径，如果找不到返回None
        """
        import platform
        import glob

        system = platform.system()

        # 常见的中文字体列表
        chinese_fonts = [
            "simhei.ttf", "simhei.ttc",
            "msyh.ttc", "msyh.ttf",
            "simsun.ttc", "simsun.ttf",
            "stsong.ttf", "stxihei.ttf",
            "NotoSansCJK-Regular.ttc",
            "SourceHanSansCN-Regular.otf",
        ]

        # Windows系统字体路径
        if system == "Windows":
            font_dirs = [
                "C:/Windows/Fonts",
                "C:/Windows/System32/Fonts",
            ]
        # Linux系统字体路径
        elif system == "Linux":
            font_dirs = [
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.local/share/fonts"),
            ]
        # macOS系统字体路径
        elif system == "Darwin":
            font_dirs = [
                "/System/Library/Fonts",
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"),
            ]
        else:
            return None

        # 搜索字体文件
        for font_dir in font_dirs:
            if not os.path.exists(font_dir):
                continue

            for font_name in chinese_fonts:
                # 直接匹配
                font_path = os.path.join(font_dir, font_name)
                if os.path.exists(font_path):
                    return font_path

                # 模糊搜索
                pattern = os.path.join(font_dir, f"*{font_name.split('.')[0]}*")
                matches = glob.glob(pattern, recursive=True)
                if matches:
                    return matches[0]

        logger.warning("未找到中文字体，词云可能无法正确显示中文")
        return None

    def generate_wordcloud(self, output_path: str) -> bool:
        """
        生成词云图

        Args:
            output_path: 输出图片路径

        Returns:
            bool: 是否成功
        """
        try:
            from wordcloud import WordCloud
            import matplotlib
            matplotlib.use('Agg')  # 使用非GUI后端
            import matplotlib.pyplot as plt

            # 获取热门词
            hot_words = self._analyze_hot_words(100)
            if not hot_words:
                logger.warning("没有足够的词汇生成词云")
                return False

            # 构建词频字典
            word_freq = dict(hot_words)

            # 查找中文字体
            font_path = self._find_chinese_font()

            # 生成词云
            wc = WordCloud(
                font_path=font_path if font_path else None,
                width=800,
                height=400,
                background_color="white",
                max_words=100,
                prefer_horizontal=0.9,
                relative_scaling=0.5,
                min_font_size=10,
            ).generate_from_frequencies(word_freq)

            # 保存
            plt.figure(figsize=(10, 5))
            plt.imshow(wc, interpolation="bilinear")
            plt.axis("off")
            plt.tight_layout(pad=0)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
            plt.close()

            logger.info(f"词云图已保存: {output_path}")
            return True

        except ImportError as e:
            logger.warning(f"生成词云需要安装 wordcloud 和 matplotlib: {e}")
            return False
        except Exception as e:
            logger.error(f"生成词云失败: {e}")
            return False

    def generate_html_report(self, output_path: str) -> bool:
        """
        生成HTML分析报告

        Args:
            output_path: 输出HTML路径

        Returns:
            bool: 是否成功
        """
        try:
            from pyecharts.charts import Bar, Pie, Line, Page
            from pyecharts import options as opts
            from pyecharts.globals import ThemeType
        except ImportError:
            logger.warning("生成HTML报告需要安装 pyecharts")
            return self._generate_simple_html_report(output_path)

        try:
            # 执行分析
            if not self.analysis_results:
                self.analyze()

            results = self.analysis_results

            # 创建页面
            page = Page(page_title="抖音评论分析报告")

            # 1. 热门词汇柱状图
            hot_words = results.get("hot_words", [])[:15]
            if hot_words:
                bar = (
                    Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
                    .add_xaxis([w[0] for w in hot_words])
                    .add_yaxis("出现次数", [w[1] for w in hot_words])
                    .set_global_opts(
                        title_opts=opts.TitleOpts(title="热门词汇 TOP15"),
                        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-45)),
                    )
                )
                page.add(bar)

            # 2. 地区分布饼图
            locations = results.get("location_distribution", [])[:10]
            if locations:
                pie = (
                    Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
                    .add(
                        "地区分布",
                        [(l[0], l[1]) for l in locations],
                        radius=["40%", "75%"],
                    )
                    .set_global_opts(
                        title_opts=opts.TitleOpts(title="评论用户地区分布 TOP10"),
                        legend_opts=opts.LegendOpts(orient="vertical", pos_top="15%", pos_left="2%"),
                    )
                )
                page.add(pie)

            # 3. 时间分布折线图
            time_dist = results.get("time_distribution", {})
            by_hour = time_dist.get("by_hour", [])
            if by_hour:
                line = (
                    Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
                    .add_xaxis([f"{h[0]}时" for h in by_hour])
                    .add_yaxis("评论数", [h[1] for h in by_hour])
                    .set_global_opts(
                        title_opts=opts.TitleOpts(title="评论时间分布（按小时）"),
                    )
                )
                page.add(line)

            # 4. 情感分析饼图
            sentiment = results.get("sentiment", {})
            if sentiment:
                pie2 = (
                    Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
                    .add(
                        "情感分布",
                        [
                            ("正面", sentiment.get("positive", 0)),
                            ("中性", sentiment.get("neutral", 0)),
                            ("负面", sentiment.get("negative", 0)),
                        ],
                    )
                    .set_global_opts(
                        title_opts=opts.TitleOpts(title="评论情感分析"),
                    )
                )
                page.add(pie2)

            # 保存
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            page.render(output_path)
            logger.info(f"HTML报告已保存: {output_path}")
            return True

        except Exception as e:
            logger.error(f"生成HTML报告失败: {e}")
            return self._generate_simple_html_report(output_path)

    def _generate_simple_html_report(self, output_path: str) -> bool:
        """生成简单的HTML报告（不需要pyecharts）"""
        try:
            if not self.analysis_results:
                self.analyze()

            results = self.analysis_results

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>抖音评论分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; border-bottom: 2px solid #ff0050; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 30px; }}
        .stat-box {{ display: inline-block; margin: 10px; padding: 15px; background: #f8f8f8; border-radius: 8px; min-width: 150px; }}
        .stat-number {{ font-size: 24px; font-weight: bold; color: #ff0050; }}
        .stat-label {{ font-size: 14px; color: #999; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f8f8; font-weight: bold; }}
        .comment-text {{ max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .tag {{ display: inline-block; padding: 2px 8px; background: #ff0050; color: white; border-radius: 4px; font-size: 12px; margin: 2px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 抖音评论分析报告</h1>
        
        <div class="stat-box">
            <div class="stat-number">{results.get('total', 0)}</div>
            <div class="stat-label">总评论数</div>
        </div>
        
        <div class="stat-box">
            <div class="stat-number">{results.get('user_activity', {}).get('total_users', 0)}</div>
            <div class="stat-label">独立用户数</div>
        </div>
        
        <div class="stat-box">
            <div class="stat-number">{results.get('sentiment', {}).get('positive_rate', 0)}%</div>
            <div class="stat-label">正面评价占比</div>
        </div>

        <h2>🔥 热门词汇 TOP15</h2>
        <div>
            {''.join([f'<span class="tag">{w[0]} ({w[1]})</span>' for w in results.get('hot_words', [])[:15]])}
        </div>

        <h2>📍 地区分布 TOP10</h2>
        <table>
            <tr><th>地区</th><th>评论数</th></tr>
            {''.join([f'<tr><td>{l[0]}</td><td>{l[1]}</td></tr>' for l in results.get('location_distribution', [])[:10]])}
        </table>

        <h2>👍 热门评论 TOP10</h2>
        <table>
            <tr><th>用户</th><th>评论内容</th><th>点赞数</th></tr>
            {''.join([f'<tr><td>{c.get("nickname", "")}</td><td class="comment-text">{c.get("text", "")}</td><td>{c.get("digg_count", 0)}</td></tr>' for c in results.get('top_comments', [])[:10]])}
        </table>
    </div>
</body>
</html>
"""

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"简单HTML报告已保存: {output_path}")
            return True

        except Exception as e:
            logger.error(f"生成简单HTML报告失败: {e}")
            return False


def analyze_comments(
    csv_file: Optional[str] = None,
    comments: Optional[List[Dict]] = None,
    output_dir: Optional[str] = None,
) -> Dict:
    """
    便捷函数：分析评论并生成报告

    Args:
        csv_file: CSV文件路径
        comments: 评论数据列表
        output_dir: 输出目录

    Returns:
        Dict: 分析结果和报告路径
    """
    analyzer = CommentAnalyzer(csv_file=csv_file, comments=comments)
    results = analyzer.analyze()

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 生成HTML报告
        html_path = os.path.join(output_dir, f"comment_analysis_{ts}.html")
        analyzer.generate_html_report(html_path)
        results["html_report"] = html_path

        # 尝试生成词云
        wordcloud_path = os.path.join(output_dir, f"comment_wordcloud_{ts}.png")
        if analyzer.generate_wordcloud(wordcloud_path):
            results["wordcloud"] = wordcloud_path

    return results
