/**
 * Scout AI - Frontend Controller & Backend Integration
 */

const API_BASE = "http://localhost:8000";

// State
let currentConversationId = localStorage.getItem("scout_conversation_id") || null;
let isProcessing = false;

// DOM Elements
const chatStream = document.getElementById("chat-stream");
const chatScroll = document.getElementById("chat-scroll");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const sessionIdDisplay = document.getElementById("session-id-display");
const welcomeCard = document.getElementById("welcome-card");
const backendStatusPill = document.getElementById("backend-status-pill");
const backendStatusText = document.getElementById("backend-status-text");
const suggestionBtns = document.querySelectorAll(".suggestion-btn");
const mobileToggle = document.getElementById("mobile-toggle");
const sidebar = document.getElementById("sidebar");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  updateSessionDisplay();
  checkBackendHealth();
  setupEventListeners();
  autoResizeTextarea();
});

function updateSessionDisplay() {
  if (currentConversationId) {
    sessionIdDisplay.textContent = currentConversationId.substring(0, 13) + "...";
    sessionIdDisplay.title = currentConversationId;
  } else {
    sessionIdDisplay.textContent = "New Session";
    sessionIdDisplay.title = "No active ID";
  }
}

async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      backendStatusText.textContent = "Backend Active";
      backendStatusPill.style.borderColor = "rgba(34, 197, 94, 0.4)";
    }
  } catch (err) {
    backendStatusText.textContent = "Offline (Port 8000)";
    backendStatusPill.style.borderColor = "rgba(239, 68, 68, 0.4)";
  }
}

function setupEventListeners() {
  // Textarea input handling
  userInput.addEventListener("input", () => {
    autoResizeTextarea();
    sendBtn.disabled = !userInput.value.trim() || isProcessing;
  });

  // Enter to send (Shift+Enter for newline)
  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) {
        chatForm.dispatchEvent(new Event("submit"));
      }
    }
  });

  // Form submission
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query || isProcessing) return;

    await handleUserMessage(query);
  });

  // New chat button
  newChatBtn.addEventListener("click", () => {
    currentConversationId = null;
    localStorage.removeItem("scout_conversation_id");
    updateSessionDisplay();
    chatStream.innerHTML = "";
    if (welcomeCard) chatStream.appendChild(welcomeCard);
    userInput.focus();
  });

  // Suggested queries
  suggestionBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const query = btn.dataset.query;
      if (query && !isProcessing) {
        userInput.value = query;
        autoResizeTextarea();
        sendBtn.disabled = false;
        chatForm.dispatchEvent(new Event("submit"));
      }
    });
  });

  // Mobile sidebar toggle
  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }
}

function autoResizeTextarea() {
  userInput.style.height = "auto";
  userInput.style.height = Math.min(userInput.scrollHeight, 160) + "px";
}

function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

async function handleUserMessage(question) {
  isProcessing = true;
  sendBtn.disabled = true;
  userInput.value = "";
  autoResizeTextarea();

  // Remove welcome card if present
  if (welcomeCard && welcomeCard.parentNode) {
    welcomeCard.parentNode.removeChild(welcomeCard);
  }

  // 1. Render User Message
  renderUserMessage(question);
  scrollToBottom();

  // 2. Render Typing Indicator
  const typingRow = renderTypingIndicator();
  scrollToBottom();

  try {
    const payload = {
      question: question,
      conversation_id: currentConversationId || undefined
    };

    const response = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({ detail: "Network request failed" }));
      throw new Error(errData.detail || `Server error: ${response.status}`);
    }

    const data = await response.json();

    // Update conversation_id
    if (data.conversation_id) {
      currentConversationId = data.conversation_id;
      localStorage.setItem("scout_conversation_id", currentConversationId);
      updateSessionDisplay();
    }

    // Remove typing indicator and render response
    typingRow.remove();
    renderAssistantMessage(data.answer, data.sources);
  } catch (error) {
    typingRow.remove();
    renderErrorMessage(error.message);
  } finally {
    isProcessing = false;
    sendBtn.disabled = !userInput.value.trim();
    scrollToBottom();
    userInput.focus();
  }
}

function renderUserMessage(text) {
  const row = document.createElement("div");
  row.className = "message-row user";
  row.innerHTML = `
    <div class="message-avatar avatar-user">U</div>
    <div class="message-body">
      <div class="message-author">You</div>
      <div class="message-bubble">${escapeHTML(text)}</div>
    </div>
  `;
  chatStream.appendChild(row);
}

function renderAssistantMessage(answer, sources) {
  const row = document.createElement("div");
  row.className = "message-row assistant";

  // Parse markdown if available
  let parsedHTML = answer;
  if (window.marked && typeof window.marked.parse === "function") {
    parsedHTML = window.marked.parse(answer);
  } else {
    parsedHTML = `<p>${escapeHTML(answer).replace(/\n/g, "<br>")}</p>`;
  }

  let sourcesHTML = "";
  if (sources && sources.length > 0) {
    // Deduplicate sources by document & page
    const uniqueSources = [];
    const seen = new Set();
    for (const s of sources) {
      const key = `${s.document}_${s.page}`;
      if (!seen.has(key)) {
        seen.add(key);
        uniqueSources.push(s);
      }
    }

    const tags = uniqueSources.map(s => `
      <span class="source-tag" title="Chunk: ${s.chunk_id}">
        <span>📄 ${escapeHTML(s.document)}</span>
        <span class="source-page">Pg. ${s.page}</span>
      </span>
    `).join("");

    sourcesHTML = `
      <div class="sources-card">
        <div class="sources-header">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
          </svg>
          <span>Retrieved Citations & Context</span>
        </div>
        <div class="sources-grid">
          ${tags}
        </div>
      </div>
    `;
  }

  row.innerHTML = `
    <div class="message-avatar avatar-assistant">AI</div>
    <div class="message-body">
      <div class="message-author">Scout AI</div>
      <div class="message-bubble">${parsedHTML}</div>
      ${sourcesHTML}
    </div>
  `;
  chatStream.appendChild(row);
}

function renderTypingIndicator() {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.innerHTML = `
    <div class="message-avatar avatar-assistant">AI</div>
    <div class="message-body">
      <div class="message-author">Scout AI</div>
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  chatStream.appendChild(row);
  return row;
}

function renderErrorMessage(message) {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.innerHTML = `
    <div class="message-avatar avatar-assistant" style="background:#ef4444;">!</div>
    <div class="message-body">
      <div class="message-author">Scout AI (Error)</div>
      <div class="message-bubble" style="color: #fca5a5;">
        ${escapeHTML(message)}
      </div>
    </div>
  `;
  chatStream.appendChild(row);
}

function escapeHTML(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}
