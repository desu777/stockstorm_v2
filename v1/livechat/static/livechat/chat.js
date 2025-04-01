// LiveChat JavaScript - obsługa WebSockets i zarządzanie stanem czatu

class LiveChat {
    constructor(userId, username) {
        this.userId = userId;
        this.username = username;
        this.chatWidget = document.getElementById('live-chat-widget');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-message');
        this.toggleButton = document.getElementById('toggle-chat');
        this.newMessageIndicator = document.getElementById('new-message-indicator');
        this.emojiPickerBtn = document.getElementById('emoji-picker-btn');
        this.emojiPicker = document.getElementById('emoji-picker');
        this.emojis = document.querySelectorAll('.emoji');
        this.messageCount = 0;
        
        this.socket = null;
        this.isCollapsed = localStorage.getItem('chat_collapsed') === 'true';
        this.isConnected = false;
        
        this.init();
    }
    
    init() {
        // Pobieranie referencji do elementów UI
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-message');
        this.toggleButton = document.getElementById('toggle-chat');
        this.newMessageIndicator = document.getElementById('new-message-indicator');
        this.emojiPickerBtn = document.getElementById('emoji-picker-btn');
        this.emojiPicker = document.getElementById('emoji-picker');
        this.emojis = document.querySelectorAll('.emoji');
        
        // Ustawienie initial state z lokalnego storage
        if (this.isCollapsed) {
            document.getElementById('live-chat-widget').classList.add('collapsed');
            this.toggleButton.innerHTML = '<i class="fas fa-chevron-up"></i>';
        }
        
        // Pobierz istniejące wiadomości
        this.loadExistingMessages();
        
        // Inicjalizacja WebSocket
        this.connectWebSocket();
        
        // Nasłuchiwanie na zdarzenia UI
        this.toggleButton.addEventListener('click', () => this.toggleChat());
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Wysyłanie wiadomości na Enter
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        // Obsługa emotek
        this.emojiPickerBtn.addEventListener('click', () => this.toggleEmojiPicker());
        
        // Zamykanie pickera po kliknięciu gdziekolwiek indziej
        document.addEventListener('click', (e) => {
            if (this.emojiPicker.classList.contains('active') && 
                !this.emojiPicker.contains(e.target) && 
                e.target !== this.emojiPickerBtn) {
                this.emojiPicker.classList.remove('active');
            }
        });
        
        // Dodanie obsługi kliknięcia dla każdej emotki
        this.emojis.forEach(emoji => {
            emoji.addEventListener('click', () => {
                this.addEmojiToInput(emoji.dataset.emoji);
            });
        });
        
        // Fokus na input po kliknięciu w obszar wiadomości
        this.chatMessages.addEventListener('click', () => {
            if (!this.isCollapsed) {
                this.chatInput.focus();
            }
        });
        
        // Markuj wiadomości jako przeczytane gdy użytkownik skupi się na inpucie
        this.chatInput.addEventListener('focus', () => this.markAsRead());
    }
    
    connectWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsHost = window.location.hostname + ':7001';
        const wsPath = '/';
        const wsUrl = wsProtocol + wsHost + wsPath;
        
