#!/usr/bin/env python3
"""
Script to list AgentVerse agents associated with your API Key.
Usage: python3 backend/scripts/fetch_my_agents.py
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add src to Python path to allow imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

# Load .env manually if needed, or rely on system env
from dotenv import load_dotenv
load_dotenv("backend/.env")

from src.integrations.agentverse.client import AgentVerseClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    api_key = os.getenv("AGENTVERSE_API_KEY")
    if not api_key:
        print("❌ Error: AGENTVERSE_API_KEY not found in environment.")
        print("Please check your backend/.env file.")
        return

    print(f"🔑 Using API Key: {api_key[:6]}...{api_key[-4:]}")
    print("⏳ Fetching your agents from AgentVerse...")

    client = AgentVerseClient(api_key=api_key)
    
    try:
        agents = await client.get_agents()
        
        if not agents:
            print("\n⚠️  No agents found for this API Key.")
            print("   Go to https://agentverse.ai/agents to create one.")
            return

        print(f"\n✅ Found {len(agents)} agents:\n")
        print(f"{ 'NAME':<20} | { 'ADDRESS':<50} | { 'TYPE':<10}")
        print("-" * 85)
        
        for agent in agents:
            name = agent.get("name", "Unnamed")
            address = agent.get("address", "N/A")
            type_ = agent.get("agent_type", "hosted")
            print(f"{name:<20} | {address:<50} | {type_:<10}")

        print("\n📝 Next Step:")
        print("1. Copy the address of the agent you want to monitor.")
        print("2. Add it to backend/.env:")
        print("   AGENTVERSE_MONITORED_ADDRESS=<paste_address_here>")

    except Exception as e:
        print(f"\n❌ Failed to fetch agents: {e}")

if __name__ == "__main__":
    asyncio.run(main())
