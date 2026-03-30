# 大数据架构改造方案

## 📋 项目概述

**目标**：将当前抖音舆情采集系统升级为基于 **Hadoop + Spark** 的大数据架构，实现 6 大核心模块。

---

## 🏗️ 新架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Vue.js 前端 + ECharts 可视化大屏                          │  │
│  │  - 舆情仪表盘                                              │  │
│  │  - 情感分析图表                                            │  │
│  │  - 地域分布热力图                                          │  │
│  │  - 趋势预测展示                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      业务应用层 (Django)                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Django Web 业务系统                                       │  │
│  │  - 用户管理                                                │  │
│  │  - 任务调度                                                │  │
│  │  - 数据管理                                                │  │
│  │  - 报表生成                                                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据采集层                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  采集模块                                                  │  │
│  │  - 抖音开放平台 API                                        │  │
│  │  - 自动化爬虫 (Selenium/Playwright)                        │  │
│  │  - 定时调度 (Celery + Redis)                               │  │
│  │  - 增量采集机制                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据存储层                                  │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │  HDFS (原始数据) │              │  MySQL (结果数据)│          │
│  │  - 原始评论      │              │  - 分析结果     │          │
│  │  - 原始用户信息  │              │  - 用户信息     │          │
│  │  - JSON 日志     │              │  - 业务数据     │          │
│  └─────────────────┘              └─────────────────┘          │
│           │                              ▲                       │
│           │ Spark SQL                    │                       │
│           └──────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据处理层 (Spark)                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Spark 计算引擎                                            │  │
│  │  - 数据清洗 (Pandas on Spark)                              │  │
│  │  - 中文分词 (Jieba on Spark)                               │  │
│  │  - 情感分析 (MLlib)                                        │  │
│  │  - 主题挖掘 (LDA)                                          │  │
│  │  - 地域分析                                                │  │
│  │  - 趋势预测 (回归模型)                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 6 大核心模块详细设计

### 1️⃣ 数据采集模块

**技术栈**：
- 抖音开放平台 API
- Selenium/Playwright (自动化爬虫)
- Celery + Redis (定时任务调度)
- Requests (HTTP 请求)

**目录结构**：
```
backend/
├── collectors/              # 采集器模块
│   ├── __init__.py
│   ├── api_collector.py    # API 采集
│   ├── spider_collector.py # 爬虫采集
│   ├── scheduler.py        # 定时调度
│   └── increment.py        # 增量采集
└── celery_app.py           # Celery 配置
```

**核心功能**：
```python
# collectors/scheduler.py
from celery import Celery
from celery.schedules import crontab

app = Celery('douyin', broker='redis://localhost:6379/0')

app.conf.beat_schedule = {
    'hourly-hot-search': {
        'task': 'collectors.tasks.collect_hot_search',
        'schedule': crontab(minute=0),  # 每小时执行
    },
    'daily-comments': {
        'task': 'collectors.tasks.collect_comments',
        'schedule': crontab(minute=0, hour=2),  # 每天凌晨 2 点
    },
}
```

---

### 2️⃣ 数据预处理模块

**技术栈**：
- Pandas on Spark
- Jieba (中文分词)
- Spark SQL

**目录结构**：
```
spark_jobs/
├── __init__.py
├── data_cleaning.py      # 数据清洗
├── text_processing.py    # 文本处理
├── stop_words.txt        # 停用词表
└── standardize.py        # 数据标准化
```

**核心代码**：
```python
# spark_jobs/data_cleaning.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace, when
import jieba

class DataCleaner:
    def __init__(self, spark: SparkSession):
        self.spark = spark
    
    def clean_comments(self, df):
        """清洗评论数据"""
        # 去除空值
        df = df.filter(col("content").isNotNull())
        
        # 去除特殊字符
        df = df.withColumn(
            "content_clean",
            regexp_replace(col("content"), "[^\\u4e00-\\u9fa5a-zA-Z0-9]", "")
        )
        
        # 去除重复
        df = df.dropDuplicates(["comment_id"])
        
        return df
    
    def tokenize(self, text):
        """中文分词"""
        return " ".join(jieba.cut(text))
```

---

### 3️⃣ 数据存储模块

**技术栈**：
- HDFS (Hadoop Distributed File System)
- MySQL
- Spark SQL

**目录结构**：
```
storage/
├── __init__.py
├── hdfs_client.py        # HDFS 客户端
├── mysql_client.py       # MySQL 客户端
├── sync_manager.py       # 数据同步
└── models.py             # 数据模型
```

