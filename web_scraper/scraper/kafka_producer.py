import json
from confluent_kafka import Producer
import os

# Environment variables for Kafka configuration
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "discount_code")
KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "localhost:9092")

def delivery_report(err, msg):
    """
    Callback function to handle delivery reports.
    """
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

def send_discount_data(data: dict) -> None:
    """
    Send discount data to the Kafka topic using Confluent Kafka.

    Args:
        data (dict): A dictionary containing discount information, including:
            - retailer_name: The name of the retailer.
            - description: A detailed description of the discount.
            - discount_code: Unique code for redeeming the discount.
            - expiration_date: Expiration date of the discount.
            - location: Geographical location where the discount is valid.

    Returns:
        None
    """
    # Configure the producer
    producer_config = {
        'bootstrap.servers': KAFKA_BROKER_URL,  # Kafka broker(s)
        'client.id': 'discount-producer'       # Optional: Client ID for tracking
    }
    
    producer = Producer(producer_config)

    try:
        # Serialize the data as JSON and send it to the Kafka topic
        producer.produce(
            topic=KAFKA_TOPIC,
            value=json.dumps(data).encode('utf-8'),
            callback=delivery_report  # Callback for delivery status
        )
        
        # Wait for all messages to be delivered
        producer.flush()
        print(f"Sent discount data to Kafka: {data}")
    
    except Exception as e:
        print(f"Failed to send message: {e}")
