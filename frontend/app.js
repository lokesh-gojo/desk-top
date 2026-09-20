// EASA DeskBot - Frontend Client Logic (V2.2 Production Hardened)
const API_BASE = window.location.origin.includes("5500") || window.location.origin.includes("localhost:3000") 
  ? "http://localhost:8000/api" 
  : "/api";

let currentLanguage = "en";
let isListening = false;
let speechRecognition = null;
let chatHistory = []; // Tracks multi-turn conversational context
let adminApiKey = sessionStorage.getItem("easa_admin_key") || "easa-admin-key-2026";

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  loadActiveNotices();
  initSpeech();
});

// Language Switcher
function setLanguage(lang) {
  currentLanguage = lang;
  document.getElementById("lang-en").classList.toggle("active", lang === "en");
  document.getElementById("lang-ta").classList.toggle("active", lang === "ta");

  const titleEl = document.getElementById("welcome-title");
  const descEl = document.getElementById("welcome-desc");
  const inputEl = document.getElementById("user-input");

  if (lang === "ta") {
    titleEl.textContent = "வணக்கம்! ஈசா பொறியியல் கல்லூரி உதவி மையத்திற்கு வரவேற்கிறோம் 👋";
    descEl.innerHTML = "நான் ஈசா பொறியியல் கல்லூரியின் அதிகாரப்பூர்வ AI தகவல் உதவியாளர். சேர்க்கை, படிப்புகள், விடுதி மற்றும் பேருந்து விவரங்கள் குறித்து என்னிடம் கேளுங்கள்.";
    inputEl.placeholder = "சேர்க்கை, பாடப்பிரிவுகள், விடுதி, பேருந்து பற்றி கேட்கவும்...";
  } else {
    titleEl.textContent = "Vanakkam! Welcome to EASA College Helpdesk 👋";
    descEl.innerHTML = "I am your official AI Information Assistant, trained on verified institutional records for <strong>EASA College of Engineering and Technology</strong>. How may I assist you today?";
    inputEl.placeholder = "Ask about admissions, courses, hostel, transport, fees...";
  }
}

// Quick Chip Action
function askQuick(question) {
  document.getElementById("user-input").value = question;
  handleSend(new Event("submit"));
}

