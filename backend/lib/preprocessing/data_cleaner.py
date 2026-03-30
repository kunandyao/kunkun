"""
数据清洗模块
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, length, regexp_replace, trim
from loguru import logger


class DataCleaner:
    """数据清洗器"""

    def __init__(self):
        """初始化数据清洗器"""
        pass

    def clean(self, df: DataFrame) -> DataFrame:
        """清洗数据

        Args:
            df: 原始数据

        Returns:
            DataFrame: 清洗后的数据
        """
        logger.info("开始数据清洗...")

        # 1. 去除重复数据
        df = df.dropDuplicates()

        # 2. 处理缺失值
        df = df.dropna(subset=["text"])

        # 3. 清理文本 - 使用 Spark SQL 内置函数
        # 3.1 去除表情符号
        df = df.withColumn("text", regexp_replace(col("text"), r'[\\uD800-\\uDBFF][\\uDC00-\\uDFFF]', ''))
        
        # 3.2 去除特殊符号
        df = df.withColumn("text", regexp_replace(col("text"), r'[-!@#$%^&*()_+=\\[\\]{};\\\\":|,.<>/?`~]', ' '))
        
        # 3.3 去除多余空格
        df = df.withColumn("text", regexp_replace(col("text"), r'\\s+', ' '))
        
        # 3.4 去除首尾空格
        df = df.withColumn("text", trim(col("text")))

        # 4. 过滤无效数据
        df = df.filter(length(col("text")) > 1)

        logger.info(f"数据清洗完成，剩余 {df.count()} 条数据")
        return df
