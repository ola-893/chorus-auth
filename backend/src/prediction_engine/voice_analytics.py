"""
Voice alert analytics and optimization engine.
"""
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict

from ..event_bus import event_bus

logger = logging.getLogger(__name__)

class VoiceAlertAnalytics:
    """
    Tracks and analyzes voice alert performance.
    """
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "total_alerts": 0,
            "voice_generated": 0,
            "delivery_failures": 0,
            "response_times": [] 
        }
        self.alert_history: List[Dict] = []
        
        # Subscribe to events
        event_bus.subscribe("voice_generation_success", self._on_voice_success)
        event_bus.subscribe("voice_alert_generated", self._on_alert_generated)
        event_bus.subscribe("intervention_executed", self._on_intervention)

    def _on_voice_success(self, data: Dict):
        self.metrics["voice_generated"] += 1

    def _on_alert_generated(self, data: Dict):
        self.metrics["total_alerts"] += 1
        self.alert_history.append({
            "timestamp": data.get("timestamp", datetime.now().timestamp()),
            "title": data.get("alert_title"),
            "type": "alert"
        })

    def _on_intervention(self, data: Dict):
        """Track response/resolution time relative to last alert."""
        timestamp = datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())).timestamp()
        
        # Find recent alert
        recent_alert = None
        for event in reversed(self.alert_history):
            if event["type"] == "alert" and timestamp - event["timestamp"] < 300: # 5 min window
                recent_alert = event
                break
        
        if recent_alert:
            response_time = timestamp - recent_alert["timestamp"]
            self.metrics["response_times"].append(response_time)

    def get_success_rate(self) -> float:
        """Calculate voice generation success rate."""
        if self.metrics["total_alerts"] == 0:
            return 1.0
        return self.metrics["voice_generated"] / self.metrics["total_alerts"]

    def get_average_response_time(self) -> float:
        """Calculate average response time."""
        times = self.metrics["response_times"]
        if not times:
            return 0.0
        return sum(times) / len(times)

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report."""
        return {
            "period_end": datetime.now().isoformat(),
            "total_voice_alerts": self.metrics["total_alerts"],
            "success_rate": self.get_success_rate(),
            "avg_response_time_seconds": self.get_average_response_time(),
            "optimization_recommendations": self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        recommendations = []
        if self.get_success_rate() < 0.95:
            recommendations.append("Check ElevenLabs API quota or circuit breaker status.")
        
        if self.get_average_response_time() > 60:
            recommendations.append("Voice alert latency high. Consider simplifying scripts for faster generation.")
            
        return recommendations

# Global instance
voice_analytics = VoiceAlertAnalytics()