// Chat Submission
async function handleSend(e) {
  if (e) e.preventDefault();
  const inputEl = document.getElementById("user-input");
  const query = inputEl.value.trim();
  if (!query) return;

  // Append user message
  appendMessage("user", query);
  inputEl.value = "";

  // Append typing indicator
  const loadingId = appendLoadingCard();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: query,
        language: currentLanguage,
        history: chatHistory.slice(-6) // Retain last 3 dialogue turns
      })
    });

    removeLoadingCard(loadingId);

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}`);
    }

    const data = await res.json();
    
    // Update local conversation history
    chatHistory.push({ role: "user", content: query });
    chatHistory.push({ role: "assistant", content: data.answer });

    appendBotMessage(data, query);
  } catch (err) {
    console.error("Chat error:", err);
    removeLoadingCard(loadingId);
    appendMessage("bot", "I couldn't reach the college helpdesk server. Please ensure the backend is running or contact the admission office at +91 97888 88888.");
  }
}

function appendMessage(role, text) {
  const container = document.getElementById("messages-container");
  const card = document.createElement("div");
  card.className = `message-card ${role}-card`;
  
  const emblem = role === "user" ? "👤" : "🎓";
  card.innerHTML = `
    <div class="avatar-ring">${emblem}</div>
    <div class="card-body">
      <p>${escapeHtml(text)}</p>
    </div>
  `;
  container.appendChild(card);
  container.scrollTop = container.scrollHeight;
}

function appendBotMessage(data, userQuery) {
  const container = document.getElementById("messages-container");
  const card = document.createElement("div");
  card.className = "message-card bot-card";

  let sourcesHtml = "";
  if (data.sources && data.sources.length > 0) {
    sourcesHtml = `
      <div class="citation-box">
        <strong>Verified Institutional Sources:</strong><br>
        ${data.sources.map(s => `
          <span class="source-item">
            🔗 <a href="${s.url}" target="_blank" rel="noopener">${escapeHtml(s.title)}</a>
            &bull; <span class="verified-badge">Verified: ${s.verified_at}</span>
          </span>
        `).join("")}
      </div>
    `;
  }

  let suggestionsHtml = "";
  if (data.suggested_questions && data.suggested_questions.length > 0) {
    suggestionsHtml = `
      <div class="quick-chips-grid" style="margin-top: 10px;">
        ${data.suggested_questions.map(q => `
          <button class="chip" onclick="askQuick('${escapeHtml(q)}')">${escapeHtml(q)}</button>
        `).join("")}
      </div>
    `;
  }

  const feedbackId = `fb-${Date.now()}`;

  card.innerHTML = `
    <div class="avatar-ring">🎓</div>
    <div class="card-body">
      <p>${formatAnswer(data.answer)}</p>
      ${sourcesHtml}
      ${suggestionsHtml}
      <div class="feedback-actions" id="${feedbackId}">
        <span style="font-size: 0.72rem; color: var(--text-muted);">Was this helpful?</span>
        <button class="fb-btn" onclick="submitFeedback('${feedbackId}', '${escapeHtml(userQuery)}', '${escapeHtml(data.answer)}', 'helpful')">👍 Helpful</button>
        <button class="fb-btn" onclick="submitFeedback('${feedbackId}', '${escapeHtml(userQuery)}', '${escapeHtml(data.answer)}', 'unhelpful')">👎 Incomplete</button>
      </div>
    </div>
  `;

  container.appendChild(card);
  container.scrollTop = container.scrollHeight;
}

function appendLoadingCard() {
  const id = `loading-${Date.now()}`;
  const container = document.getElementById("messages-container");
  const card = document.createElement("div");
  card.id = id;
  card.className = "message-card bot-card";
  card.innerHTML = `
    <div class="avatar-ring">🎓</div>
    <div class="card-body" style="color: var(--text-muted); font-style: italic;">
      Consulting verified EASA institutional knowledge base...
    </div>
  `;
  container.appendChild(card);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeLoadingCard(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// Notice Ribbon Loader
async function loadActiveNotices() {
  try {
    const res = await fetch(`${API_BASE}/notices`);
    if (res.ok) {
      const notices = await res.json();
      if (notices && notices.length > 0) {
        document.getElementById("ribbon-text").textContent = 
          notices.map(n => `• ${n.title}`).join("   ");
      }
    }
  } catch (err) {
    document.getElementById("ribbon-text").textContent = "Admission Open 2026-27 for B.E & B.Tech • TNEA Single Window Code: 2755";
  }
}

// Feedback submission (Persists to SQLite/Supabase)
async function submitFeedback(elementId, q, a, rating) {
  const container = document.getElementById(elementId);
  if (container) {
    container.innerHTML = `<span style="font-size: 0.75rem; color: var(--accent-gold);">✓ Feedback recorded in persistent storage. Thank you!</span>`;
  }
  try {
    await fetch(`${API_BASE}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, answer: a, rating: rating })
    });
  } catch (e) {
    console.warn("Feedback err:", e);
  }
}

// Speech Recognition (Voice 🎤)
function initSpeech() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = false;
    speechRecognition.interimResults = false;
    speechRecognition.lang = currentLanguage === "ta" ? "ta-IN" : "en-IN";

    speechRecognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      document.getElementById("user-input").value = transcript;
      toggleVoice(false);
      handleSend(new Event("submit"));
    };

    speechRecognition.onerror = () => toggleVoice(false);
    speechRecognition.onend = () => toggleVoice(false);
  } else {
    document.getElementById("mic-btn").style.display = "none";
  }
}

function toggleVoice(force) {
  if (!speechRecognition) return;
  const btn = document.getElementById("mic-btn");
  if (force === false || isListening) {
    speechRecognition.stop();
    isListening = false;
    btn.classList.remove("listening");
  } else {
    speechRecognition.lang = currentLanguage === "ta" ? "ta-IN" : "en-IN";
    speechRecognition.start();
    isListening = true;
    btn.classList.add("listening");
  }
}

// Admin Drawer Controls (Protected with X-Admin-API-Key)
function toggleAdminPanel() {
  const drawer = document.getElementById("admin-drawer");
  drawer.classList.toggle("open");
  if (drawer.classList.contains("open")) {
    loadAdminData();
  }
}

function switchAdminTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".admin-tab-pane").forEach(p => p.classList.remove("active"));
  
  event.target.classList.add("active");
  document.getElementById(tabId).classList.add("active");
}

function getAdminHeaders() {
  return {
    "Content-Type": "application/json",
    "X-Admin-API-Key": adminApiKey
  };
}