        console.log('Próba połączenia z WebSocket na:', wsUrl);
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket połączony pomyślnie');
            this.isConnected = true;
        };
        
        this.socket.onmessage = (e) => {
            console.log('Otrzymano wiadomość WebSocket:', e.data);
            const data = JSON.parse(e.data);
            this.receiveMessage(data);
        };
        
        this.socket.onclose = (e) => {
            console.log('WebSocket rozłączony:', e);
            this.isConnected = false;
            
            // Próba ponownego połączenia po 5 sekundach
            setTimeout(() => {
                console.log('Próba ponownego połączenia...');
                this.connectWebSocket();
            }, 5000);
        };
        
        this.socket.onerror = (error) => {
            console.error('Błąd WebSocket:', error);
        };
    }
    
    // Ładowanie istniejących wiadomości z serwera
    loadExistingMessages() {
        console.log('Próba ładowania historii wiadomości...');
        
        // Określenie absolutnego URL-a do API
        const messagesUrl = window.location.protocol + '//' + window.location.host + '/livechat/messages/';
        console.log('Ładowanie wiadomości z:', messagesUrl);
        
        fetch(messagesUrl)
            .then(response => {
                console.log('Status odpowiedzi:', response.status);
                if (!response.ok) {
                    throw new Error('Błąd sieci: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                console.log('Otrzymano dane:', data);
                if (data.messages.length === 0) {
                    this.chatMessages.innerHTML = '<div class="empty-chat">Brak wiadomości. Bądź pierwszy i napisz coś!</div>';
                } else {
                    this.chatMessages.innerHTML = '';
                    data.messages.forEach(msg => {
                        this.displayMessage(msg);
                    });
                    
                    // Przewinięcie do najnowszej wiadomości
                    this.scrollToBottom();
                }
            })
            .catch(error => {
                console.error('Błąd podczas ładowania wiadomości:', error);
                this.chatMessages.innerHTML = '<div class="empty-chat">Nie można załadować wiadomości</div>';
            });
    }
    
    // Wysyłanie wiadomości
    sendMessage() {
        const messageText = this.chatInput.value.trim();
        
        if (messageText && this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log('Wysyłanie wiadomości:', messageText);
            
            const messageData = {
                'message': messageText,
                'username': this.username,
                'user_id': this.userId
            };
            
            this.socket.send(JSON.stringify(messageData));
            this.chatInput.value = '';
        } else {
            console.log('Nie można wysłać wiadomości:', { 
                messageText: !!messageText, 
                socketExists: !!this.socket, 
                socketReadyState: this.socket ? this.socket.readyState : 'no socket',
                openState: WebSocket.OPEN
            });
        }
    }
    
    receiveMessage(data) {
        const isScrolledToBottom = this.isAtBottom();
        
        // Przygotowanie danych wiadomości
        const messageData = {
            id: null,
            username: data.username,
            user_id: data.user_id,
            message: data.message,
            timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
            is_self: parseInt(this.userId) === parseInt(data.user_id),
            profile_picture: data.profile_picture || null
        };
        
        // Szczegółowe logowanie otrzymanych danych
        console.log("Przetwarzanie otrzymanej wiadomości:", {
            original: data,
            processed: messageData,
            hasProfilePicture: !!messageData.profile_picture,
            userId: this.userId,
            isSelf: messageData.is_self
        });
        
        // Wyświetl wiadomość
        this.displayMessage(messageData);
        
        // Automatyczne przewijanie tylko jeśli użytkownik był już na dole
        if (isScrolledToBottom) {
            this.scrollToBottom();
        }
        
        // Jeśli czat jest zwinięty, pokaż wskaźnik nowej wiadomości
        if (this.isCollapsed) {
            this.messageCount++;
            this.showNewMessageIndicator();
        }
        
        // Usuń komunikat o pustym chacie, jeśli istnieje
        const emptyChat = this.chatMessages.querySelector('.empty-chat');
        if (emptyChat) {
            emptyChat.remove();
        }
    }
    
    // Wyświetlanie wiadomości w oknie czatu
    displayMessage(msg) {
        console.log("Wyświetlanie wiadomości:", msg);
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${msg.is_self ? 'sent' : 'received'}`;
        
        const formattedTime = this.formatTimestamp(msg.timestamp);
        
        // Prosta wersja z zawsze wyświetlaną nazwą użytkownika dla wszystkich wiadomości
        if (msg.is_self) {
            // Własne wiadomości (po prawej)
            messageDiv.innerHTML = `
                <div class="sender">${msg.username}</div>
                <div class="content">${this.escapeHTML(msg.message)}</div>
                <div class="timestamp">${formattedTime}</div>
            `;
        } else {
            // Wiadomości od innych (po lewej)
            messageDiv.innerHTML = `
                <div class="sender">${msg.username}</div>
                <div class="content">${this.escapeHTML(msg.message)}</div>
                <div class="timestamp">${formattedTime}</div>
            `;
        }
        
        this.chatMessages.appendChild(messageDiv);
    }
    
    // Zwijanie/rozwijanie czatu
    toggleChat() {
        const chatWidget = document.getElementById('live-chat-widget');
        chatWidget.classList.toggle('collapsed');
        
        this.isCollapsed = chatWidget.classList.contains('collapsed');
        localStorage.setItem('chat_collapsed', this.isCollapsed);
        
        if (this.isCollapsed) {
            this.toggleButton.innerHTML = '<i class="fas fa-chevron-up"></i>';
        } else {
            this.toggleButton.innerHTML = '<i class="fas fa-chevron-down"></i>';
            // Po rozwinięciu, przewiń na dół i ustaw focus na input
            this.scrollToBottom();
            this.chatInput.focus();
            this.markAsRead();
        }
    }
    
    // Pokazywanie/ukrywanie selektora emotek
    toggleEmojiPicker() {
        this.emojiPicker.classList.toggle('active');
    }
    
    // Dodawanie emotki do pola tekstowego
    addEmojiToInput(emoji) {
        this.chatInput.value += emoji;
        this.chatInput.focus();
    }
    
    // Sprawdzenie czy użytkownik przewinął na sam dół
    isAtBottom() {
        const tolerance = 30; // Tolerancja na niewielkie odchylenia
        return (this.chatMessages.scrollHeight - this.chatMessages.scrollTop - this.chatMessages.clientHeight) < tolerance;
    }
    
    // Przewinięcie na sam dół okna czatu
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    // Oznaczenie wiadomości jako przeczytanych
    markAsRead() {
        this.messageCount = 0;
        this.newMessageIndicator.classList.remove('visible');
    }
    
    // Wyświetlenie wskaźnika nowych wiadomości
    showNewMessageIndicator() {
        this.newMessageIndicator.textContent = this.messageCount > 9 ? '9+' : this.messageCount;
        this.newMessageIndicator.classList.add('visible');
    }
    
    // Formatowanie timestampu do czytelnej postaci
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${hours}:${minutes}`;
    }
    
    // Zabezpieczenie przed XSS
    escapeHTML(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;')
            .replace(/\n/g, '<br>');
    }
}

// Inicjalizacja live chatu po załadowaniu DOM
document.addEventListener('DOMContentLoaded', function() {
    // Sprawdzamy czy użytkownik jest zalogowany
    const userId = document.getElementById('user-id')?.value;
    const username = document.getElementById('username')?.value;
    
    if (userId && username) {
        window.liveChat = new LiveChat(userId, username);
    }
});
