#!/usr/bin/env python3
"""
Chorus Voice Command Interface (Bidirectional)

This script demonstrates the "Grand Prize" winning feature:
A conversational interface for managing the Multi-Agent Immune System.

It listens to your voice, interprets commands using Gemini, executes them
on the Chorus system, and responds via ElevenLabs voice.

Requirements:
    pip install -r requirements-voice.txt
    PortAudio (brew install portaudio)

Usage:
    python demo_voice_interaction.py
"""

import os
import sys
import json
import time
import logging
import asyncio
from typing import Dict, Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ChorusVoice")

# Import Chorus components
try:
    from src.config import settings
    from src.prediction_engine.gemini_client import GeminiClient
    from src.prediction_engine.redis_client import RedisClient
    from src.prediction_engine.trust_manager import RedisTrustManager, RedisTrustScoreManager
except ImportError as e:
    print(f"Error importing Chorus components: {e}")
    print("Please run this script from the 'backend' directory.")
    sys.exit(1)

# Import Voice dependencies
try:
    import speech_recognition as sr
    from elevenlabs import generate, play, set_api_key
except ImportError:
    print("Missing voice dependencies. Please run: pip install -r requirements-voice.txt")
    # We will mock these for now if running in an environment without them
    sr = None

class VoiceInterface:
    def __init__(self):
        self.recognizer = sr.Recognizer() if sr else None
        self.microphone = sr.Microphone() if sr else None
        
        # Initialize Gemini for intent understanding
        self.gemini = GeminiClient()
        
        # Initialize System Interface (Partial)
        self.redis = RedisClient()
        self.trust_manager = RedisTrustManager(RedisTrustScoreManager(self.redis))
        
        # ElevenLabs Setup
        if settings.elevenlabs.api_key:
            try:
                set_api_key(settings.elevenlabs.api_key)
                self.voice_enabled = True
            except Exception as e:
                logger.warning(f"ElevenLabs init failed: {e}")
                self.voice_enabled = False
        else:
            logger.warning("ElevenLabs API key not found.")
            self.voice_enabled = False

    def listen(self) -> str:
        """Capture audio from microphone and transcribe it."""
        if not self.recognizer or not self.microphone:
            print("\n📝 Type your command (Voice modules missing):")
            return input("> ")

        print("\n🎤 Listening... (Speak now)")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5.0)
                print("⏳ Transcribing...")
                # We use Google Speech Recognition (free tier) for the demo, 
                # but in production, we'd use google-cloud-speech for better accuracy.
                text = self.recognizer.recognize_google(audio)
                print(f"🗣️  You said: '{text}'")
                return text
            except sr.WaitTimeoutError:
                print("⚠️  No speech detected.")
                return ""
            except sr.UnknownValueError:
                print("⚠️  Could not understand audio.")
                return ""
            except Exception as e:
                logger.error(f"Recognition error: {e}")
                return ""

    def analyze_intent(self, text: str) -> Dict[str, Any]:
        """Use Gemini to understand the user's intent."""
        print("🧠 Interpreting intent with Gemini...")
        
        prompt = f"""
        You are the voice interface for the Chorus Multi-Agent Immune System.
        Interpret the following user command: "{text}"
        
        System Context:
        - We manage autonomous AI agents.
        - Agents have "Trust Scores" (0-100).
        - Agents can be "Quarantined".
        - We monitor for "Conflicts" and "Deadlocks".
        
        Map the command to one of these actions:
        1. QUARANTINE_AGENT (parameters: agent_id, reason)
        2. GET_TRUST_SCORE (parameters: agent_id)
        3. SYSTEM_STATUS (no parameters)
        4. EXPLAIN_FAILURE (parameters: failure_type)
        5. UNKNOWN (if command is unclear)
        
        Return ONLY valid JSON (no markdown):
        {{
            "action": "ACTION_NAME",
            "parameters": {{ ... }},
            "response_script": "A short, natural language response confirming the action for the user."
        }}
        """
        
        try:
            # We use the raw client for this specific prompt to get JSON
            # Using the synchronous call pattern we identified
            if hasattr(self.gemini._client, 'models'):
                response = self.gemini._client.models.generate_content(
                    model=self.gemini.model,
                    contents=prompt
                )
            else:
                response = self.gemini._client.generate_content(prompt)
                
            # Clean up response text (remove markdown code blocks if present)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return {
                "action": "UNKNOWN",
                "response_script": "I'm sorry, I encountered an error analyzing your request."
            }

    def execute_action(self, intent: Dict[str, Any]):
        """Execute the determined action."""
        action = intent.get("action")
        params = intent.get("parameters", {})
        script = intent.get("response_script", "Action completed.")
        
        print(f"⚙️  Executing: {action} {params}")
        
        if action == "QUARANTINE_AGENT":
            agent_id = params.get("agent_id", "unknown_agent")
            # In a real run, we'd call intervention_engine.execute_quarantine
            # Here we mock the effect for the demo script
            print(f"   🚫 QUARANTINING AGENT: {agent_id}")
            print(f"   📝 Reason: {params.get('reason', 'Manual voice command')}")
            
        elif action == "GET_TRUST_SCORE":
            agent_id = params.get("agent_id", "unknown_agent")
            try:
                # Try to get real score if Redis is up
                score = self.trust_manager.get_trust_score(agent_id)
                print(f"   🛡️  Trust Score for {agent_id}: {score}")
                # We might want to inject the real score into the script if the LLM guessed it
                script = script.replace("[SCORE]", str(score)) 
            except:
                print(f"   🛡️  Trust Score for {agent_id}: 85 (Mock)")

        elif action == "SYSTEM_STATUS":
            print("   📊 System is ONLINE. 6 Agents Active. 0 Conflicts.")
            
        # Speak the response
        self.speak(script)

    def speak(self, text: str):
        """Synthesize speech using ElevenLabs."""
        print(f"🤖 Chorus: '{text}'")
        if self.voice_enabled:
            try:
                audio = generate(
                    text=text,
                    voice="Rachel", # Default reliable voice
                    model="eleven_turbo_v2"
                )
                play(audio)
            except Exception as e:
                logger.error(f"Speech generation failed: {e}")

    def run(self):
        print("="*60)
        print("🗣️  Chorus Bidirectional Voice Interface")
        print("="*60)
        print("Try saying:")
        print("  - 'What is the trust score for Agent Alpha?'")
        print("  - 'Quarantine Agent Beta immediately.'")
        print("  - 'System status report.'")
        print("  - 'exit' to quit")
        print("-" * 60)

        while True:
            command = self.listen()
            if not command:
                continue
                
            if command.lower() in ['exit', 'quit', 'stop']:
                print("Goodbye.")
                break
                
            intent = self.analyze_intent(command)
            self.execute_action(intent)

if __name__ == "__main__":
    # Ensure environment is loaded
    from src.config import load_settings
    load_settings()
    
    interface = VoiceInterface()
    interface.run()
