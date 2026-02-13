function toggleChat() {
    const chatWindow = document.getElementById('chat-window');
    chatWindow.classList.toggle('active');
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    const chatBox = document.getElementById('chat-messages');

    if (!message) return;

    chatBox.innerHTML += `<div class="message user-msg">${message}</div>`;
    input.value = '';
    scrollToBottom(); 
    const loadingId = 'loading-' + Date.now();
    chatBox.innerHTML += `<div class="message ai-msg" id="${loadingId}">열심히 답변을 작성 중이에요...💬</div>`;
    scrollToBottom();

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });
        const data = await response.json();

        document.getElementById(loadingId).innerText = data.reply;
    } catch (error) {
        document.getElementById(loadingId).innerText = "죄송해요, 연결에 문제가 생겼어요. 😥";
    }
    scrollToBottom(); 
}

async function handleChat(userInput) {
    const idMatch = userInput.match(/(\d+)th\s*summarize/);
    
    if (idMatch) {
        const postId = idMatch[1];
        const response = await fetch(`/ai/summarize/${postId}`);
        const data = await response.json();
        
        appendMessage("AI", data.summary);
    }
}

function scrollToBottom() {
    const chatBox = document.getElementById('chat-messages');
    chatBox.scrollTop = chatBox.scrollHeight;
}