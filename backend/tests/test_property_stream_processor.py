"""
Property-based tests for Stream Processor.

**Feature: Real-Time Data Flow**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**
"""
import pytest
import time
from datetime import datetime
from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st, settings, HealthCheck

from src.stream_processor import StreamProcessor

class TestStreamProcessor:
    
    @given(
        agent_ids=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
            min_size=1, max_size=5
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_stream_processing_pipeline_integration(self, agent_ids):
        """
        Property 4: Stream processing pipeline integration.
        Validates: Requirements 2.1, 2.2
        
        Input messages should result in output decisions.
        """
        with patch('src.stream_processor.kafka_bus') as mock_bus:
            processor = StreamProcessor()
            
            # Generate valid message structures
            mock_msgs = []
            for agent_id in agent_ids:
                valid_message = {
                    "agent_id": agent_id,
                    "resource_type": "cpu",
                    "requested_amount": 50,
                    "priority_level": 5,
                    "timestamp": datetime.now().isoformat()
                }
                mock_msg = {
                    "value": valid_message,
                    "key": f"key_{agent_id}",
                    "topic": processor.input_topic,
                    "offset": 0,
                    "partition": 0
                }
                mock_msgs.append(mock_msg)
            
            # Process each message
            for msg in mock_msgs:
                processor._process_message(msg)
                
            # Verify production to output topic
            expected_count = len(agent_ids)
            assert mock_bus.produce.call_count == expected_count
            
            # Verify arguments only if there were calls made
            if expected_count > 0:
                args, _ = mock_bus.produce.call_args
                assert args[0] == processor.output_topic
                assert "status" in args[1] # Decision object

    @given(
        agent_id=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    def test_property_processing_error_routing(self, agent_id):
        """
        Property 5: Processing error routing.
        Validates: Requirements 2.3
        
        Errors should be routed to DLQ.
        """
        with patch('src.stream_processor.kafka_bus') as mock_bus:
            processor = StreamProcessor()
            
            # Create a valid message structure that will cause processing error
            valid_message = {
                "agent_id": agent_id,
                "resource_type": "cpu",
                "requested_amount": 50,
                "priority_level": 5,
                "timestamp": datetime.now().isoformat()
            }
            
            # Simulate a message that causes an error during analysis
            with patch.object(processor, '_analyze_intention', side_effect=Exception("Processing Failed")):
                msg = {
                    "value": valid_message,
                    "key": f"key_{agent_id}"
                }
                
                processor._process_message(msg)
                
                # Should produce to DLQ
                mock_bus.produce.assert_called_with(
                    processor.dlq_topic,
                    {
                        "original_message": msg,
                        "error": "Processing Failed",
                        "timestamp": pytest.approx(time.time(), 1.0)
                    },
                    key=f"key_{agent_id}"
                )

    @given(
        message_sequence=st.lists(st.integers(), min_size=2, max_size=10)
    )
    def test_property_agent_specific_message_ordering(self, message_sequence):
        """
        Property 6: Agent-specific message ordering.
        Validates: Requirements 2.4
        
        Messages should be processed in order.
        """
        # Since _process_message is synchronous, ordering is guaranteed by the caller (poll loop).
        # We verify that we process what we receive in order.
        
        processed_sequence = []
        
        class MockProcessor(StreamProcessor):
            def _analyze_intention(self, intention):
                processed_sequence.append(intention.requested_amount)  # Use requested_amount as sequence
                return {}

        processor = MockProcessor()
        
        with patch('src.stream_processor.kafka_bus'):
            for seq in message_sequence:
                # Create valid message with all required fields
                msg = {
                    "value": {
                        "agent_id": "ordered_agent",
                        "resource_type": "cpu",
                        "requested_amount": seq,
                        "priority_level": 5,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                processor._process_message(msg)
        
        assert processed_sequence == message_sequence