**HDFS 目录设计**：
```
/hdfs/douyin/
├── raw/                  # 原始数据层 (ODS)
│   ├── comments/
│   │   ├── 2026-03-27/
│   │   └── 2026-03-28/
│   └── users/
├── cleaned/              # 清洗数据层 (DWD)
│   └── comments_cleaned/
└── analysis/             # 分析结果层 (DWS)
    └── sentiment_results/
```

**核心代码**：
```python
# storage/hdfs_client.py
from hdfs import InsecureClient

class HDFSClient:
    def __init__(self, namenode_url="http://localhost:50070"):
        self.client = InsecureClient(namenode_url, user='hadoop')
    
    def save_parquet(self, df, path):
        """保存 Parquet 格式数据"""
        df.write.parquet(f"hdfs://localhost:9000/{path}", mode='overwrite')
    
    def load_parquet(self, path):
        """加载 Parquet 数据"""
        return self.spark.read.parquet(f"hdfs://localhost:9000/{path}")
```

---

### 4️⃣ 核心分析模块

**技术栈**：
- Spark MLlib
- Spark GraphX
- Jieba

**目录结构**：
```
spark_jobs/
├── sentiment_analysis.py   # 情感分析
├── topic_mining.py        # 主题挖掘
├── region_analysis.py     # 地域分析
└── trend_prediction.py    # 趋势预测
```

**情感分析示例**：
```python
# spark_jobs/sentiment_analysis.py
from pyspark.ml import Pipeline
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.feature import HashingTF, Tokenizer

class SentimentAnalyzer:
    def __init__(self, spark):
        self.spark = spark
        
    def train(self, train_data):
        """训练情感分类模型"""
        tokenizer = Tokenizer(inputCol="content", outputCol="words")
        hashingTF = HashingTF(inputCol="words", outputCol="features")
        lr = LogisticRegression(maxIter=10, regParam=0.01)
        
        pipeline = Pipeline(stages=[tokenizer, hashingTF, lr])
        model = pipeline.fit(train_data)
        
        return model
    
    def predict(self, model, data):
        """预测情感倾向"""
        predictions = model.transform(data)
        return predictions.select("comment_id", "content", "prediction")
```

**主题挖掘 (LDA)**：
```python
# spark_jobs/topic_mining.py
from pyspark.ml.clustering import LDA
from pyspark.ml.feature import CountVectorizer

class TopicMiner:
    def __init__(self, spark, num_topics=10):
        self.spark = spark
        self.num_topics = num_topics
    
    def extract_topics(self, df):
        """提取评论主题"""
        # 词频统计
        cv = CountVectorizer(inputCol="words", outputCol="features", vocabSize=10000)
        cvModel = cv.fit(df)
        corpus = cvModel.transform(df)
        
        # LDA 聚类
        lda = LDA(k=self.num_topics, maxIter=10)
        model = lda.fit(corpus)
        
        # 显示主题
        topics = model.describeTopics(maxTermsPerTopic=5)
        return topics
```

---

### 5️⃣ 数据可视化模块

**技术栈**：
- Vue.js 3
- ECharts 5
- Django REST Framework

**目录结构**：
```
frontend_new/
├── src/
│   ├── views/
│   │   ├── Dashboard.vue       # 数据大屏
│   │   ├── Sentiment.vue       # 情感分析
│   │   ├── Topics.vue          # 主题分析
│   │   └── Region.vue          # 地域分析
│   ├── components/
│   │   ├── WordCloud.vue
│   │   ├── HeatMap.vue
│   │   └── TrendChart.vue
│   └── api/
│       └── index.js
```

**ECharts 大屏示例**：
```vue
<!-- Dashboard.vue -->
<template>
  <div class="dashboard">
    <div class="chart-row">
      <div id="sentiment-chart" style="width: 600px; height: 400px;"></div>
      <div id="topic-cloud" style="width: 600px; height: 400px;"></div>
    </div>
    <div id="region-map" style="width: 1200px; height: 500px;"></div>
  </div>
</template>

<script>
import * as echarts from 'echarts';
import 'echarts-wordcloud';

export default {
  mounted() {
    this.initSentimentChart();
    this.initWordCloud();
    this.initRegionMap();
  },
  methods: {
    async initSentimentChart() {
      const chart = echarts.init(document.getElementById('sentiment-chart'));
      const data = await this.$api.getSentimentStats();
      
      chart.setOption({
        title: { text: '情感分布' },
        tooltip: {},
        xAxis: { data: ['正面', '中性', '负面'] },
        yAxis: {},
        series: [{
          type: 'bar',
          data: data.values
        }]
      });
    }
  }
}
</script>
```

---

