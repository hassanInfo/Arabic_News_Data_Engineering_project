import os
from airflow import DAG
from datetime import timedelta
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup
from modules.config.reader import Configuration
from airflow.operators.dummy_operator import DummyOperator
from modules.airflow.operators import FetchProduceOperator, ArAnalysisOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator


conf_path = "./etl-config/config.yml"
config = Configuration.load(conf_path)
# platforms = list(config['api']['rapid']['endpoints'].keys())[:3]
platforms = list(config['api']['rapid']['endpoints'].keys())
spark_kafka_dependency = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.2,org.apache.spark:spark-avro_2.12:3.5.2"
app_location =  "./etl-spark-jobs"


def get_spark_conf(n_executor, executor_cores, executor_memory, driver_cores, driver_memory, schema_registry_url):
    return {
        'spark.num.executors': str(n_executor),
        'spark.executor.cores': str(executor_cores),
        'spark.executor.memory': executor_memory,
        'spark.driver.cores': str(driver_cores),
        'spark.driver.memory': driver_memory,
        "spark.kafka.schema.registry.url": schema_registry_url
    }


def news_dag():
    
    with DAG(
        dag_id="news_fetching_and_processing",
        default_args={
            'owner': 'airflow',
            'depends_on_past': False,
            # "email": ["to@gmail.com"],
            # "email_on_failure": True,
            # "email_on_retry": True
        },
        description='Fetch and ingest news into Kafka',
        schedule_interval=timedelta(minutes=30),
        start_date=days_ago(0),
        catchup=False,
    ) as dag:
        
        dummy_task_1 = DummyOperator(
            task_id='start',
            dag=dag
        )
        
        setup_task = SparkSubmitOperator(
            task_id=f"setup_kafka_dependencies",
            conn_id="spark-connection",
            application=f"{app_location}/dummy.py",
            files=conf_path,
            packages=spark_kafka_dependency,
            conf=get_spark_conf(2, 2, '2G', 1, '1G', os.getenv("SCHEMA_REGISTRY_URL")),
            verbose=True
        )
        
        with TaskGroup('fetch_news_to_kafka') as fetch_to_kafka_task_grp:
            for platform in platforms:
                fetch_and_produce_task = FetchProduceOperator(
                    task_id=f'fetch_and_produce_{platform.upper()}',
                    config=config,
                    platform=platform, 
                    api_key=os.getenv("X-RAPID-API-KEY"),
                    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SREVERS"),
                    schema_regestry_url=os.getenv("SCHEMA_REGISTRY_URL")
                    )

                fetch_and_produce_task
                
        process_task = SparkSubmitOperator(
            task_id=f"process",
            conn_id="spark-connection",
            application=f"{app_location}/process.py",
            files=conf_path,
            packages=spark_kafka_dependency,
            conf=get_spark_conf(2, 2, '2G', 1, '1G', os.getenv("SCHEMA_REGISTRY_URL")),
            verbose=True
        )

        analyze_task = ArAnalysisOperator(
                task_id=f"analyze_load",
                config=config,
                api_key=os.getenv("GROQ-API-KEY"),
                bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SREVERS"),
                schema_regestry_url=os.getenv("SCHEMA_REGISTRY_URL")
            )
        
        dummy_task_2 = DummyOperator(
            task_id='end',
            dag=dag
        )
        
        dummy_task_1 >> setup_task >> fetch_to_kafka_task_grp >> process_task >> analyze_task >> dummy_task_2

    return dag


globals()['news_fetching_and_processing'] = news_dag()
