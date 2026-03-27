import sys
import os
import subprocess
import requests
import time
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.config import Settings as Config
from src.logging_config import setup_logging
import asyncio

class ComprehensiveDemo:
    """
    Auto-Pilot Demo Driver for Chorus Video Recording.
    """
    
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.start_time = None

    def log(self, message):
        """Print timestamped log."""
        elapsed = int(time.time() - self.start_time) if self.start_time else 0
        print(f"[{elapsed:03d}s] {message}")

    def trigger(self, scenario_name):
        """Triggers the scenario on the backend."""
        try:
            url = f"{self.api_base}/demo/trigger/{scenario_name}"
            self.log(f"🎬 TRIGGERING SCENARIO: {scenario_name.upper()}...")
            requests.post(url, timeout=2.0)
        except Exception:
            pass

    def run_auto_pilot(self):
        print("\n" + "="*60)
        print("      CHORUS VIDEO DEMO - AUTO PILOT MODE")
        print("="*60)
        print("Timestamps aligned with script:")
        print("  0:00 - Intro & Background Activity")
        print("  0:50 - Lazy Loop Scenario")
        print("  1:20 - Distributed Deadlock Scenario")
        print("  1:50 - Trust Score & Quarantine")
        print("="*60)
        
        print("\n⚠️  SWITCH TO BROWSER NOW. RECORDING STARTS IN 10 SECONDS...")
        for i in range(10, 0, -1):
            print(f" {i}...", end="", flush=True)
            time.sleep(1)
        print("\n\n🎥 ACTION! (Start your voiceover)\n")
        
        self.start_time = time.time()

        # --- 0:00 to 0:50: INTRO & BACKGROUND NOISE ---
        self.log("Phase 1: Background Activity (Intro)...")
        # Send some random 'safe' pings to keep the dashboard alive
        # The backend simulation loop is already running, but we can add specific "good" behavior here if needed.
        # For now, we just wait and let the viewer talk.
        
        time.sleep(10)
        self.log("... (User talking about Architecture) ...")
        
        time.sleep(20)
        self.log("... (User talking about Dashboard Overview) ...")
        
        # We are at T+30s. 20s to go until Lazy Loop.
        time.sleep(20)

        # --- 0:50: LAZY LOOP SCENARIO ---
        self.log("⚠️  Approaching Scene 2: Lazy Loop (T+50s)")
        self.trigger("lazy_loop")
        
        # Wait for 30 seconds (User explains Lazy Loop)
        time.sleep(30)

        # --- 1:20: DEADLOCK SCENARIO ---
        self.log("🚫 Approaching Scene 3: Deadlock (T+80s)")
        self.trigger("deadlock")

        # Wait for 30 seconds (User explains Deadlock)
        time.sleep(30)

        # --- 1:50: QUARANTINE SCENARIO ---
        self.log("🛡️  Approaching Scene 4: Quarantine (T+110s)")
        self.trigger("resource_hog")

        # Wait for closing
        time.sleep(15)
        self.log("✅ Demo Sequence Complete. Fade out.")

if __name__ == "__main__":
    demo = ComprehensiveDemo()
    try:
        demo.run_auto_pilot()
    except KeyboardInterrupt:
        print("\n👋 Demo stopped.")
