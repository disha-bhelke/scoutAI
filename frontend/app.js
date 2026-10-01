/**
 * Scout AI - Frontend Controller & Backend Integration
 */

// Resolve Backend API URL from environment variables (.env / Vercel)
const getApiBase = () => {
  // Check process.env (Vercel / Node build environments)
  if (typeof process !== "undefined" && process.env && process.env.BACKEND_URL) {
    return process.env.BACKEND_URL;
  }

  // Check window global (if injected by hosting provider or config script)
  if (typeof window !== "undefined") {
    if (window.BACKEND_URL) return window.BACKEND_URL;
    if (window.__ENV__?.BACKEND_URL) return window.__ENV__.BACKEND_URL;
  }

  // Local development fallback
  return (window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1"))
    ? (window.location.port === "8000" ? "" : "http://localhost:8000")
    : "";
};

const API_BASE = getApiBase().replace(/\/+$/, "");




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

  // Admin Modal Handling
  setupAdminModal();
}

function setupAdminModal() {
  const adminModalBtn = document.getElementById("admin-modal-btn");
  const adminModal = document.getElementById("admin-modal");
  const closeModalBtn = document.getElementById("close-modal-btn");
  const adminLoginView = document.getElementById("admin-login-view");
  const adminIngestView = document.getElementById("admin-ingest-view");
  const adminUserInput = document.getElementById("admin-user-input");
  const adminPassInput = document.getElementById("admin-pass-input");
  const adminLoginSubmit = document.getElementById("admin-login-submit");
  const loginErrorMsg = document.getElementById("login-error-msg");
  const adminLogoutBtn = document.getElementById("admin-logout-btn");
  const loggedUserName = document.getElementById("logged-user-name");
  const triggerIngestBtn = document.getElementById("trigger-ingest-btn");
  const ingestPathInput = document.getElementById("ingest-path-input");
  const resetCollectionCheckbox = document.getElementById("reset-collection-checkbox");
  const ingestStatusBox = document.getElementById("ingest-status-box");
  const ingestStatusText = document.getElementById("ingest-status-text");
  const ingestDetails = document.getElementById("ingest-details");
  const ingestSpinner = document.getElementById("ingest-spinner");
  const adminBtnLabel = document.getElementById("admin-btn-label");

  function getAdminToken() {
    return localStorage.getItem("scout_admin_token");
  }

  function updateAdminBtnState() {
    if (getAdminToken()) {
      adminBtnLabel.textContent = "Admin (Logged In)";
    } else {
      adminBtnLabel.textContent = "Admin Portal";
    }
  }

  updateAdminBtnState();

  function openModal() {
    const token = getAdminToken();
    if (token) {
      adminLoginView.style.display = "none";
      adminIngestView.style.display = "flex";
      loggedUserName.textContent = localStorage.getItem("scout_admin_user") || "admin";
    } else {
      adminLoginView.style.display = "flex";
      adminIngestView.style.display = "none";
      loginErrorMsg.style.display = "none";
      adminPassInput.value = "";
    }
    adminModal.style.display = "flex";
  }

  function closeModal() {
    adminModal.style.display = "none";
    loginErrorMsg.style.display = "none";
  }

  adminModalBtn.addEventListener("click", openModal);
  closeModalBtn.addEventListener("click", closeModal);
  adminModal.addEventListener("click", (e) => {
    if (e.target === adminModal) closeModal();
  });

  // Handle Login
  adminLoginSubmit.addEventListener("click", async () => {
    const username = adminUserInput.value.trim();
    const password = adminPassInput.value.trim();

    if (!username || !password) {
      loginErrorMsg.textContent = "Please provide both username and password.";
      loginErrorMsg.style.display = "block";
      return;
    }

    loginErrorMsg.style.display = "none";
    adminLoginSubmit.disabled = true;
    adminLoginSubmit.textContent = "Authenticating...";

    try {
      const res = await fetch(`${API_BASE}/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Login failed" }));
        throw new Error(data.detail || "Invalid credentials.");
      }

      const data = await res.json();
      localStorage.setItem("scout_admin_token", data.token);
      localStorage.setItem("scout_admin_user", data.username);
      updateAdminBtnState();

      // Switch to Ingest view
      adminLoginView.style.display = "none";
      adminIngestView.style.display = "flex";
      loggedUserName.textContent = data.username;
    } catch (err) {
      loginErrorMsg.textContent = err.message;
      loginErrorMsg.style.display = "block";
    } finally {
      adminLoginSubmit.disabled = false;
      adminLoginSubmit.textContent = "Authenticate";
    }
  });

  // Handle Logout
  adminLogoutBtn.addEventListener("click", () => {
    localStorage.removeItem("scout_admin_token");
    localStorage.removeItem("scout_admin_user");
    updateAdminBtnState();
    adminIngestView.style.display = "none";
    adminLoginView.style.display = "flex";
    adminPassInput.value = "";
  });

  // Handle Ingest (File Upload to Cloudinary or Directory Path)
  triggerIngestBtn.addEventListener("click", async () => {
    const token = getAdminToken();
    if (!token) {
      adminLogoutBtn.click();
      return;
    }

    const docFileInput = document.getElementById("doc-file-input");
    const file = docFileInput && docFileInput.files && docFileInput.files[0];
    const filePath = ingestPathInput.value.trim() || undefined;
    const resetCollection = resetCollectionCheckbox.checked;

    if (!file && !filePath) {
      alert("Please either select a document to upload to Cloudinary or enter an existing path.");
      return;
    }

    triggerIngestBtn.disabled = true;
    ingestStatusBox.style.display = "flex";
    ingestSpinner.style.display = "inline-block";
    ingestStatusText.textContent = file
      ? `Uploading ${file.name} to Cloudinary and indexing...`
      : "Extracting and indexing documents...";
    ingestDetails.textContent = "This may take a moment depending on document size...";

    try {
      let res;
      if (file) {
        // Upload directly to Cloudinary via /admin/upload
        const formData = new FormData();
        formData.append("file", file);
        formData.append("reset_collection", resetCollection);

        res = await fetch(`${API_BASE}/admin/upload`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`
          },
          body: formData
        });
      } else {
        // Ingest from path via /ingest
        res = await fetch(`${API_BASE}/ingest`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            file_path: filePath,
            reset_collection: resetCollection
          })
        });
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Ingestion failed" }));
        throw new Error(data.detail || `Error ${res.status}`);
      }

      const data = await res.json();
      ingestSpinner.style.display = "none";
      ingestStatusText.textContent = "✅ Ingestion Successful!";
      ingestDetails.innerHTML = `
        <strong>${data.message}</strong><br>
        Document: <code>${data.document_name}</code><br>
        Total Chunks: <code>${data.total_chunks}</code> | Collection: <code>${data.collection}</code>
      `;
      // Clear file input
      if (docFileInput) docFileInput.value = "";
    } catch (err) {
      ingestSpinner.style.display = "none";
      ingestStatusText.textContent = "❌ Ingestion Failed";
      ingestDetails.textContent = err.message;
    } finally {
      triggerIngestBtn.disabled = false;
    }
  });
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
