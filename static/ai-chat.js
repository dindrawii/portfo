const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const chatBox = document.getElementById('chat-box');
const chatStatus = document.getElementById('chat-status');

function addMessage(role, text) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;

  wrapper.appendChild(bubble);
  chatBox.appendChild(wrapper);
  chatBox.scrollTop = chatBox.scrollHeight;
}

chatForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();
  if (!message) return;

  addMessage('user', message);
  messageInput.value = '';
  chatStatus.textContent = 'Thinking...';

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      addMessage('assistant', data.error || 'Something went wrong.');
      chatStatus.textContent = 'Request failed.';
      return;
    }

    addMessage('assistant', data.reply);
    chatStatus.textContent = `Model used: ${data.model}`;
  } catch (error) {
    addMessage('assistant', 'Network error. Please try again.');
    chatStatus.textContent = 'Network error.';
  }
});