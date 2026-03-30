from pyspark.sql import DataFrame
from pyspark.sql.functions import col, split, regexp_replace, trim, lower
from loguru import logger


class Tokenizer:
    def __init__(self):
        logger.info("✓ 分词器初始化完成")

    def tokenize(self, df):
        logger.info("开始分词处理...")

        # 使用 Spark SQL 内置函数进行分词（避免 Python UDF）
        # 1. 将文本转换为小写
        df = df.withColumn("text", lower(col("text")))
        
        # 2. 使用空格分割文本
        df = df.withColumn("words", split(col("text"), " "))

        logger.info(f"分词完成，共 {df.count()} 条记录")
        return df