import pyspark.sql.functions as func
from pyspark.sql.types import BinaryType
from pyspark.sql.avro.functions import from_avro, to_avro
from confluent_kafka.schema_registry import SchemaRegistryClient


class KafkaStreamProcessor:
    def __init__(self, spark, kafka_bootstrap_servers, input_topic, output_topic, schema_registry_url, logger):
        self.spark = spark
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.logger = logger
        self.schema_registry_client = SchemaRegistryClient({
            "url": schema_registry_url
            })

    def read_from_kafka(self):
        self.logger.info(f"Reading data from Kafka topic: {self.input_topic}")
        return self.spark.read \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_bootstrap_servers) \
            .option("subscribe", self.input_topic) \
            .option("kafka.group.id", "group_1") \
            .option("startingOffsets", "earliest") \
            .option("endingOffsets", "latest") \
            .load()

    def transform_data(self, raw_data):
        self.logger.info("Processing data...")
        value_schema_str = self.schema_registry_client.get_latest_version(f"{self.input_topic}_value").schema.schema_str
        raw_data = raw_data.withColumn('fixed_value', func.expr("substring(value, 6, length(value)-5)"))
        parsed_data = raw_data.select(
            from_avro(func.col("fixed_value"), value_schema_str, {"mode": "PERMISSIVE"}).alias("data")
                ).select("data.*")
        # self.logger.debug("debug-1 "+"*"*80)
        # parsed_data.show(1, truncate=False)
        processed_data = parsed_data \
            .filter(func.col("url").isNotNull()) \
            .na.fill({"url": "No url", "title": "Untitled", "content": "No Content", "source": "Unknown"}) \
            .withColumn("title", func.trim(func.col("title"))) \
            .withColumn("date", func.trim(func.col("date"))) \
            .withColumn("image", func.trim(func.col("image"))) \
            .withColumn("content", func.trim(func.col("content"))) \
            .withColumn("url", func.trim(func.col("url"))) \
            .withColumn("source", func.trim(func.col("source"))) \
            .withColumn("word_count", func.size(func.split(func.col("content"), " "))) \
            .withColumn("processed", func.lit(True))
        # self.logger.debug("debug-2 "+"*"*80)
        # processed_data.show(truncate=False)
        return processed_data

    def write_to_kafka(self, processed_data):
        self.logger.info(f"The data is : {processed_data}")
        self.logger.info(f"Writing data to Kafka topic: {self.output_topic}")
        value_latest_version = self.schema_registry_client.get_latest_version(f"{self.output_topic}_value")
        
        # processed_data.printSchema()
        processed_data = processed_data.select(
            # to_avro(lit("data"), key_schema_str).alias("key"),
            to_avro(func.struct(
                "title", 
                "date", 
                "image", 
                "content", 
                "url", 
                "source", 
                "word_count",
                "processed"), 
                value_latest_version.schema.schema_str).alias("value")
                )
        
        # self.logger.debug("debug-3 "+"*"*80)
        # processed_data.show(truncate=False)
        int_to_binary_udf = func.udf(lambda value, byte_size: (value).to_bytes(byte_size, byteorder='big'), BinaryType())
        magicByteBinary = int_to_binary_udf(func.lit(0), func.lit(1))
        schemaIdBinary = int_to_binary_udf(func.lit(value_latest_version.schema_id), func.lit(4))
        processed_data = processed_data.withColumn("value", func.concat(magicByteBinary, schemaIdBinary, func.col("value")))
        # self.logger.debug("debug-4 "+"*"*80)
        # processed_data.show(truncate=False)
        # processed_data = processed_data.withColumn(
        # "value",
        # func.concat(
        #     func.encode(func.lit(0).cast("int"), "big"),  # Magic byte (0)
        #     func.encode(func.lit(value_latest_version.schema_id).cast("int"), "big"),  # Schema ID
        #     func.col("value")
        # )
        # )
        # self.logger.debug("debug-4 "+"*"*80)
        # processed_data.show(truncate=False)
        # self.logger.debug("debug-5 "+"*"*80)
        processed_data.write \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_bootstrap_servers) \
            .option("topic", self.output_topic) \
            .option("checkpointLocation", "/tmp/spark-checkpoints") \
            .save()

    def start(self):
        self.logger.info("Starting Kafka Spark Job...")
        raw_data = self.read_from_kafka()
        processed_data = self.transform_data(raw_data)
        self.write_to_kafka(processed_data)