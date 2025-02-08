import json
import logging
from kafka import KafkaConsumer
from django.conf import settings
from .ingest_discount import ingest_discount_data
from celery import shared_task

# Configure logging
logging.basicConfig(level=logging.INFO)

@shared_task
def start_consumer() -> None:
    """
    Start the Kafka consumer to listen for discount messages.

    This function continuously listens for messages on the specified Kafka topic
    and processes them by calling the ingest_discount_data function.

    Returns:
        None
    """
    try:
        consumer = KafkaConsumer(
            'discounts_topic',  # Replace with your Kafka topic name
            bootstrap_servers=settings.KAFKA_BROKER_URL,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='discounts_group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )

        for message in consumer:
            data = message.value
            ingest_discount_data(data)  # Call the ingestion function
    except Exception as e:
        logging.error(f"Error in Kafka consumer: {e}")
