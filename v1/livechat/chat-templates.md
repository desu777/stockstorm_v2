## 1. Create the chat template

Create a new file in `v1/hpcrypto/templates/chat.html`:

```html
{% extends "base.html" %}

{% block title %}
    Live Chat | STOCKstorm
{% endblock %}

{% block content %}
<div class="app-body-main-content">
    <div class="chat-title-bar">
        <span class="chat-icon"><i class="fa fa-comments"></i></span>
        <h2>Live Chat</h2>
        <div class="online-users">
            <i class="fa fa-users"></i> <span id="online-count">0</span>
        </div>
    </div>
    
    <div class="chat-container">
        <div class="chat-header">
            <h3>Market Discussion</h3>
            <div class="online-users">
                <i class="fa fa-users"></i> <span id="online-count">0</span> users online
            </div>
        </div>
        
        <div class="chat-messages" id="chat-messages">
            <!-- Messages will be populated here -->
        </div>
        
        <div class="chat-input-area">
            <div class="emoji-picker-container">
                <button id="emoji-button" class="btn btn-sm btn-outline-secondary">
                    <i class="fa fa-smile-o"></i>
                </button>
                <div id="emoji-picker" class="emoji-picker">
                    <!-- Emojis will be populated here -->
                </div>
            </div>
            
            <textarea id="message-input" placeholder="Type your message..." class="message-input"></textarea>
            
            <button id="send-button" class="btn btn-primary send-button">
                <i class="fa fa-paper-plane"></i>
            </button>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/reconnecting-websocket/1.0.0/reconnecting-websocket.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Chat elements
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const onlineCount = document.getElementById('online-count');
    const emojiButton = document.getElementById('emoji-button');
    const emojiPicker = document.getElementById('emoji-picker');
    
    // User information
    const currentUser = {
        id: {{ user.id }},
        username: "{{ user.username }}",
        photo: "{{ user.profile.photo_url|default:'/static/images/default-avatar.png' }}"
    };
    
    // Common emojis
    const commonEmojis = [
        "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", 
        "😉", "😊", "😋", "😎", "😍", "😘", "🥰", "😗", 
        "😙", "😚", "🙂", "🤗", "🤩", "🤔", "🤨", "😐", 
        "😑", "😶", "🙄", "😏", "😣", "😥", "😮", "🤐", 
        "😯", "😪", "😫", "🥱", "😴", "😌", "😛", "😜", 
        "😝", "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", 
        "😲", "☹️", "🙁", "😖", "😞", "😟", "😤", "😢", 
        "😭", "😦", "😧", "😨", "😩", "🤯", "😬", "😰", 
        "😱", "🥵", "🥶", "😳", "🤪", "😵", "🥴", "😠", 
        "😡", "🤬", "😷", "🤒", "🤕", "🤢", "🤮", "🤧", 
        "😇", "🥳", "🥺", "🤠", "🤡", "🤥", "🤫", "🤭", 
        "🧐", "🤓", "😈", "👍", "👎", "👏", "🙌", "👋"
    ];
    
    // Populate emoji picker
    commonEmojis.forEach(emoji => {
        const emojiSpan = document.createElement('span');
        emojiSpan.textContent = emoji;
        emojiSpan.className = 'emoji';
        emojiSpan.addEventListener('click', () => {
            // Wstawianie emoji do pola tekstowego
            const startPos = messageInput.selectionStart;
            const endPos = messageInput.selectionEnd;
            const text = messageInput.value;
            messageInput.value = text.substring(0, startPos) + emoji + text.substring(endPos);
            
            // Ustawienie kursora na pozycji po emoji
            messageInput.selectionStart = messageInput.selectionEnd = startPos + emoji.length;
            
            // Ukrycie emoji pickera
            emojiPicker.classList.remove('visible');
            
            // Ustawienie fokusu na pole wiadomości
            messageInput.focus();
        });
        emojiPicker.appendChild(emojiSpan);
    });
    
    // Toggle emoji picker
    emojiButton.addEventListener('click', () => {
        emojiPicker.classList.toggle('visible');
    });
    
    // Close emoji picker when clicking outside
    document.addEventListener('click', (event) => {
        if (!emojiButton.contains(event.target) && !emojiPicker.contains(event.target)) {
            emojiPicker.classList.remove('visible');
        }
    });
    
    // WebSocket connection
    const chatSocket = new ReconnectingWebSocket(
        'ws://' + window.location.host + '/ws/chat/'
    );
    
    chatSocket.onopen = function(e) {
        console.log('Chat connection established');
    };
    
    chatSocket.onclose = function(e) {
        console.log('Chat connection closed');
    };
    
    // Handle incoming messages
    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        
        if (data.type === 'chat_message') {
            addMessage(data.message);
        } else if (data.type === 'user_count') {
            onlineCount.textContent = data.count;
        } else if (data.type === 'chat_history') {
            // Clear existing messages
            chatMessages.innerHTML = '';
            // Add history messages
            data.messages.forEach(message => {
                addMessage(message);
            });
            // Scroll to bottom after loading history
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    };
    
    // Add message to chat
    function addMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'chat-message';
        
        if (message.user_id === currentUser.id) {
            messageElement.classList.add('my-message');
        }
        
        const messageTextDiv = document.createElement('div');
        messageTextDiv.className = 'message-text';
        messageTextDiv.textContent = message.content; // Używamy textContent zamiast innerHTML
        
        messageElement.innerHTML = `
            <div class="message-avatar">
                <img src="${message.user_photo}" alt="${message.username}">
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-username">${message.username}</span>
                    <span class="message-time">${message.timestamp}</span>
                </div>
            </div>
        `;
        
        // Dodajemy treść jako element DOM zamiast jako innerHTML
        messageElement.querySelector('.message-content').appendChild(messageTextDiv);
        
        chatMessages.appendChild(messageElement);
        
        // Scroll to the new message
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Send message function
    function sendMessage() {
        const message = messageInput.value.trim();
        
        if (message) {
            chatSocket.send(JSON.stringify({
                'type': 'chat_message',
                'message': message,
                'user_id': currentUser.id,
                'username': currentUser.username,
                'user_photo': currentUser.photo
            }));
            
            messageInput.value = '';
        }
    }
    
    // Send button click
    sendButton.addEventListener('click', sendMessage);
    
    // Enter key press
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});
</script>

<style>
.chat-container {
    background-color: #2a2a2a;
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: 70vh;
    max-width: 800px;
    margin: 0 auto;
}

.chat-header {
    background-color: #333;
    padding: 15px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #444;
}

.chat-header h3 {
    margin: 0;
}

.online-users {
    color: #aaa;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 5px;
    background-color: rgba(0, 0, 0, 0.2);
    padding: 5px 10px;
    border-radius: 15px;
}

.online-users i {
    color: #4CAF50;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 15px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.chat-message {
    display: flex;
    gap: 10px;
    max-width: 80%;
}

.my-message {
    align-self: flex-end;
    flex-direction: row-reverse;
}

.my-message .message-content {
    background-color: #2b5278;
}

.message-avatar img {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    object-fit: cover;
}

.message-content {
    background-color: #333;
    border-radius: 8px;
    padding: 10px;
    overflow-wrap: break-word;
}

.message-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
}

.message-username {
    font-weight: bold;
    color: #ddd;
}

.message-time {
    font-size: 12px;
    color: #888;
}

.message-text {
    color: #fff;
}

.chat-input-area {
    display: flex;
    padding: 15px;
    border-top: 1px solid #444;
    background-color: #333;
    gap: 10px;
    align-items: flex-end;
}

.message-input {
    flex: 1;
    border: 1px solid #444;
    border-radius: 4px;
    background-color: #2a2a2a;
    color: #fff;
    padding: 10px;
    min-height: 50px;
    max-height: 150px;
    resize: vertical;
}

.emoji-picker-container {
    position: relative;
}

.emoji-picker {
    display: none; /* Initial state is hidden */
    position: absolute;
    bottom: 100%;
    left: 0;
    background-color: #333;
    border: 1px solid #444;
    border-radius: 8px;
    padding: 10px;
    width: 300px;
    max-height: 200px;
    overflow-y: auto;
    flex-wrap: wrap;
    gap: 5px;
    margin-bottom: 10px;
    z-index: 100;
}

.emoji-picker.visible {
    display: flex;
}

.emoji {
    font-size: 20px;
    cursor: pointer;
    padding: 5px;
    border-radius: 4px;
}

.emoji:hover {
    background-color: #444;
}

.send-button {
    height: 50px;
    width: 50px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.chat-title-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    background-color: #333;
    border-bottom: 1px solid #444;
}

.chat-icon {
    color: white;
    font-size: 18px;
}

.chat-toggle {
    cursor: pointer;
    padding: 5px;
}

.online-users {
    color: #aaa;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 5px;
    background-color: rgba(0, 0, 0, 0.2);
    padding: 3px 8px;
    border-radius: 12px;
    margin-left: 10px;
}

.online-users i {
    color: #4CAF50;
}

@media (max-width: 768px) {
    .chat-message {
        max-width: 90%;
    }
    
    .emoji-picker {
        width: 250px;
    }
}
</style>
{% endblock %}
