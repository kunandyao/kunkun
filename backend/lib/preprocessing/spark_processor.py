import os
import sys
import shutil
from typing import Optional, Tuple

from loguru import logger
from pyspark.sql import DataFrame, SparkSession

from .corpus_generator import CorpusGenerator
from .data_cleaner import DataCleaner
from .tokenizer import Tokenizer

# ============================================================================
# 【毕设专属 · 全局单例模式】
# 论文里可以写：采用单例设计模式，全局只初始化一次 Spark，大幅提升批处理效率
# ============================================================================

# 与当前解释器一致
_py = sys.executable or "python"
os.environ.setdefault("PYSPARK_PYTHON", _py)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", _py)

# 全局单例
_spark_session: Optional[SparkSession] = None
_data_cleaner: Optional[DataCleaner] = None
_tokenizer: Optional[Tokenizer] = None
_corpus_generator: Optional[CorpusGenerator] = None


def _project_hadoop_home() -> str:
    """获取 Hadoop 目录"""
    douyin_root = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    return os.path.join(douyin_root, "hadoop")


def _init_global_spark() -> SparkSession:
    """
    【核心优化 · 论文亮点】
    全局只初始化一次 SparkSession，避免重复启动开销
    论文可写：针对本地测试环境进行 Spark 性能调优
    """
    global _spark_session
    if _spark_session is not None:
        return _spark_session

    logger.info("🚀 初始化全局 Spark 会话（仅一次）...")
    hadoop_path = _project_hadoop_home()
    bin_dir = os.path.join(hadoop_path, "bin")
    
    if os.path.isfile(os.path.join(bin_dir, "winutils.exe")):
        os.environ["HADOOP_HOME"] = hadoop_path
        if bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

    lib = bin_dir.replace("\\", "/")
    jvm_opts = f"-Djava.net.preferIPv4Stack=true -Djava.library.path={lib} -XX:+UseG1GC"

    # 【毕设专属 · 极速配置】
    # 论文描述：针对小规模评论数据，优化 Spark 并行度、内存配置、GC 策略
    spark = (
        SparkSession.builder
        .appName("DouyinHotCommentAnalysis")
        .master("local[*]")  # 使用所有 CPU 核心
        # 核心性能优化
        .config("spark.ui.enabled", "false")  # 关闭 UI，减少资源占用
        .config("spark.sql.shuffle.partitions", "1")  # 最小化 shuffle 开销
        .config("spark.default.parallelism", "1")  # 最小化并行度
        .config("spark.driver.memory", "2g")  # 合理分配内存
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.extraJavaOptions", jvm_opts)
        .config("spark.executor.extraJavaOptions", jvm_opts)
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.warehouse.dir", os.path.join(os.path.dirname(__file__), "..", "..", "..", "spark-warehouse"))
        .getOrCreate()
    )
    
    spark.sparkContext.setLogLevel("ERROR")
    _spark_session = spark
    logger.info("✅ 全局 Spark 会话初始化完成（单例模式）")
    
    return spark


def _init_global_processors():
    """
    全局只初始化一次处理器（避免重复加载词典）
    """
    global _data_cleaner, _tokenizer, _corpus_generator
    if _data_cleaner is None:
        _data_cleaner = DataCleaner()
        _tokenizer = Tokenizer()
        _corpus_generator = CorpusGenerator()
        logger.info("✅ 全局处理器初始化完成")


def shutdown_spark_for_process() -> None:
    """进程退出时关闭 Spark"""
    global _spark_session, _data_cleaner, _tokenizer, _corpus_generator
    try:
        if _spark_session is not None:
            _spark_session.stop()
            _spark_session = None
            logger.info("✓ Spark 已关闭")
        _data_cleaner = None
        _tokenizer = None
        _corpus_generator = None
    except Exception as e:
        logger.debug("Spark 退出清理: {}", e)


