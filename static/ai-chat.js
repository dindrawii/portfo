(function () {
  const widget = document.createElement("div");

  widget.innerHTML = `
    <button id="portfolio-chat-toggle" aria-label="Open portfolio assistant">
      💬
    </button>

    <section id="portfolio-chat-window" class="portfolio-chat-hidden">
      <div class="portfolio-chat-header">
        <div>
          <strong>Mohammed Assistant</strong>
          <span>Ask about my skills, work, or experience</span>
        </div>
        <button id="portfolio-chat-close" aria-label="Close chat">×</button>
      </div>

      <div id="portfolio-chat-box" class="portfolio-chat-box">
        <div class="portfolio-message assistant">
          Hi, I’m Mohammed’s portfolio assistant. Ask me about his experience, skills, projects, or EdTech work.
        </div>
      </div>

      <form id="portfolio-chat-form" class="portfolio-chat-form">
        <input
          id="portfolio-chat-input"
          type="text"
          placeholder="Ask about Mohammed..."
          autocomplete="off"
        />
        <button type="submit">Send</button>
      </form>

      <p id="portfolio-chat-status" class="portfolio-chat-status"></p>
    </section>
  `;

  document.body.appendChild(widget);

  const toggleButton = document.getElementById("portfolio-chat-toggle");
  const closeButton = document.getElementById("portfolio-chat-close");
  const chatWindow = document.getElementById("portfolio-chat-window");
  const chatForm = document.getElementById("portfolio-chat-form");
  const chatInput = document.getElementById("portfolio-chat-input");
  const chatBox = document.getElementById("portfolio-chat-box");
  const chatStatus = document.getElementById("portfolio-chat-status");

  function openChat() {
    chatWindow.classList.remove("portfolio-chat-hidden");
    toggleButton.classList.add("portfolio-chat-hidden");
    chatInput.focus();
  }

  function closeChat() {
    chatWindow.classList.add("portfolio-chat-hidden");
    toggleButton.classList.remove("portfolio-chat-hidden");
  }

  function addMessage(role, text) {
    const message = document.createElement("div");
    message.className = `portfolio-message ${role}`;
    message.textContent = text;
    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  toggleButton.addEventListener("click", openChat);
  closeButton.addEventListener("click", closeChat);

  chatForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const message = chatInput.value.trim();
    if (!message) return;

    addMessage("user", message);
    chatInput.value = "";
    chatStatus.textContent = "Thinking...";

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message })
      });

      const data = await response.json();

      if (!response.ok || !data.ok) {
        addMessage("assistant", data.error || "Something went wrong.");
        chatStatus.textContent = "Request failed.";
        return;
      }

      addMessage("assistant", data.reply);
      chatStatus.textContent = "";
    } catch (error) {
      addMessage("assistant", "Network error. Please try again.");
      chatStatus.textContent = "Network error.";
    }
  });
})();