import os
from pyspark import SparkFiles
from pyspark.sql import SparkSession
from modules.config.reader import Configuration
from modules.processing.kafka_stream_processor import KafkaStreamProcessor         


def main():
    spark = SparkSession.builder \
        .appName("KafkaSparkProcessing") \
        .getOrCreate()
    
    log4jLogger = spark._jvm.org.apache.log4j
    logger = log4jLogger.LogManager.getLogger(__name__)

    path = SparkFiles.get("config.yml")
    config = Configuration.load(path)
    prc = KafkaStreamProcessor(spark=spark, 
                               kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SREVERS"), 
                               input_topic=config["kafka_topics"]["raw_data"],
                               output_topic=config["kafka_topics"]["processed_data"], 
                               schema_registry_url=spark.conf.get("spark.kafka.schema.registry.url"),
                               logger=logger)
    try:
        prc.start()
    except Exception as e:
        logger.error("Job failed with error: %s", str(e))
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
