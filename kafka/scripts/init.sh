
#!/bin/bash

set -e  # Exit on any error

if [ -z "$1" ]; then
  echo "Error: No schema directory provided."
  echo "Usage: $0 <schema-directory>"
  exit 1
fi

SCHEMA_DIR=$1

if [ ! -d "$SCHEMA_DIR" ]; then
  echo "Error: Directory $SCHEMA_DIR does not exist."
  exit 1
fi

SCHEMA_R_URL="http://kafka-schema-registry:8081"
KAFKA_BROKERS="kafka1:19092,kafka2:19093"

echo "Waiting for Kafka and Schema Registry to be ready..."

# Function to wait for a service
wait_for_service() {
  local cmd="$1"
  local message="$2"
  
  until eval "$cmd" > /dev/null 2>&1; do
    echo "$message"
    sleep 2
  done
}

wait_for_service "kafka-topics --bootstrap-server $KAFKA_BROKERS --list" "Waiting for Kafka to be ready..."
wait_for_service "curl -s $SCHEMA_R_URL/subjects" "Waiting for Schema Registry to be ready..."

# Function to create Kafka topic
create_topic() {
  local topic_name=$1

  if ! kafka-topics --bootstrap-server "$KAFKA_BROKERS" --list | grep -q "^$topic_name$"; then
    echo "Creating Kafka topic: $topic_name..."
    kafka-topics --create --topic "$topic_name" --bootstrap-server "$KAFKA_BROKERS" --partitions 1 --replication-factor 2
  else
    echo "Topic $topic_name already exists. Skipping topic creation."
  fi
}

# Function to register schema
register_schema() {
  local topic_name=$1
  local type=$2
  local schema_file=$3
  local schema

  # Read and format schema file
  schema=$(jq -Rs . < "$schema_file")
  if [ -z "$schema" ]; then
    echo "Error: Failed to read schema from $schema_file"
    exit 1
  fi

  local response=$(curl -s -w "%{http_code}" -o /dev/null -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
     --data "{\"schema\": $schema }" "$SCHEMA_R_URL/subjects/${topic_name}_${type}/versions")

  if [[ "$response" -eq 200 || "$response" -eq 201 ]]; then
    echo "Schema for $topic_name ($type) registered successfully."
  else
    echo "Failed to register schema for $topic_name ($type). HTTP response code: $response"
    # exit 1
  fi
}

# Process each schema file
for schema_file in "$SCHEMA_DIR"/*_value.avsc; do
  if [ -f "$schema_file" ]; then
    topic_name=$(basename "$schema_file" _value.avsc)
    create_topic "$topic_name"
    register_schema "$topic_name" "value" "$schema_file"
  fi
done

for schema_file in "$SCHEMA_DIR"/*_key.avsc; do
  if [ -f "$schema_file" ]; then
    topic_name=$(basename "$schema_file" _key.avsc)    
    register_schema "$topic_name" "key" "$schema_file"
  fi
done

echo "Kafka topics and schema registration completed!"

curl -X POST -H "Content-Type: application/json" \
  --data @/config/bigquery-sink.json \
  http://kafka-connect:8083/connectors

echo "Bigquery sink connector has been deployed!"

tail -f /dev/null