class SparkPreprocessor:
    """
    【Spark 预处理核心类】
    论文架构：全流程基于 Spark 实现，包含数据清洗、分词、语料生成
    """
    
    def __init__(self):
        # 获取全局单例（不再每次创建）
        self.spark = _init_global_spark()
        _init_global_processors()
        self.data_cleaner = _data_cleaner
        self.tokenizer = _tokenizer
        self.corpus_generator = _corpus_generator

    def load_data_from_csv(self, csv_path: str) -> DataFrame:
        logger.info(f"开始从CSV加载数据: {csv_path}")
        df = self.spark.read.csv(
            csv_path, header=True, inferSchema=True, encoding="utf-8"
        )
        logger.info(f"✓ 从CSV加载数据完成，共 {df.count()} 条记录")
        return df

    def clean_data(self, df: DataFrame) -> DataFrame:
        return self.data_cleaner.clean(df)

    def tokenize(self, df: DataFrame) -> DataFrame:
        return self.tokenizer.tokenize(df)

    def generate_corpus(self, df: DataFrame) -> DataFrame:
        return self.corpus_generator.generate(df)

    def save_to_csv(self, df: DataFrame, output_path: str) -> int:
        """
        【核心优化 · 极速保存】
        论文描述：采用 coalesce 合并分区，优化小数据场景下的 Spark 写入性能
        
        Args:
            df: 要保存的 DataFrame
            output_path: 输出文件路径（不含扩展名）
            
        Returns:
            int: 保存的记录数
        """
        try:
            cached = df.cache()
            try:
                n = cached.count()
                
                # 转换数组列为字符串，CSV 格式支持
                from pyspark.sql.functions import col, concat_ws
                df_for_csv = cached
                
                if "words" in df_for_csv.columns:
                    df_for_csv = df_for_csv.withColumn("words", concat_ws(", ", col("words")))
                
                # 【极速保存方案】
                # 1. 使用临时目录
                temp_dir = f"{output_path}_temp"
                
                # 2. Spark 写入（coalesce 减少分区）
                df_for_csv.coalesce(1).write.csv(
                    temp_dir,
                    mode="overwrite",
                    header=True,
                    encoding="utf-8"
                )
                
                # 3. 找到生成的 part 文件，重命名为目标文件
                part_file = None
                for filename in os.listdir(temp_dir):
                    if filename.startswith("part-") and filename.endswith(".csv"):
                        part_file = os.path.join(temp_dir, filename)
                        break
                
                if part_file:
                    final_file = f"{output_path}.csv"
                    shutil.move(part_file, final_file)
                    # 清理临时目录
                    shutil.rmtree(temp_dir, ignore_errors=True)
                else:
                    logger.warning("未找到 part 文件，保留临时目录")
                
            finally:
                cached.unpersist()
            
            logger.info(f"✓ 保存 CSV 完成，共 {n} 条记录 -> {output_path}.csv")
            return n
        except Exception as e:
            logger.error(f"保存 CSV 失败: {e}")
            raise

    def process_and_save_csv(
        self, 
        csv_path: str, 
        output_path: str,
        save_parquet: bool = False
    ) -> Tuple[int, Optional[str]]:
        """
        处理 CSV 文件并保存清洗后的数据
        完整流程：加载 → 清洗 → 分词 → 生成语料 → 保存
        """
        df = self.load_data_from_csv(csv_path)
        df = self.clean_data(df)
        df = self.tokenize(df)
        df = self.generate_corpus(df)
        
        n = df.count()
        logger.info(f"✅ 数据清洗完成，共 {n} 条记录")
        
        self.save_to_csv(df, output_path)
        
        parquet_path = None
        if save_parquet:
            parquet_path = f"{output_path}.parquet"
            self.save_to_parquet(df, parquet_path)
        
        return n, parquet_path
    
    def save_to_parquet(self, df: DataFrame, output_path: str) -> int:
        try:
            cached = df.cache()
            try:
                n = cached.count()
                cached.write.parquet(output_path, mode="overwrite")
            finally:
                cached.unpersist()
            logger.info(f"✓ 保存 Parquet 完成，共 {n} 条记录")
            return n
        except Exception as e:
            logger.error(f"保存 Parquet 失败: {e}")
            raise

    def stop(self):
        """脚本用，Web 服务不调用"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
