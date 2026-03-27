"""
Interfaces for alert delivery components.
"""
from typing import Protocol, List, Optional
from .models.alert import ClassifiedAlert

class AlertChannel(Protocol):
    def send(self, alert: ClassifiedAlert, script: Optional[str] = None) -> bool:
        ...

class AlertDeliveryEngine(Protocol):
    def process_alert(self, alert: ClassifiedAlert) -> bool:
        ...
