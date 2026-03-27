import sys
sys.path.append('.')
from src.config import settings
print(f"Settings Kafka Enabled: {settings.kafka.enabled}")

from src.integrations.kafka_client import KafkaMessageBus, Producer
print(f"Producer class: {Producer}")

bus = KafkaMessageBus()
print(f"Bus Enabled: {bus.enabled}")