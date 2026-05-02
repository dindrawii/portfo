(function () {
  let chatHistory = [];
  let conversationId = null;
  let contextLoaded = false;
  let contextLoading = false;

  const widget = document.createElement("div");

  widget.innerHTML = `
    <button id="portfolio-chat-toggle" aria-label="Open portfolio assistant">
      💬
    </button>

    <section id="portfolio-chat-window" class="portfolio-chat-hidden">
      <div class="portfolio-chat-header">
        <div>
          <strong>Mohammed Assistant</strong>
          <span>Ask about Mohammed's skills, work, or experience</span>
        </div>
        <button id="portfolio-chat-close" aria-label="Close chat">×</button>
      </div>

      <div id="portfolio-chat-box" class="portfolio-chat-box">
        <div class="portfolio-message assistant">
          Hi, I’m Mohammed’s portfolio assistant. Open the chat and I’ll load the latest available profile context.
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

  function addMessage(role, text) {
    const message = document.createElement("div");
    message.className = `portfolio-message ${role}`;
    message.textContent = text;
    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  async function loadContextOnce() {
    if (contextLoaded || contextLoading) return;

    contextLoading = true;
    chatStatus.textContent = "Loading latest profile context...";
    chatInput.disabled = true;

    try {
      const response = await fetch("/api/load-context", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({})
      });

      const rawText = await response.text();

      let data;
      try {
        data = JSON.parse(rawText);
      } catch (error) {
        addMessage(
          "assistant",
          "The server did not return JSON from /api/load-context. Check PythonAnywhere error logs."
        );
        chatStatus.textContent = `Context load failed: ${response.status}`;
        chatInput.disabled = false;
        return;
      }

      if (!response.ok || !data.ok) {
        addMessage("assistant", data.error || "Could not load profile context.");
        chatStatus.textContent = `Context load failed: ${response.status}`;
        chatInput.disabled = false;
        return;
      }

      conversationId = data.conversation_id;
      contextLoaded = true;

      const linkedinStatus = data.debug?.linkedin?.status || "unknown";
      const usedFallback = data.debug?.used_fallback_profile;

      if (linkedinStatus === "loaded") {
        chatStatus.textContent = "Profile context loaded.";
      } else if (usedFallback) {
        chatStatus.textContent = "LinkedIn live scrape unavailable; using profile cache.";
      } else {
        chatStatus.textContent = "Portfolio context loaded. LinkedIn live scrape unavailable.";
      }

      chatInput.disabled = false;
      chatInput.focus();
    } catch (error) {
      addMessage(
        "assistant",
        "Network error while loading profile context. The chat is enabled, but the backend context route is failing."
      );
      chatStatus.textContent = "Context network error.";
      chatInput.disabled = false;
    } finally {
      contextLoading = false;
    }
  }

  async function openChat() {
    chatWindow.classList.remove("portfolio-chat-hidden");
    toggleButton.classList.add("portfolio-chat-hidden");
    await loadContextOnce();
    chatInput.focus();
  }

  function closeChat() {
    chatWindow.classList.add("portfolio-chat-hidden");
    toggleButton.classList.remove("portfolio-chat-hidden");
  }

  toggleButton.addEventListener("click", openChat);
  closeButton.addEventListener("click", closeChat);

  chatForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const message = chatInput.value.trim();
    if (!message) return;

    if (!contextLoaded || !conversationId) {
      addMessage("assistant", "Profile context is still loading. Please try again in a moment.");
      return;
    }

    addMessage("user", message);

    chatHistory.push({
      role: "user",
      content: message
    });

    chatInput.value = "";
    chatStatus.textContent = "Thinking...";
    chatInput.disabled = true;

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: message,
          conversation_id: conversationId,
          history: chatHistory
        })
      });

      const data = await response.json();

      if (!response.ok || !data.ok) {
        addMessage("assistant", data.error || "Something went wrong.");
        chatStatus.textContent = `Request failed: ${response.status}`;
        return;
      }

      addMessage("assistant", data.reply);

      chatHistory.push({
        role: "assistant",
        content: data.reply
      });

      chatHistory = chatHistory.slice(-24);
      chatStatus.textContent = "";
    } catch (error) {
      addMessage("assistant", "Network error. Please try again.");
      chatStatus.textContent = "Network error.";
    } finally {
      chatInput.disabled = false;
      chatInput.focus();
    }
  });
})();