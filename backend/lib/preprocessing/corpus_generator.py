"""
标准化语料生成模块
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, concat_ws, length, size
from loguru import logger


class CorpusGenerator:
    """语料生成器"""

    def __init__(self):
        """初始化语料生成器"""
        pass

    def generate(self, df: DataFrame) -> DataFrame:
        """生成标准化语料

        Args:
            df: 分词后的数据

        Returns:
            DataFrame: 标准化语料
        """
        logger.info("开始生成标准化语料...")

        # 1. 生成语料文本（words 为 split 得到的数组，需拼接为字符串）
        df = df.withColumn("corpus", concat_ws(" ", col("words")))

        # 2. 添加文本长度
        df = df.withColumn("text_length", length(col("text")))

        # 3. 词数：words 已是 ARRAY<STRING>，用 size 即可
        df = df.withColumn("word_count", size(col("words")))

        # 4. 过滤无效语料
        df = df.filter(col("word_count") > 0)

        logger.info("✓ 标准化语料生成完成")
        return df
