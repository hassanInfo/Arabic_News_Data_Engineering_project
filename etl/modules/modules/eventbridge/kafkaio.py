import time
import random
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer, AvroDeserializer
from confluent_kafka import SerializingProducer, DeserializingConsumer


class KafkaIO():
    def __init__(self, bootstrap_servers, schema_regestry_url, logger):
        self.bootstrap_servers = bootstrap_servers
        self.schema_registry_client = SchemaRegistryClient({
            "url": schema_regestry_url
            })
        self.logger = logger

    def delivery_report(self, err, msg):
        if err is not None:
            self.logger.error("Message delivery failed: {}".format(err))
        else:
            self.logger.info(f"Message delivered to topic {msg.topic()} partition [{msg.partition()}] offset {msg.offset()}")

    def get_schema(self, topic):
        key_schema_str = self.schema_registry_client.get_latest_version(f"{topic}_key").schema.schema_str
        value_schema_str = self.schema_registry_client.get_latest_version(f"{topic}_value").schema.schema_str
        return key_schema_str, value_schema_str

    def get_serializers(self, topic):
        key_schema_str, value_schema_str = self.get_schema(topic)
        avro_key_serializer = AvroSerializer(
            self.schema_registry_client,
            key_schema_str
        )
        avro_value_serializer = AvroSerializer(
            self.schema_registry_client,
            value_schema_str
        )
        return (avro_key_serializer, avro_value_serializer)

    def get_deserializers(self, topic):
        key_schema_str, value_schema_str = self.get_schema(topic)
        avro_value_deserializer = AvroDeserializer(
            self.schema_registry_client,
            value_schema_str
        )
        avro_key_deserializer = AvroDeserializer(
            self.schema_registry_client,
            key_schema_str
        )
        return avro_key_deserializer, avro_value_deserializer

    def get_prd_conf(self, topic):
        avro_key_serializer, avro_value_serializer = self.get_serializers(topic)
        conf = {
            "bootstrap.servers": self.bootstrap_servers,
            # "key.serializer": avro_key_serializer,
            "value.serializer": avro_value_serializer
        } 
        return conf
    
    def get_csm_conf(self, topic):
        avro_key_deserializer, avro_value_deserializer = self.get_deserializers(topic)
        conf = {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": "group_1",  
            "auto.offset.reset": "earliest",
            # "key.deserializer": avro_key_deserializer,
            "value.deserializer": avro_value_deserializer
        } 
        return conf        

    def produce(self, topic, data_list):
        p = SerializingProducer(self.get_prd_conf(topic))
        for data in data_list:
            p.poll(0)
            p.produce(topic=topic, value=data, on_delivery=self.delivery_report)
            time.sleep(random.uniform(0.1, 0.5))
        p.flush()

    def consume(self, topic):
        consumer = DeserializingConsumer(self.get_csm_conf(topic))
        consumer.subscribe([topic])
        data = []
        while True:
            msg = consumer.poll(5)
            if msg is None:
                break
            if msg.error():
                self.logger.error(f"kafkaio error: {msg.error()}")
            data.append(msg.value())
            
        consumer.close()  
        return data 

