// static/js/chat.js - Green AI Chat with Ollama

// Send chat message to Green AI
async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const messagesDiv = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('send-btn');
    
    const question = input.value.trim();
    
    if (!question) {
        showNotification('Please enter a message', 'error');
        return;
    }
    
    // Add user message to chat
    addMessage(question, 'user');
    
    // Clear input
    input.value = '';
    
    // Disable send button
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Thinking...';
    
    // Add loading message
    const loadingId = addMessage('Thinking...', 'ai-loading');
    
    try {
        const response = await fetch('/api/greenai', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });
        
        const data = await response.json();
        
        // Remove loading message
        document.getElementById(loadingId)?.remove();
        
        if (data.error) {
            addMessage(`Error: ${data.error}`, 'ai-error');
            showNotification('Failed to get response from Green AI', 'error');
        } else if (data.answer) {
            addMessage(data.answer, 'ai');
            
            // Show carbon info if available
            if (data.carbon && data.carbon.carbon_intensity) {
                const carbonInfo = `Current grid carbon: ${data.carbon.carbon_intensity.toFixed(1)} gCO₂/kWh (${data.carbon.region})`;
                addMessage(carbonInfo, 'ai-info');
            }
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        document.getElementById(loadingId)?.remove();
        addMessage(`Error: ${error.message}`, 'ai-error');
        showNotification('Failed to connect to Green AI', 'error');
    }
    
    // Re-enable send button
    sendBtn.disabled = false;
    sendBtn.innerHTML = 'Send <i class="fas fa-paper-plane"></i>';
    
    // Scroll to bottom
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Add message to chat
function addMessage(text, type) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageId = `msg-${Date.now()}`;
    
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `message ${type === 'user' ? 'user-message' : 'ai-message'}`;
    
    if (type === 'user') {
        messageDiv.innerHTML = `<strong>You:</strong><p>${escapeHtml(text)}</p>`;
    } else if (type === 'ai-loading') {
        messageDiv.innerHTML = `<strong>Green AI:</strong><p><i class="fas fa-spinner fa-spin"></i> ${escapeHtml(text)}</p>`;
    } else if (type === 'ai-error') {
        messageDiv.innerHTML = `<strong>Green AI:</strong><p style="color: var(--accent-color);">${escapeHtml(text)}</p>`;
    } else if (type === 'ai-info') {
        messageDiv.innerHTML = `<p style="font-size: 0.9em; color: var(--text-muted); font-style: italic;">${escapeHtml(text)}</p>`;
    } else {
        // Format AI response with line breaks
        const formattedText = escapeHtml(text).replace(/\n/g, '<br>');
        messageDiv.innerHTML = `<strong>Green AI:</strong><p>${formattedText}</p>`;
    }
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    return messageId;
}

// Set custom prompt template
function setPrompt(promptText) {
    const input = document.getElementById('chat-input');
    input.value = promptText;
    input.focus();
    showNotification('Prompt template loaded', 'success');
}

// Handle Enter key in chat input
document.addEventListener('DOMContentLoaded', function() {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keydown', function(e) {
            // Shift+Enter for new line, Enter alone to send
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }
});

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}