### 6️⃣ 业务系统与智能挖掘模块

**技术栈**：
- Django 4
- Django REST Framework
- Scikit-learn
- XGBoost

**目录结构**：
```
django_project/
├── manage.py
├── opinion/
│   ├── __init__.py
│   ├── models.py          # 数据模型
│   ├── views.py           # 视图
│   ├── urls.py            # URL 路由
│   ├── serializers.py     # DRF 序列化
│   └── ml/
│       ├── trend_predict.py  # 趋势预测
│       └── anomaly_detect.py # 异常检测
└── templates/
```

**趋势预测模型**：
```python
# opinion/ml/trend_predict.py
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

class TrendPredictor:
    def __init__(self):
        self.model = XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1
        )
    
    def prepare_features(self, historical_data):
        """准备特征数据"""
        # 特征工程
        features = []
        for i in range(len(historical_data) - 7):
            # 使用过去 7 天的数据预测第 8 天
            window = historical_data[i:i+7]
            features.append({
                'mean_7d': np.mean(window),
                'std_7d': np.std(window),
                'trend': window[-1] - window[0],
            })
        
        return features
    
    def train(self, X_train, y_train):
        """训练预测模型"""
        self.model.fit(X_train, y_train)
    
    def predict_next_day(self, historical_data):
        """预测明天舆情热度"""
        features = self.prepare_features(historical_data)
        return self.model.predict([features[-1]])[0]
```

---

## 🚀 实施步骤

### 阶段 1：环境搭建（1-2 周）
```bash
# 1. 安装 Hadoop
wget https://downloads.apache.org/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz
tar -xzf hadoop-3.3.6.tar.gz

# 2. 安装 Spark
wget https://downloads.apache.org/spark/spark-3.4.1/spark-3.4.1-bin-hadoop3.tgz
tar -xzf spark-3.4.1-bin-hadoop3.tgz

# 3. 安装 Redis (消息队列)
sudo apt install redis-server

# 4. 安装 Python 依赖
pip install pyspark celery django djangorestframework
pip install jieba pandas scikit-learn xgboost
```

### 阶段 2：数据采集改造（1 周）
- [ ] 集成 Celery 定时任务
- [ ] 实现增量采集机制
- [ ] 添加数据采集监控

### 阶段 3：存储层改造（2 周）
- [ ] 搭建 HDFS 集群
- [ ] 实现 HDFS ↔ MySQL 数据同步
- [ ] 设计数据分层存储策略

### 阶段 4：Spark 分析（3 周）
- [ ] 数据清洗和预处理
- [ ] 情感分析模型训练
- [ ] 主题挖掘 (LDA)
- [ ] 地域分析

### 阶段 5：可视化开发（2 周）
- [ ] Vue.js 前端框架搭建
- [ ] ECharts 图表开发
- [ ] 数据大屏设计

### 阶段 6：业务系统（2 周）
- [ ] Django 项目搭建
- [ ] 用户管理系统
- [ ] 趋势预测功能
- [ ] 报表导出

---

## 📊 技术栈总览

| 模块 | 技术 | 用途 |
|------|------|------|
| **采集** | Celery + Redis | 定时任务调度 |
| **存储** | Hadoop HDFS | 分布式文件存储 |
| **存储** | MySQL 8.0 | 结构化数据存储 |
| **计算** | Spark 3.4 | 分布式计算 |
| **分析** | Spark MLlib | 机器学习 |
| **分析** | Jieba | 中文分词 |
| **后端** | Django 4 | Web 框架 |
| **后端** | DRF | REST API |
| **前端** | Vue.js 3 | 前端框架 |
| **可视化** | ECharts 5 | 数据可视化 |
| **预测** | XGBoost | 趋势预测 |

---

## 🎯 迁移建议

### 渐进式迁移（推荐）

1. **保留现有 FastAPI**：继续提供 API 服务
2. **新增 Django**：作为业务系统后台
3. **逐步迁移**：
   - 先搭建 Hadoop/Spark 环境
   - 再开发数据采集和预处理
   - 然后实现分析功能
   - 最后开发可视化界面

### 架构演进路线

```
当前架构 → 混合架构 → 目标架构
(1 周)     (1-2 月)    (3-4 月)
```

---

## 📝 下一步行动

1. **评估硬件资源**：确认是否有足够的服务器部署 Hadoop/Spark
2. **学习大数据技术**：Hadoop、Spark、HDFS
3. **分阶段实施**：按照上述 6 个阶段逐步推进
4. **持续集成**：保持现有系统可用，逐步叠加新功能

需要我帮你开始实施哪个模块？
