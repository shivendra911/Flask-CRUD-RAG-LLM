/**
 * RAG Tutor — Chat Interface JavaScript
 * Handles message sending, rendering, and auto-scroll.
 */

const messagesEl = document.getElementById('chat-messages');
const inputEl = document.getElementById('question-input');
const sendBtn = document.getElementById('send-btn');

// ── Auto-resize textarea ─────────────────────────────────────────────
inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
});

// ── Enter to send (Shift+Enter for newline) ──────────────────────────
inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// ── Suggestion chip click ────────────────────────────────────────────
function useSuggestion(chip) {
    inputEl.value = chip.textContent;
    inputEl.focus();
    sendMessage();
}

// ── Send message ─────────────────────────────────────────────────────
async function sendMessage() {
    const question = inputEl.value.trim();
    if (!question) return;

    // Clear welcome screen on first message
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    // Show user bubble
    appendBubble('user', question);

    // Reset input
    inputEl.value = '';
    inputEl.style.height = 'auto';
    sendBtn.disabled = true;

    // Show typing indicator
    const typingEl = showTypingIndicator();

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });

        const data = await res.json();

        // Remove typing indicator
        typingEl.remove();

        if (res.ok && data.answer) {
            appendBubble('ai', data.answer);
        } else {
            appendBubble('ai', data.error || 'Something went wrong. Please try again.');
        }
    } catch (err) {
        typingEl.remove();
        appendBubble('ai', 'Network error. Please check your connection and try again.');
    }

    sendBtn.disabled = false;
    inputEl.focus();
}

// ── Render a chat bubble ─────────────────────────────────────────────
function appendBubble(role, text) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;

    const label = document.createElement('div');
    label.className = 'bubble-label';
    label.textContent = role === 'user' ? 'You' : 'RAG Tutor';

    const content = document.createElement('div');
    content.className = 'bubble-content';
    // Simple markdown-like formatting
    content.innerHTML = formatText(text);

    bubble.appendChild(label);
    bubble.appendChild(content);
    messagesEl.appendChild(bubble);

    scrollToBottom();
}

// ── Typing indicator ─────────────────────────────────────────────────
function showTypingIndicator() {
    const el = document.createElement('div');
    el.className = 'typing-indicator';
    el.innerHTML = '<span></span><span></span><span></span>';
    messagesEl.appendChild(el);
    scrollToBottom();
    return el;
}

// ── Scroll to bottom ─────────────────────────────────────────────────
function scrollToBottom() {
    messagesEl.scrollTo({
        top: messagesEl.scrollHeight,
        behavior: 'smooth',
    });
}

// ── Simple text formatter (basic markdown) ───────────────────────────
function formatText(text) {
    return text
        // Code blocks
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Bullet points
        .replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
        // Numbered lists
        .replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
        // Newlines
        .replace(/\n/g, '<br>');
}
