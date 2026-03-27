import pytest
import base64
import json
from datetime import datetime
from src.integrations.agentverse.mapper import AgentVerseAdapter
from src.prediction_engine.models.core import AgentMessage

def test_decode_payload_json():
    data = {"hello": "world"}
    encoded = base64.b64encode(json.dumps(data).encode()).decode()
    
    result = AgentVerseAdapter.decode_payload(encoded)
    assert result == data

def test_decode_payload_text():
    text = "Just some text"
    encoded = base64.b64encode(text.encode()).decode()
    
    result = AgentVerseAdapter.decode_payload(encoded)
    assert result == {"text": "Just some text"}

def test_to_chorus_message():
    # Setup
    payload_data = {"alert": "high"}
    encoded_payload = base64.b64encode(json.dumps(payload_data).encode()).decode()
    timestamp_str = "2023-10-27T10:00:00Z"
    
    av_msg = {
        "uuid": "msg-123",
        "received_at": timestamp_str,
        "envelope": {
            "version": 1,
            "sender": "agent1q...",
            "target": "agent1qTarget...",
            "session": "sess-1",
            "protocol": "proto-1",
            "payload": encoded_payload
        }
    }
    
    # Execute
    msg = AgentVerseAdapter.to_chorus_message(av_msg, sender_alias="MyFriend")
    
    # Verify
    assert isinstance(msg, AgentMessage)
    assert msg.sender_id == "MyFriend"
    assert msg.receiver_id == "agent1qTarget..."
    assert msg.message_type == "agentverse_interop"
    assert msg.content["alert"] == "high"
    assert msg.content["_agentverse_metadata"]["sender_address"] == "agent1q..."
    assert msg.content["_agentverse_metadata"]["uuid"] == "msg-123"
    assert msg.timestamp.year == 2023

def test_to_chorus_message_no_alias():
    av_msg = {
        "envelope": {
            "sender": "agent1q...",
            "payload": "" 
        }
    }
    msg = AgentVerseAdapter.to_chorus_message(av_msg)
    assert msg.sender_id == "agent1q..." # Should fallback to address
