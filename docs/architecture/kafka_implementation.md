# Kafka Message Buffering Implementation

## Overview
This document describes the implementation of message buffering for Kafka reconnection, which ensures that messages are not lost during temporary connection failures.

## Implementation Details

### Core Components

#### 1. Message Buffer
- **Type**: `collections.deque` with configurable max length
- **Default Size**: 1000 messages (configurable via `KAFKA__BUFFER_SIZE`)
- **Behavior**: FIFO queue that automatically drops oldest messages when full

#### 2. Connection State Tracking
- **Variable**: `_is_connected` (boolean)
- **Integration**: Circuit breaker state change callbacks
- **Purpose**: Determines whether to buffer or send messages

#### 3. Message Replay
- **Method**: `_replay_buffer()`
- **Trigger**: Circuit breaker closes (connection restored)
- **Behavior**: 
  - Replays messages in FIFO order
  - Stops on first failure and preserves remaining messages
  - Logs replay progress and results

### Key Features

#### Buffer Management
```python
# Initialize buffer with max size
self.message_buffer = deque(maxlen=settings.kafka.buffer_size)

# Buffer message when disconnected
if not self._is_connected and not from_buffer:
    self.message_buffer.append({
        'topic': topic,
        'value': value,
        'key': key,
        'headers': headers,
        'buffered_at': time.time()
    })
```

#### Overflow Handling
- When buffer reaches max capacity, oldest messages are automatically dropped
- Warning logs are generated when overflow occurs
- Buffer utilization can be monitored via `get_buffer_status()`

#### Message Ordering
- FIFO ordering is preserved using `deque`
- Messages are replayed in the exact order they were buffered
- Agent-specific ordering is maintained through partition keys

#### Replay Logic
```python
def _replay_buffer(self):
    """Replay messages from buffer when connection is restored."""
    while self.message_buffer and self._is_connected:
        msg = self.message_buffer.popleft()
        try:
            self.produce(msg['topic'], msg['value'], msg['key'], 
                        msg['headers'], from_buffer=True)
            replayed_count += 1
        except Exception as e:
            # Put message back and stop on failure
            self.message_buffer.appendleft(msg)
            break
```

### API Methods

#### `get_buffer_status() -> Dict[str, Any]`
Returns current buffer metrics:
- `size`: Current number of buffered messages
- `max_size`: Maximum buffer capacity
- `utilization`: Buffer usage percentage (0.0 to 1.0)
- `is_full`: Whether buffer is at capacity
- `is_connected`: Current connection state

#### `clear_buffer() -> int`
Clears all buffered messages and returns the count of cleared messages.

### Circuit Breaker Integration

The buffering system integrates with the circuit breaker pattern:

1. **Circuit Opens** (connection fails):
   - `_is_connected` set to `False`
   - New messages are buffered instead of sent
   - Overflow warnings logged if buffer fills

2. **Circuit Closes** (connection restored):
   - `_is_connected` set to `True`
   - `_replay_buffer()` automatically triggered
   - Messages replayed in order

3. **Circuit Half-Open** (testing connection):
   - Messages continue to be buffered
   - Replay only occurs when circuit fully closes

### Configuration

Environment variables:
```bash
# Buffer size (default: 1000)
KAFKA__BUFFER_SIZE=1000

# Circuit breaker settings
KAFKA__ENABLED=true
KAFKA__BOOTSTRAP_SERVERS=localhost:9092
```

### Testing

#### Unit Tests (`test_kafka_buffering.py`)
- Buffer initialization
- Message buffering when disconnected
- Buffer overflow handling
- Message ordering preservation
- Replay on reconnection
- Replay failure handling
- Buffer status tracking
- Buffer clearing

#### Integration Tests (`test_kafka_buffering_integration.py`)
- Circuit breaker triggering buffering
- Buffer replay on circuit breaker close
- Buffer status tracking with real circuit breaker

### Performance Considerations

1. **Memory Usage**: Buffer size should be tuned based on:
   - Expected message rate
   - Average message size
   - Available memory
   - Acceptable message loss threshold

2. **Replay Performance**: 
   - Messages are replayed sequentially
   - Replay stops on first failure to prevent cascading issues
   - Failed messages remain in buffer for next retry

3. **Monitoring**:
   - Buffer utilization should be monitored
   - High utilization indicates connection issues
   - Full buffer indicates message loss

### Logging

The implementation provides comprehensive logging:

- **INFO**: Buffer operations (buffering, replay start/end)
- **WARNING**: Buffer overflow, replay failures
- **ERROR**: System errors during replay

Example logs:
```json
{
  "level": "INFO",
  "message": "Message buffered for topic test-topic. Buffer size: 5/1000",
  "action_type": "kafka_message_buffered"
}

{
  "level": "WARNING",
  "message": "Kafka message buffer is full (1000 messages). Oldest message will be dropped.",
  "action_type": "kafka_buffer_overflow"
}

{
  "level": "INFO",
  "message": "Replaying 50 buffered messages.",
  "action_type": "kafka_replay_start"
}
```

## Requirements Validation

This implementation satisfies all requirements from task 14:

✅ **Add local message buffer in KafkaMessageBus for connection failures**
- Implemented using `collections.deque` with configurable size

✅ **Implement message replay functionality when connection is restored**
- `_replay_buffer()` method automatically triggered on reconnection

✅ **Add buffer size limits and overflow handling**
- Configurable max size with automatic oldest-message dropping
- Overflow warnings logged

✅ **Ensure message ordering is preserved during replay**
- FIFO ordering maintained through `deque`
- Sequential replay preserves order

## Future Enhancements

Potential improvements for future iterations:

1. **Persistent Buffer**: Store buffer to disk for crash recovery
2. **Priority Queuing**: Allow high-priority messages to skip buffer
3. **Compression**: Compress buffered messages to save memory
4. **Metrics**: Export buffer metrics to monitoring systems
5. **Adaptive Sizing**: Dynamically adjust buffer size based on load
