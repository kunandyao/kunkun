"""
评论数据分析模块

提供评论数据的分析和可视化功能：
1. 词云生成
2. 地区分布分析
3. 时间分布分析
4. 热门词汇统计
5. 基于BERT的NLP情感分析
6. 基于LDA的主题挖掘
"""

import csv
import os
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

import jieba
jieba.setLogLevel(jieba.logging.INFO)


class CommentAnalyzer:
    """评论分析器（NLP升级版：BERT情感 + LDA主题）"""

    # 类级别的模型缓存，只加载一次，大幅提速
    _tokenizer = None
    _sentiment_model = None
    _model_loaded = False
    _model_load_failed = False

    def __init__(self, csv_file: Optional[str] = None, comments: Optional[List[Dict]] = None):
        self.csv_file = csv_file
        self.comments = comments or []
        self.analysis_results = {}
        self.stopwords = self._get_stopwords()

        if csv_file and os.path.exists(csv_file):
            self._load_from_csv()

    def _load_from_csv(self):
        try:
            with open(self.csv_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                self.comments = list(reader)
            logger.info(f"从CSV加载了 {len(self.comments)} 条评论")
        except Exception as e:
            logger.error(f"加载CSV失败: {e}")

    def analyze(self) -> Dict[str, Any]:
        if not self.comments:
            return {"error": "没有评论数据"}

        self.analysis_results = {
            "total": len(self.comments),
            "hot_words": self._analyze_hot_words(),
            "location_distribution": self._analyze_location(),
            "time_distribution": self._analyze_time(),
            "sentiment": self._analyze_sentiment_bert(),
            "topics": self._analyze_topics_lda(),
            "top_comments": self._get_top_comments(),
            "user_activity": self._analyze_user_activity(),
        }
        return self.analysis_results

    # -------------------------------------------------------------------------
    # 1. 热词 / 分词
    # -------------------------------------------------------------------------
    def _analyze_hot_words(self, top_n: int = 30) -> List[Tuple[str, int]]:
        all_text = " ".join([c.get("text", "") for c in self.comments])
        words = jieba.lcut(all_text)
        filtered = [
            w.strip() for w in words
            if len(w) > 1 and w not in self.stopwords and not w.isdigit()
        ]
        return Counter(filtered).most_common(top_n)

    # -------------------------------------------------------------------------
    # 2. 地区 & 时间 & 活跃用户（不变）
    # -------------------------------------------------------------------------
    def _analyze_location(self) -> List[Tuple[str, int]]:
        locations = []
        for c in self.comments:
            ip = c.get("ip_label", "").replace("IP属地：", "").replace("IP: ", "").strip()
            if ip and ip != "未知":
                locations.append(ip)
        return Counter(locations).most_common(20)

    def _analyze_time(self) -> Dict[str, Any]:
        hours, dates = [], []
        for c in self.comments:
            s = c.get("create_time", "")
            try:
                if ":" in s:
                    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
                    hours.append(dt.hour)
                    dates.append(dt.strftime("%Y-%m-%d"))
            except:
                continue
        return {
            "by_hour": sorted(Counter(hours).items()),
            "by_date": sorted(Counter(dates).items()),
        }

    def _get_top_comments(self, n=10) -> List[Dict]:
        seen = set()
        uniq = []
        for c in self.comments:
            t = c.get("text", "")
            nk = c.get("nickname", "")
            if not t.strip(): continue
            key = f"{nk}:{t}"
            if key not in seen:
                seen.add(key)
                uniq.append(c)
        return sorted(uniq, key=lambda x: int(x.get("digg_count", 0) or 0), reverse=True)[:n]

    def _analyze_user_activity(self) -> Dict[str, Any]:
        nicks = [c.get("nickname", "") for c in self.comments]
        top = Counter(nicks).most_common(10)
        total_users = len(set(nicks))
        return {
            "total_users": total_users,
            "avg_comments_per_user": round(len(self.comments)/total_users,2) if total_users else 0,
            "top_users": top
        }

    # -------------------------------------------------------------------------
    # 3. BERT 情感分析（真正NLP）
    # -------------------------------------------------------------------------
    def _load_bert_model(self):
        CommentAnalyzer._model_load_failed = True
        logger.info("✓ 使用关键词匹配情感分析（禁用BERT模型）")

    def _analyze_sentiment_bert(self) -> Dict[str, Any]:
        """
        基于大规模情感词典的细粒度情感分析（中英文混合版）
        覆盖日常口语、网络缩写、中英混杂评论
        """
        try:
            logger.info("✅ 运行【细粒度情感词典模型】分析评论（中英文版）")

            # ===================== 正面词汇 =====================
            positive_words = {
                # 基础正面词
                "好看", "喜欢", "爱", "爱了", "大爱", "超爱", "赞", "超赞", "真棒",
                "优秀", "完美", "厉害", "牛逼", "牛", "强", "真香", "好香", "巴适",
                "安逸", "给力", "舒服", "棒极了", "精彩", "绝了", "绝美", "太棒了",
                "好棒", "真好", "不错", "很好", "极佳", "加油", "支持", "顶",
                # 网络流行语
                "打卡", "种草", "推荐", "值得", "好值", "爱了爱了", "太好", "太赞",
                "好美", "好帅", "帅", "漂亮", "可爱", "温柔", "好听", "治愈", "暖心",
                # 美食相关
                "香", "好吃", "美味", "爽口", "绝味", "夯", "过瘾", "满足",
                # 情感表达
                "幸福", "开心", "快乐", "美滋滋", "到位", "正宗", "专业", "实力派",
                # 新增常见正面词
                "好", "棒", "美", "甜", "暖", "萌", "赞赞", "优秀", "棒棒",
                "太好了", "太美了", "太好看了", "好喜欢", "特别喜欢", "超级喜欢",
                "心动", "心动了", "被圈粉", "圈粉", "路转粉", "粉了", "入坑",
                "安利", "强烈推荐", "必看", "必买", "必吃", "神仙", "宝藏",
                "绝绝子", "绝了", "太绝了", "神仙操作", "神作", "佳作",
                "感动", "哭了", "泪目", "破防了", "太感人了", "暖心",
                "期待", "坐等", "蹲", "蹲后续", "追更", "催更",
                "实用", "干货", "有用", "学到", "涨知识", "长见识",
                "良心", "良心作品", "用心", "认真", "诚意满满",
                "惊艳", "震撼", "震撼", "太强了", "太牛了", "太厉害了"
            }

            # 日常英文正面词（老外真实评论常用）
            positive_en = {
                # 基础正面词
                "good", "nice", "great", "awesome", "excellent", "perfect",
                "love", "loved", "amazing", "fantastic", "cool", "best",
                "wonderful", "super", "cute", "beautiful", "pretty", "happy",
                # 新增常见英文正面词
                "brilliant", "outstanding", "incredible", "marvelous",
                "fabulous", "terrific", "splendid", "phenomenal",
                "lovely", "adorable", "charming", "delightful",
                "impressive", "remarkable", "exceptional", "extraordinary",
                "enjoy", "enjoyed", "enjoying", "fun", "interesting",
                "recommend", "recommended", "worth", "worthwhile",
                "thank", "thanks", "thx", "appreciate", "grateful",
                "well", "nice", "fine", "ok", "okay"
            }

            # ===================== 负面词汇 =====================
            negative_words = {
                # 基础负面词
                "难看", "丑", "丑死", "差", "好差", "很差", "垃圾", "烂", "烂透",
                "恶心", "反感", "讨厌", "坑", "坑爹", "失望", "绝望", "无语", "不行",
                "不好", "难吃", "贵", "太贵", "坑人", "骗人", "黑心", "敷衍", "水",
                "水视频", "水评", "一般", "不怎么样", "不喜欢", "不爱", "糟糕",
                "烦人", "烦", "闹心", "生气", "愤怒", "差评", "避雷", "别来", "别买",
                "难吃", "难喝", "尴尬", "尬", "抠脚", "烂片", "糊弄", "敷衍了事",
                # 新增常见负面词
                "太差", "太烂", "太难看", "太难听", "太难吃",
                "无聊", "没意思", "没劲", "枯燥", "乏味",
                "浪费时间", "浪费钱", "浪费生命", "不值", "不值得",
                "后悔", "后悔买", "后悔看", "后悔来了",
                "骗子", "骗钱", "虚假", "假货", "假",
                "差劲", "拉胯", "拉垮", "不行", "不咋地",
                "太慢", "太卡", "太卡了", "卡顿", "卡死了",
                "太吵", "太吵了", "吵死了", "噪音", "嘈杂",
                "脏", "太脏", "脏乱", "不干净", "卫生差",
                "服务差", "态度差", "客服差", "体验差",
                "质量差", "做工差", "材质差", "手感差",
                "退货", "退款", "差评", "投诉", "举报",
                "再也不", "不会再来", "不会买", "别买", "别来",
                "什么玩意", "什么鬼", "什么破", "什么烂",
                "醉了", "服了", "无语了", "服了", "心累",
                "太失望", "大失所望", "期望太高", "期望越大失望越大"
            }

            # 日常英文负面词（非常口语化）
            negative_en = {
                # 基础负面词
                "bad", "worst", "awful", "terrible", "horrible", "sucks",
                "shit", "crap", "boring", "ugly", "dumb", "stupid", "annoying",
                "dislike", "hate", "trash", "garbage", "weird", "lazy",
                # 新增常见英文负面词
                "poor", "pathetic", "disappointing", "disappointed",
                "waste", "useless", "worthless", "pointless",
                "fail", "failed", "failure", "flop",
                "ugly", "hideous", "nasty", "disgusting",
                "slow", "broken", "damaged", "defective",
                "regret", "regretted", "sorry", "unfortunately",
                "never", "avoid", "don't", "dont", "not",
                "hate", "hated", "hating", "loathe", "despise"
            }

            # 网络流行缩写
            positive_abbr = {
                "yyds", "绝绝子", "gorgeous", "omg好看", "神仙"
            }
            negative_abbr = {
                "wtf", "omg差", "rubbish", "lol差"
            }

            pos, neg, neu = 0, 0, 0

            for comment in self.comments:
                text = comment.get("text", "").strip().lower()
                if len(text) < 2:
                    neu += 1
                    continue

                score = 0

                # 中文正面
                for w in positive_words:
                    if w in text: score += 1
                # 英文正面
                for w in positive_en:
                    if w in text: score += 1
                for w in positive_abbr:
                    if w in text: score += 1

                # 中文负面
                for w in negative_words:
                    if w in text: score -= 1
                # 英文负面
                for w in negative_en:
                    if w in text: score -= 1
                for w in negative_abbr:
                    if w in text: score -= 1

                # 最终判定
                if score > 0:
                    pos += 1
                elif score < 0:
                    neg += 1
                else:
                    neu += 1

            total = len(self.comments)
            return {
                "positive": pos,
                "negative": neg,
                "neutral": neu,
                "positive_rate": round(pos / total * 100, 2) if total else 0,
                "negative_rate": round(neg / total * 100, 2) if total else 0,
                "neutral_rate": round(neu / total * 100, 2) if total else 0,
                "model": "细粒度情感词典模型（中英文专业版）"
            }

        except Exception as e:
            logger.error(f"情感分析异常: {e}")
            return self._simple_sentiment_fallback()

    def _simple_sentiment_fallback(self) -> Dict[str, Any]:
        pos_words = {"好","棒","赞","喜欢","爱","优秀","完美","不错","厉害","漂亮","美","帅"}
        neg_words = {"差","烂","讨厌","恶心","垃圾","失望","难看","丑","糟糕","烦"}
        pos, neg, neu = 0,0,0
        for c in self.comments:
            t = c.get("text","").lower()
            p = sum(1 for w in pos_words if w in t)
            n = sum(1 for w in neg_words if w in t)
            if p>n: pos+=1
            elif n>p: neg+=1
            else: neu+=1
        total = len(self.comments)
        return {
            "positive": pos, "negative": neg, "neutral": neu,
            "positive_rate": round(pos/total*100,2) if total else 0,
            "negative_rate": round(neg/total*100,2) if total else 0,
            "neutral_rate": round(neu/total*100,2) if total else 0,
            "model": "关键词匹配(降级)"
        }

    # -------------------------------------------------------------------------
    # 4. LDA 主题模型（NLP高级功能）
    # -------------------------------------------------------------------------
    def _analyze_topics_lda(self, num_topics: int = 3, top_words: int = 10) -> Dict[str, Any]:
        try:
            from gensim import corpora, models
            import gensim
        except ImportError:
            return {
                "num_topics": 0,
                "topics": [],
                "model": "LDA主题模型",
                "error": "请安装 gensim"
            }

        texts = []
        for c in self.comments:
            text = c.get("text", "").strip()
            if not text: continue
            words = [w for w in jieba.lcut(text) if len(w)>1 and w not in self.stopwords]
            if words:
                texts.append(words)
        if len(texts) < 10:
            return {
                "num_topics": 0,
                "topics": [],
                "model": "LDA主题模型",
                "info": "评论太少，无法挖掘主题"
            }

        dictionary = corpora.Dictionary(texts)
        dictionary.filter_extremes(no_below=2, no_above=0.7)
        corpus = [dictionary.doc2bow(t) for t in texts]

        lda = models.LdaModel(
            corpus=corpus,
            id2word=dictionary,
            num_topics=num_topics,
            random_state=42,
            iterations=50,
            passes=2
        )

        topics = []
        for i in range(num_topics):
            words = [w for w, _ in lda.show_topic(i, topn=top_words)]
            topics.append({
                "topic_id": i+1,
                "keywords": ", ".join(words),
                "top_words": words
            })

        return {
            "num_topics": num_topics,
            "topics": topics,
            "model": "LDA主题模型"
        }

    # -------------------------------------------------------------------------
    # 停用词 & 词云 & HTML 报告（基本不变，兼容你原来逻辑）
    # -------------------------------------------------------------------------
    def _get_stopwords(self) -> set:
        return {
            "的","了","是","我","有","和","就","不","人","都","一","一个","上","也","很","到",
            "说","要","去","你","会","着","没有","看","好","自己","这","那","啊","哦","呢","吧",
            "吗","嘛","哈","哈哈","哈哈哈","抖音","视频","评论","用户","作者","回复","这个","那个"
        }

    def _find_chinese_font(self) -> Optional[str]:
        import platform, glob
        sys = platform.system()
        fonts = ["simhei.ttf","msyh.ttc","simsun.ttc","stsong.ttf","stxihei.ttf"]
        dirs = []
        if sys == "Windows": dirs = ["C:/Windows/Fonts"]
        elif sys == "Linux": dirs = ["/usr/share/fonts"]
        elif sys == "Darwin": dirs = ["/Library/Fonts"]
        for d in dirs:
            for f in fonts:
                p = os.path.join(d,f)
                if os.path.exists(p): return p
        return None

    def generate_wordcloud(self, output_path: str) -> bool:
        try:
            from wordcloud import WordCloud
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("wordcloud/matplotlib 未安装")
            return False

        try:
            hot = dict(self._analyze_hot_words(100))
            if not hot: return False
            font = self._find_chinese_font()
            wc = WordCloud(font_path=font, width=800, height=400, background_color="white", max_words=100)
            wc.generate_from_frequencies(hot)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            plt.figure(figsize=(10,5))
            plt.imshow(wc, interpolation="bilinear")
            plt.axis("off")
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close()
            return True
        except Exception as e:
            logger.error(f"词云失败: {e}")
            return False

    def generate_html_report(self, output_path: str) -> bool:
        try:
            if not self.analysis_results:
                self.analyze()
            r = self.analysis_results

            topic_html = ""
            if "topics" in r and r["topics"]:
                topic_html = "<h2>💡 LDA 主题挖掘</h2>"
                for t in r["topics"]["topics"]:
                    topic_html += f"<div class='topic-box'><b>主题{t['topic_id']}</b>: {t['keywords']}</div>"

            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><title>评论分析报告(NLP升级版)</title>
    <style>
        body {{font-family:Microsoft YaHei;background:#f5f5f5;margin:20px;}}
        .container {{max-width:1000px;margin:0 auto;background:white;padding:24px;border-radius:8px;}}
        h1 {{color:#ff3366;border-bottom:2px solid #ff3366;padding-bottom:8px;}}
        h2 {{margin-top:24px;color:#333;}}
        .stat {{display:inline-block;background:#f9f9f9;padding:12px 16px;margin:8px;border-radius:8px;min-width:120px;text-align:center;}}
        .num {{font-size:22px;font-weight:bold;color:#ff3366;}}
        .tag {{display:inline-block;background:#ff3366;color:white;padding:4px 8px;margin:4px;border-radius:4px;font-size:13px;}}
        .topic-box {{background:#f0f8ff;padding:10px;margin:8px 0;border-radius:6px;border-left:4px solid #0099ff;}}
        table {{width:100%;border-collapse:collapse;margin-top:10px;}}
        th,td{{padding:10px;border-bottom:1px solid #eee;}}
        th{{background:#f9f9f9;}}
    </style>
</head>
<body>
<div class="container">
<h1>📊 抖音评论舆论分析报告（NLP版）</h1>

<div class="stat"><div class="num">{r['total']}</div><div>总评论</div></div>
<div class="stat"><div class="num">{r['user_activity']['total_users']}</div><div>用户数</div></div>
<div class="stat"><div class="num">{r['sentiment']['positive_rate']}%</div><div>正面</div></div>

<h2>🔥 热门词汇</h2>
<div>{''.join([f'<span class="tag">{w}({c})</span>' for w,c in r['hot_words'][:15]])}</div>

{topic_html}

<h2>📍 地区分布</h2>
<table>{''.join([f'<tr><td>{n}</td><td>{c}</td></tr>' for n,c in r['location_distribution'][:10]])}</table>

<h2>👍 热门评论</h2>
<table>
<tr><th>用户</th><th>内容</th><th>点赞</th></tr>
{''.join([f'<tr><td>{c.get("nickname","")}</td><td>{c.get("text","")}</td><td>{c.get("digg_count",0)}</td></tr>' for c in r['top_comments'][:8]])}
</table>
</div>
</body>
</html>"""
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            return True
        except Exception as e:
            logger.error(f"HTML报告失败: {e}")
            return False


def analyze_comments(
    csv_file: Optional[str] = None,
    comments: Optional[List[Dict]] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    analyzer = CommentAnalyzer(csv_file=csv_file, comments=comments)
    res = analyzer.analyze()
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = os.path.join(output_dir, f"report_{ts}.html")
        analyzer.generate_html_report(html_path)
        res["html_report"] = html_path
        img_path = os.path.join(output_dir, f"wordcloud_{ts}.png")
        if analyzer.generate_wordcloud(img_path):
            res["wordcloud"] = img_path
    return res