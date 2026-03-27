"""
Alert delivery orchestration engine.
"""
import logging
import threading
import time
from queue import PriorityQueue
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .models.alert import ClassifiedAlert, AlertSeverity
from .voice_script_generator import script_generator
from ..integrations.elevenlabs_client import voice_client
from ..event_bus import event_bus
from ..config import settings

logger = logging.getLogger(__name__)

@dataclass(order=True)
class PrioritizedAlert:
    priority: int
    timestamp: float
    alert: ClassifiedAlert = field(compare=False)

class AlertDeliveryEngine:
    """
    Orchestrates the delivery of alerts across multiple channels.
    """
    
    def __init__(self):
        self.alert_queue = PriorityQueue()
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # Priority mapping (lower number = higher priority)
        self.priority_map = {
            AlertSeverity.EMERGENCY: 1,
            AlertSeverity.CRITICAL: 2,
            AlertSeverity.WARNING: 3,
            AlertSeverity.INFO: 4
        }

    def start(self):
        """Start the delivery worker."""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._delivery_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Alert delivery engine started")

    def stop(self):
        """Stop the delivery worker."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2.0)
        logger.info("Alert delivery engine stopped")

    def process_alert(self, alert: ClassifiedAlert) -> bool:
        """
        Enqueue an alert for delivery.
        """
        priority = self.priority_map.get(alert.severity, 5)
        item = PrioritizedAlert(
            priority=priority,
            timestamp=time.time(),
            alert=alert
        )
        self.alert_queue.put(item)
        logger.info(f"Queued alert: {alert.title} (Priority: {priority})")
        return True

    def _delivery_loop(self):
        """Main delivery loop processing the queue."""
        while self.running:
            try:
                if self.alert_queue.empty():
                    time.sleep(0.1)
                    continue
                
                item = self.alert_queue.get(timeout=1.0)
                self._deliver_alert(item.alert)
                self.alert_queue.task_done()
                
            except Exception as e:
                # Log error but keep running
                logger.error(f"Error in delivery loop: {e}")

    def _deliver_alert(self, alert: ClassifiedAlert):
        """Deliver alert to configured channels."""
        try:
            # Determine audience from settings
            audience = "technical"
            if settings.demo.mode_enabled:
                audience = f"{settings.demo.audience}_demo"

            # 1. Generate Script
            script = script_generator.generate_script(alert, audience=audience)
            
            # 2. Voice Channel (if required)
            if alert.requires_voice_alert and voice_client.enabled:
                self._deliver_voice(alert, script)
            
            # 3. System Event (WebSocket/Dashboard)
            self._deliver_system_event(alert, script)
            
            logger.info(f"Delivered alert: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to deliver alert {alert.title}: {e}")

    def _deliver_voice(self, alert: ClassifiedAlert, script: str):
        """Deliver via ElevenLabs."""
        try:
            audio_data = voice_client.generate_alert(script)
            if audio_data:
                # In a real app, we would stream this to a frontend or play it
                # For now, we save it as a file artifact
                incident_id = f"{alert.severity.value}_{int(time.time())}"
                filepath = voice_client.save_audio_file(audio_data, incident_id)
                
                # Notify system of available audio
                event_bus.publish("voice_alert_generated", {
                    "alert_title": alert.title,
                    "audio_path": filepath,
                    "timestamp": time.time()
                })
        except Exception as e:
            logger.error(f"Voice delivery failed: {e}")

    def _deliver_system_event(self, alert: ClassifiedAlert, script: str):
        """Deliver via internal event bus."""
        payload = {
            "type": "system_alert",
            "data": {
                "severity": alert.severity.value,
                "title": alert.title,
                "description": alert.description,
                "script": script,
                "impact": {
                    "system": alert.impact.system_impact_score,
                    "business": alert.impact.business_impact_score
                },
                "timestamp": alert.timestamp.isoformat()
            }
        }
        event_bus.publish("system_alert", payload)

# Global instance
alert_delivery_engine = AlertDeliveryEngine()
