FROM apache/airflow:2.10.3-python3.11

USER root

RUN apt-get update && \
    apt-get install -y gcc python3-dev openjdk-17-jdk && \
    apt-get clean

ENV JAVA_HOME /usr/lib/jvm/java-17-openjdk-amd64

USER airflow

RUN mkdir /opt/airflow/tmp

COPY ./plugins/*.whl /opt/airflow/tmp

RUN pip install /opt/airflow/tmp/etl-4.1.0-py3-none-any.whl

RUN rm -rf /opt/airflow/tmp