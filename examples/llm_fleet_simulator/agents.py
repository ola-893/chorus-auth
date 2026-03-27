import time
import random
import uuid
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LLMAgent")

class AgentState(Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING_FOR_REVIEW = "waiting_for_review"
    REVIEWING = "reviewing"
    QUARANTINED = "quarantined"

class LLMAgent:
    def __init__(self, agent_id: str, role: str, capabilities: List[str], model: str = "gpt-4"):
        self.agent_id = agent_id
        self.role = role # "coder", "verifier", "researcher"
        self.capabilities = capabilities
        self.model = model
        self.state = AgentState.IDLE
        self.current_task_id: Optional[str] = None
        self.message_log: List[Dict[str, Any]] = []
        self.trust_score = 100
        
        # Simulation parameters
        self.work_speed = 1.0 if "turbo" in model else 2.0 
        self.error_rate = 0.05 # 5% chance of error
        
    def log_event(self, event_type: str, details: Dict[str, Any]):
        """Logs an internal event."""
        logger.info(f"[{self.agent_id}] {event_type}: {details}")

    def receive_message(self, sender_id: str, content: Dict[str, Any]):
        """Handle incoming message from another agent."""
        msg_type = content.get("type")
        self.log_event("RECEIVED_MESSAGE", {"from": sender_id, "type": msg_type})
        
        if msg_type == "request_review":
            self.state = AgentState.REVIEWING
            # Simulate review time
            return self._process_review(sender_id, content)
            
        elif msg_type == "review_feedback":
            # Received feedback
            if content.get("verdict") == "approved":
                self.state = AgentState.IDLE
                self.current_task_id = None
                self.log_event("TASK_COMPLETE", {"task": content.get("task_id")})
            else:
                self.state = AgentState.WORKING
                self.log_event("REVISION_REQUIRED", {"reason": content.get("reason")})
                return self._perform_revision(content.get("task_id"), sender_id)

    def _process_review(self, sender_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate reviewing code."""
        # SIMULATION LOGIC:
        # If this is the 'Deadlock' scenario, we always reject.
        # We can check a global flag or property.
        
        is_deadlock_scenario = content.get("scenario") == "deadlock"
        
        response = {
            "sender_id": self.agent_id,
            "target_id": sender_id,
            "type": "agent_message",
            "content": {
                "type": "review_feedback",
                "task_id": content.get("task_id"),
                "timestamp": time.time()
            }
        }
        
        if is_deadlock_scenario:
            # Rejection Loop
            response["content"]["verdict"] = "rejected"
            response["content"]["reason"] = "Code style violation in line 42. Please fix."
        else:
            response["content"]["verdict"] = "approved"
            
        return response

    def _perform_revision(self, task_id: str, reviewer_id: str) -> Dict[str, Any]:
        """Simulate fixing code."""
        # Send back to reviewer
        return {
            "sender_id": self.agent_id,
            "target_id": reviewer_id,
            "type": "agent_message",
            "content": {
                "type": "request_review",
                "task_id": task_id,
                "scenario": "deadlock", # Persist the scenario tag
                "code_snippet": "def fixed_function(): pass",
                "timestamp": time.time()
            }
        }

    def process_task(self, task: Dict[str, Any], target_agent_id: str) -> Dict[str, Any]:
        """Start a new task (e.g. Write Code)."""
        self.state = AgentState.WORKING
        self.current_task_id = task.get("id")
        self.log_event("START_TASK", {"task": task})
        
        # Simulate work
        time.sleep(0.1) 
        
        self.state = AgentState.WAITING_FOR_REVIEW
        
        # Hand off to verifier
        return {
            "sender_id": self.agent_id,
            "target_id": target_agent_id,
            "type": "agent_message",
            "content": {
                "type": "request_review",
                "task_id": task.get("id"),
                "scenario": task.get("scenario"),
                "code_snippet": "def main(): print('hello')",
                "timestamp": time.time()
            }
        }
