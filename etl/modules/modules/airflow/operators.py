from time import sleep
from airflow.models.baseoperator import BaseOperator


class FetchProduceOperator(BaseOperator):
    def __init__(self, api_key: str, config: dict, platform: str, bootstrap_servers: str, schema_regestry_url : str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key
        self.config = config
        self.platform = platform
        self.bootstrap_servers = bootstrap_servers
        self.schema_regestry_url = schema_regestry_url

    def execute(self, context):
        from modules.eventbridge.kafkaio import KafkaIO
        from modules.ingestion.extractor import NewsAPIClient

        extractor = NewsAPIClient(
            api_key=self.api_key, 
            base_url=self.config["api"]["rapid"]["base_url"], 
            endpoints=self.config["api"]["rapid"]["endpoints"], 
            retries=self.config["api"]["rapid"]["retry_attempts"], 
            timeout=self.config["api"]["rapid"]["request_timeout"],
            logger=self.log
            )
        data_list = extractor.fetch_and_prepare_news(self.platform)
        data_list = data_list[:self.config["api"]["rapid"]["limit_articles"]]
        KafkaIO(
            bootstrap_servers=self.bootstrap_servers,
            schema_regestry_url = self.schema_regestry_url,
            logger=self.log
            ).produce(
                topic=self.config['kafka_topics']['raw_data'],
                data_list=data_list
                )


class ArAnalysisOperator(BaseOperator):
    def __init__(self, api_key: str, config: dict, bootstrap_servers: str, schema_regestry_url : str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key
        self.config = config
        self.bootstrap_servers = bootstrap_servers
        self.schema_regestry_url = schema_regestry_url

    def execute(self, context):
        from modules.eventbridge.kafkaio import KafkaIO
        from modules.processing.nlp_analyzer import ArabicNLPAnalyzer

        analyzer = ArabicNLPAnalyzer(
            api_key=self.api_key,
            model=self.config["api"]["groq"]["model"],
            temperature=self.config["api"]["groq"]["temperature"],
            maxtokens=self.config["api"]["groq"]["maxtokens"],
            logger=self.log
            )
        
        kafkaio = KafkaIO(
            bootstrap_servers=self.bootstrap_servers,
            schema_regestry_url = self.schema_regestry_url,
            logger=self.log
            )

        processed_list = kafkaio.consume(
            topic=self.config['kafka_topics']['processed_data']
            )

        self.log.info(f"Total number to analyze: {len(processed_list)}")
        for i, item in enumerate(processed_list):
            self.log.info(i)
            user_prompt = item["content"]
            user_prompt = user_prompt[: self.config["api"]["groq"]["limit_tokens"]]
            result = analyzer.run_conversation(user_prompt)
            item["topic"] = result["topic"]
            item["geolocations"] = result["geolocations"]
            item["entities"] = result["entities"]
            sleep(3)

        kafkaio.produce(
            topic=self.config['kafka_topics']['analyzed_data'],
            data_list=processed_list
            )            
