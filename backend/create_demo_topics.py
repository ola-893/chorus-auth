import os
import sys
from confluent_kafka.admin import AdminClient, NewTopic
from dotenv import load_dotenv

# Load environment variables
print(f"CWD: {os.getcwd()}")
load_dotenv(dotenv_path='.env', override=True)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093")
print(f"Loaded KAFKA_BOOTSTRAP_SERVERS: {KAFKA_BOOTSTRAP_SERVERS}")
print(f"Loaded KAFKA_SASL_MECHANISM: {os.getenv('KAFKA_SASL_MECHANISM')}")

def create_topics():
    print(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
    
    conf = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'client.id': 'create-topics-script'
    }
    
    security_protocol = os.getenv("KAFKA_SECURITY_PROTOCOL")
    if security_protocol:
        conf['security.protocol'] = security_protocol
        
    sasl_mechanism = os.getenv("KAFKA_SASL_MECHANISM")
    if sasl_mechanism:
        conf['sasl.mechanism'] = sasl_mechanism
        
    sasl_username = os.getenv("KAFKA_SASL_USERNAME")
    if sasl_username:
        conf['sasl.username'] = sasl_username
        
    sasl_password = os.getenv("KAFKA_SASL_PASSWORD")
    if sasl_password:
        conf['sasl.password'] = sasl_password
    
    print(f"Debug: Config keys: {list(conf.keys())}")
    print(f"Debug: SASL Mechanism: {conf.get('sasl.mechanism')}")
    
    admin_client = AdminClient(conf)

    topics = [
        "agent-messages-raw",
        "agent-decisions-processed",
        "system-alerts",
        "causal-graph-updates",
        "analytics-metrics"
    ]

    new_topics = [NewTopic(topic, num_partitions=1, replication_factor=3) for topic in topics]

    # Call create_topics to asynchronously create topics.
    fs = admin_client.create_topics(new_topics)

    # Wait for each operation to finish.
    for topic, f in fs.items():
        try:
            f.result()  # The result itself is None
            print(f"Topic '{topic}' created successfully.")
        except Exception as e:
            print(f"Failed to create topic '{topic}': {e}")

if __name__ == "__main__":
    create_topics()