# StockStorm Live Chat Module

## Overview
The Live Chat module provides real-time communication capabilities for StockStorm users to discuss market trends and share trading ideas.

## Features
- Real-time messaging using WebSockets
- Emoji support
- Message history
- User presence tracking (online status)
- Message persistence in database

## WebSocket API

### Connection
```
ws://<host>/ws/chat/
```

### Message Types

#### Sending Messages
```json
{
  "type": "chat_message",
  "message": "Your message text",
  "user_id": 123,
  "username": "username",
  "user_photo": "/path/to/photo.jpg"
}
```

#### Receiving Messages
```json
{
  "type": "chat_message",
  "message": {
    "id": 1,
    "user_id": 123,
    "username": "username",
    "user_photo": "/path/to/photo.jpg",
    "content": "Message content",
    "timestamp": "10:30 AM"
  }
}
```

#### User Count Updates
```json
{
  "type": "user_count",
  "count": 5
}
```

#### Chat History
```json
{
  "type": "chat_history",
  "messages": [/* Array of message objects */]
}
```

## Implementation Notes
- Uses Django Channels with Redis as the backing store
- Messages are persisted in the database through the ChatMessage model
- User information is associated with messages when available

## Security Considerations
- All messages are associated with authenticated users when possible
- WebSocket connections require valid Django session
- Input is sanitized to prevent XSS attacks