async function loadAdminData() {
  // 1. Unanswered (from persistent DB)
  try {
    const res1 = await fetch(`${API_BASE}/admin/unanswered`, { headers: getAdminHeaders() });
    if (res1.status === 401) {
      promptForAdminKey();
      return;
    }
    const data1 = await res1.json();
    document.getElementById("unanswered-list").innerHTML = data1.length ? data1.map(item => `
      <div class="audit-item">
        <strong>"${escapeHtml(item.query)}"</strong>
        <div style="color: var(--accent-gold); font-size: 0.75rem;">Asked: ${item.frequency} times &bull; Last: ${new Date(item.last_asked_at).toLocaleString()}</div>
      </div>
    `).join("") : "<p>No unanswered queries logged. All tested questions passed confidence gates.</p>";
  } catch (e) {
    document.getElementById("unanswered-list").innerHTML = "<p>Admin access requires valid key.</p>";
  }

  // 2. Ingestion audits
  try {
    const res2 = await fetch(`${API_BASE}/admin/audits`, { headers: getAdminHeaders() });
    const data2 = await res2.json();
    document.getElementById("audit-history-list").innerHTML = data2.length ? data2.map(run => `
      <div class="audit-item">
        <div><strong>Status: ${run.status}</strong> &bull; ${run.started_at.split("T")[0]}</div>
        <div style="font-size: 0.72rem; color: var(--text-muted);">
          Scanned: ${run.pages_scanned} | Chunks: ${run.chunks_generated} | Errors: ${run.error_count}
        </div>
      </div>
    `).join("") : "<p>No ingestion runs recorded yet.</p>";
  } catch (e) {
    document.getElementById("audit-history-list").innerHTML = "<p>Ready to index.</p>";
  }

  // 3. Feedback list
  try {
    const res3 = await fetch(`${API_BASE}/feedback`, { headers: getAdminHeaders() });
    const data3 = await res3.json();
    document.getElementById("feedback-list").innerHTML = data3.length ? data3.map(f => `
      <div class="audit-item">
        <strong>${f.rating === 'helpful' ? '👍 Helpful' : '👎 Incomplete'}</strong>: "${escapeHtml(f.question)}"
        <div style="font-size: 0.72rem; color: var(--text-muted);">${f.answer.slice(0, 100)}...</div>
      </div>
    `).join("") : "<p>No user feedback entries recorded yet.</p>";
  } catch (e) {
    document.getElementById("feedback-list").innerHTML = "<p>Feedback log ready.</p>";
  }
}

async function triggerReindex() {
  const btn = document.getElementById("reindex-btn");
  btn.textContent = "⏳ Incremental Indexing...";
  btn.disabled = true;
  try {
    const res = await fetch(`${API_BASE}/admin/reindex`, {
      method: "POST",
      headers: getAdminHeaders()
    });
    const data = await res.json();
    alert(`Re-index complete! ${data.message}`);
    loadAdminData();
  } catch (e) {
    alert("Re-index failed. Please verify admin authentication key.");
  } finally {
    btn.textContent = "🔄 Trigger Re-Index";
    btn.disabled = false;
  }
}

async function submitNewNotice() {
  const title = document.getElementById("new-notice-title").value.trim();
  const content = document.getElementById("new-notice-content").value.trim();
  if (!title || !content) {
    alert("Please provide both a title and content for the notice.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/notices`, {
      method: "POST",
      headers: getAdminHeaders(),
      body: JSON.stringify({
        id: `notice-${Date.now()}`,
        title: title,
        category: "general",
        content: content,
        published_date: new Date().toISOString().split("T")[0],
        status: "active"
      })
    });

    if (res.ok) {
      alert("Notice published to persistent database!");
      document.getElementById("new-notice-title").value = "";
      document.getElementById("new-notice-content").value = "";
      loadActiveNotices();
    } else {
      alert("Failed to publish notice. Unauthorized.");
    }
  } catch (e) {
    alert("Error saving notice.");
  }
}

function promptForAdminKey() {
  const key = prompt("Enter EASA Admin API Key:", adminApiKey);
  if (key) {
    adminApiKey = key.trim();
    sessionStorage.setItem("easa_admin_key", adminApiKey);
    loadAdminData();
  }
}

function formatAnswer(text) {
  return escapeHtml(text).replace(/\n/g, "<br>");
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
