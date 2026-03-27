#!/usr/bin/env python3
import os
import re

def update_env_file(env_path, updates):
    """Updates the .env file with new values."""
    if not os.path.exists(env_path):
        print(f"❌ Error: {env_path} not found.")
        return

    with open(env_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    keys_updated = set()

    for line in lines:
        key_match = re.match(r'^([A-Z_]+)=', line)
        if key_match:
            key = key_match.group(1)
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                keys_updated.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Append new keys if they didn't exist
    for key, value in updates.items():
        if key not in keys_updated:
            new_lines.append(f"{key}={value}\n")

    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"✅ Updated {env_path}")

def main():
    print("=== Confluent Cloud Configuration Setup ===")
    print("Please enter your Confluent Cloud details.")
    print("(Press Enter to keep existing value if unsure, but Bootstrap Server MUST be changed from localhost)")
    
    bootstrap = input("\nBootstrap Server (e.g., pkc-xxxxx.region.provider.confluent.cloud:9092): ").strip()
    api_key = input("API Key (SASL_USERNAME): ").strip()
    api_secret = input("API Secret (SASL_PASSWORD): ").strip()
    
    updates = {
        "KAFKA_ENABLED": "true",
        "KAFKA_SECURITY_PROTOCOL": "SASL_SSL",
        "KAFKA_SASL_MECHANISM": "PLAIN"
    }

    if bootstrap:
        updates["KAFKA_BOOTSTRAP_SERVERS"] = bootstrap
    if api_key:
        updates["KAFKA_SASL_USERNAME"] = api_key
    if api_secret:
        updates["KAFKA_SASL_PASSWORD"] = api_secret

    env_path = os.path.join("backend", ".env")
    update_env_file(env_path, updates)
    
    print("\n✅ Configuration updated. Please restart your services.")

if __name__ == "__main__":
    main()
