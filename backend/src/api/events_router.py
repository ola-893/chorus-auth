"""
API Router for historical event querying.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime

import json
import os

from ..event_sourcing import event_log_manager

router = APIRouter(prefix="/events", tags=["events"])

@router.get("/demo-live")
async def get_demo_live_events():
    """
    Get live demo events directly from the local log file.
    Bypasses Kafka for immediate frontend updates.
    """
    try:
        # Find project root (one level up from 'backend')
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        # current_file_dir is backend/src/api/
        project_root = os.path.abspath(os.path.join(current_file_dir, "..", "..", ".."))
        log_file = os.path.join(project_root, 'backend', 'logs', 'demo_events.jsonl')
        
        if not os.path.exists(log_file):
            # Try current directory as fallback
            log_file = os.path.join(os.getcwd(), 'logs', 'demo_events.jsonl')
            if not os.path.exists(log_file):
                return {"events": [], "count": 0}
            
        events = []
        with open(log_file, 'r') as f:
            # Read last 50 lines
            lines = f.readlines()[-50:]
            for line in lines:
                try:
                    events.append(json.loads(line))
                except:
                    continue
        
        # Reverse to get newest first
        events.reverse()
        return {"events": events, "count": len(events)}
    except Exception as e:
        return {"events": [], "error": str(e)}

@router.get("/history")
async def get_events_history(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type (message, decision, or all)"),
    start_date: Optional[str] = Query(None, description="Start date in ISO format"),
    end_date: Optional[str] = Query(None, description="End date in ISO format"),
    limit: int = Query(100, description="Max number of events to return", ge=1, le=1000)
):
    """
    Query historical events from the event log (Kafka).
    
    Returns events matching the specified filters, sorted by timestamp.
    """
    try:
        # Parse datetime strings if provided
        start_time = None
        end_time = None
        
        if start_date:
            try:
                start_time = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid start_date format: {start_date}")
        
        if end_date:
            try:
                end_time = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid end_date format: {end_date}")
        
        # If agent_id is provided, use the optimized get_agent_history
        if agent_id:
            events = event_log_manager.get_agent_history(
                agent_id, 
                start_time=start_time,
                end_time=end_time,
                event_type=event_type or "all"
            )
            # Limit results
            events = events[:limit]
        else:
            # For system-wide queries, we need to query both topics
            events = []
            
            # Define filter function
            def event_filter(payload):
                # Filter by event_type if specified
                if event_type and event_type != "all":
                    # This will be set by the topic we're querying
                    return True
                return True
            
            # Query message topic
            if not event_type or event_type in ["message", "all"]:
                msg_topic = event_log_manager.msg_topic
                for event in event_log_manager.replay_events(
                    msg_topic,
                    start_time=start_time,
                    end_time=end_time,
                    filter_func=event_filter,
                    limit=limit
                ):
                    event["type"] = "message"
                    events.append(event)
                    if len(events) >= limit:
                        break
            
            # Query decision topic if we haven't hit limit
            if (not event_type or event_type in ["decision", "all"]) and len(events) < limit:
                decision_topic = event_log_manager.decision_topic
                remaining_limit = limit - len(events)
                for event in event_log_manager.replay_events(
                    decision_topic,
                    start_time=start_time,
                    end_time=end_time,
                    filter_func=event_filter,
                    limit=remaining_limit
                ):
                    event["type"] = "decision"
                    events.append(event)
                    if len(events) >= limit:
                        break
            
            # Sort by timestamp
            events.sort(key=lambda x: x.get("timestamp", 0))
        
        # Format events for frontend consumption
        formatted_events = []
        for event in events:
            formatted_event = {
                "timestamp": event.get("timestamp"),
                "type": event.get("type", "unknown"),
                "source": event.get("value", {}).get("agent_id", "system"),
                "data": event.get("value", {}),
                "offset": event.get("offset"),
                "key": event.get("key")
            }
            formatted_events.append(formatted_event)
        
        return {
            "events": formatted_events,
            "count": len(formatted_events),
            "filters": {
                "agent_id": agent_id,
                "event_type": event_type,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            },
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query events: {str(e)}")
