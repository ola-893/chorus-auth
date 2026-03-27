import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def verify_gemini():
    print("\n--- Verifying Gemini API ---")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment.")
        return False
    
    print(f"Key found: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        import google.genai as genai
        # Try listing models as a connection test
        client = genai.Client(api_key=api_key)
        try:
            print("Attempting to list models with google-genai Client...")
            # list() yields models, just take one
            models = client.models.list()
            first_model = next(iter(models), None)
            if first_model:
                print(f"Successfully listed models, found: {first_model.name}")
            else:
                print("Successfully listed models (list empty)")
            print("✅ Gemini API: SUCCESS")
            return True
        except Exception as e:
            print(f"Listing models failed: {e}")
            
            # Try generation as fallback
            try:
                print("Attempting generation with google-genai Client...")
                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp", 
                    contents="Hello"
                )
                print(f"Generation response: {response.text}")
                print("✅ Gemini API: SUCCESS")
                return True
            except Exception as e2:
                print(f"Generation failed: {e2}")
                return False

    except ImportError:
        logger.error("google-genai library not installed.")
        return False
    except Exception as e:
        logger.error(f"Gemini verification failed: {e}")
        return False

def verify_redis():
    print("\n--- Verifying Redis ---")
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", 6379))
    password = os.getenv("REDIS_PASSWORD")
    
    try:
        import redis
        r = redis.Redis(host=host, port=port, password=password, socket_timeout=5)
        if r.ping():
            print(f"Connected to Redis at {host}:{port}")
            print("✅ Redis: SUCCESS")
            return True
    except ImportError:
        logger.error("redis library not installed.")
        return False
    except Exception as e:
        logger.error(f"Redis verification failed: {e}")
        return False

def verify_datadog():
    print("\n--- Verifying Datadog ---")
    api_key = os.getenv("DATADOG_API_KEY")
    app_key = os.getenv("DATADOG_APP_KEY")
    
    if not api_key:
        print("DATADOG_API_KEY not found. Skipping.")
        return None
    
    print(f"API Key found: {api_key[:5]}...{api_key[-5:]}")
    if app_key:
        print(f"APP Key found: {app_key[:5]}...{app_key[-5:]}")
    else:
        print("DATADOG_APP_KEY not found, which may be required.")

    try:
        from datadog_api_client import Configuration, ApiClient
        from datadog_api_client.v1.api.authentication_api import AuthenticationApi
        
        configuration = Configuration()
        configuration.api_key["apiKeyAuth"] = api_key
        configuration.api_key["appKeyAuth"] = app_key
        configuration.server_variables["site"] = os.getenv("DATADOG_SITE", "datadoghq.com")
        
        with ApiClient(configuration) as api_client:
            api_instance = AuthenticationApi(api_client)
            try:
                print("Attempting to validate API key...")
                response = api_instance.validate()
                print(f"Validation response: {response}")
                print("✅ Datadog: SUCCESS")
                return True
            except Exception as e:
                print(f"Datadog API key validation failed: {e}")
                return False
                
    except ImportError:
        logger.error("datadog-api-client not installed.")
        return False
    except Exception as e:
        logger.error(f"Datadog verification failed: {e}")
        return False

def verify_elevenlabs():
    print("\n--- Verifying ElevenLabs ---")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    
    if not api_key:
        print("ELEVENLABS_API_KEY not found. Skipping.")
        return None
    
    print(f"Key found: {api_key[:5]}...{api_key[-5:]}")
        
    try:
        from elevenlabs.client import ElevenLabs
        
        client = ElevenLabs(api_key=api_key)
        try:
            print("Attempting to list voices...")
            voices = client.voices.get_all()
            print(f"Successfully retrieved {len(voices.voices)} voices.")
            print("✅ ElevenLabs: SUCCESS")
            return True
        except Exception as e:
            print(f"ElevenLabs API call failed: {e}")
            return False
            
    except ImportError:
        logger.error("elevenlabs library not installed.")
        return False
    except Exception as e:
        logger.error(f"ElevenLabs verification failed: {e}")
        return False

def verify_kafka():
    print("\n--- Verifying Kafka ---")
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap_servers:
        print("KAFKA_BOOTSTRAP_SERVERS not found. Skipping.")
        return None
    
    print(f"Bootstrap Servers: {bootstrap_servers}")
    
    try:
        from confluent_kafka.admin import AdminClient
        
        conf = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'verify-keys-script'
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

        print("Connecting to Kafka...")
        admin_client = AdminClient(conf)
        
        # list_topics returns a ClusterMetadata object
        metadata = admin_client.list_topics(timeout=10)
        
        if metadata.topics:
            print(f"Successfully connected. Found {len(metadata.topics)} topics.")
            print(f"Topics: {', '.join(list(metadata.topics.keys())[:5])}...")
            print("✅ Kafka: SUCCESS")
            return True
        else:
            print("Connected but no topics found (or permission issue).")
            print("✅ Kafka: SUCCESS (Empty cluster)")
            return True
            
    except ImportError:
        logger.error("confluent_kafka library not installed.")
        return False
    except Exception as e:
        logger.error(f"Kafka verification failed: {e}")
        return False

def main():
    if load_dotenv(override=True):
        print("Environment variables loaded from .env file.")
    else:
        print("No .env file found or unable to load.")
    
    verify_redis()
    verify_gemini()
    verify_datadog()
    verify_elevenlabs()
    verify_kafka()

if __name__ == "__main__":
    main()