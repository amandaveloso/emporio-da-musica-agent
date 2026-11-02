const STORAGE_SESSION_KEY = "emporio_musica_session_id";
const STORAGE_HISTORY_KEY = "emporio_musica_history_v1";

const WELCOME_MESSAGE =
  "Olá! Bem-vindo(a) à **Empório da Música** 🎸✨\n\n" +
  "Sou o assistente virtual da loja em Campo Grande/MS. Posso consultar nosso **estoque e preços em tempo real**, simular **desconto no PIX ou parcelamento**, verificar o **status do seu pedido** ou tirar dúvidas sobre **trocas, frete e garantia**.\n\n" +
  "Como posso ajudar no seu som hoje?";

const appShell = document.querySelector(".app-shell");
const sidebar = document.getElementById("sidebar");
const messagesContainer = document.getElementById("messagesContainer");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const tracesList = document.getElementById("tracesList");
const toolCountBadge = document.getElementById("toolCountBadge");
const toggleInspectorBtn = document.getElementById("toggleInspectorBtn");

let totalToolsUsed = 0;

function getOrCreateSessionId() {
  let sid = localStorage.getItem(STORAGE_SESSION_KEY);
  if (!sid) {
    sid = "web-" + Math.random().toString(36).slice(2, 10) + "-" + Date.now().toString(36);
    localStorage.setItem(STORAGE_SESSION_KEY, sid);
  }
  return sid;
}

function loadLocalHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveLocalHistory(history) {
  localStorage.setItem(STORAGE_HISTORY_KEY, JSON.stringify(history.slice(-20)));
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatMarkdown(text) {
  const escaped = escapeHtml(text || "");
  const lines = escaped.split(/\r?\n/);
  let html = "";
  let inList = false;

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const bulletMatch = line.match(/^\s*[-*•]\s+(.*)$/);
    if (bulletMatch) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${inlineFormat(bulletMatch[1])}</li>`;
    } else {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
      if (line.trim() === "") {
        html += "";
      } else {
        html += `<p>${inlineFormat(line)}</p>`;
      }
    }
  }
  if (inList) html += "</ul>";
  return html || `<p>${escaped}</p>`;
}

function inlineFormat(str) {
  return str
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function appendMessage(role, content, meta = null) {
  const row = document.createElement("div");
  row.className = `msg-row ${role === "user" ? "user" : "assistant"}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "👤" : "🎸";

  const wrap = document.createElement("div");
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = role === "user" ? `<p>${escapeHtml(content)}</p>` : formatMarkdown(content);
  wrap.appendChild(bubble);

  if (meta && role !== "user") {
    const metaBar = document.createElement("div");
    metaBar.className = "msg-meta";
    if (meta.model_used) {
      metaBar.innerHTML += `<span class="meta-chip">🧠 ${escapeHtml(meta.model_used)}</span>`;
    }
    if (meta.latency_ms) {
      metaBar.innerHTML += `<span class="meta-chip">⚡ ${(meta.latency_ms / 1000).toFixed(1)}s</span>`;
    }
    if (meta.tool_traces && meta.tool_traces.length > 0) {
      metaBar.innerHTML += `<span class="meta-chip">🛠️ ${meta.tool_traces.length} consulta(s) ao sistema</span>`;
    }
    wrap.appendChild(metaBar);
  }

  row.appendChild(avatar);
  row.appendChild(wrap);
  messagesContainer.appendChild(row);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showTypingIndicator() {
  const row = document.createElement("div");
  row.className = "msg-row assistant";
  row.id = "typingIndicator";
  row.innerHTML = `
    <div class="avatar">🎸</div>
    <div class="bubble">
      <div class="typing-eq">
        <span class="bar"></span><span class="bar"></span><span class="bar"></span>
        <span>Consultando catálogo e políticas da loja...</span>
      </div>
    </div>
  `;
  messagesContainer.appendChild(row);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typingIndicator");
  if (el) el.remove();
}

function recordToolTraces(userPrompt, traces, modelUsed) {
  if (!traces || traces.length === 0) {
    const emptyTurn = document.createElement("div");
    emptyTurn.className = "trace-card";
    emptyTurn.innerHTML = `
      <div class="trace-card-top">
        <span class="trace-fn">resposta_direta_guardrail</span>
        <span class="trace-ms">${escapeHtml(modelUsed || "")}</span>
      </div>
      <div class="trace-summary">Respondido pelo contexto da conversa/persona sem necessidade de consulta externa.</div>
    `;
    if (totalToolsUsed === 0) tracesList.innerHTML = "";
    tracesList.prepend(emptyTurn);
    return;
  }

  if (totalToolsUsed === 0) tracesList.innerHTML = "";
  totalToolsUsed += traces.length;
  toolCountBadge.textContent = String(totalToolsUsed);

  for (const t of [...traces].reverse()) {
    const card = document.createElement("div");
    card.className = "trace-card";
    card.innerHTML = `
      <div class="trace-card-top">
        <span class="trace-fn">${escapeHtml(t.tool)}()</span>
        <span class="trace-ms">${t.latency_ms}ms</span>
      </div>
      <div class="trace-args">${escapeHtml(JSON.stringify(t.args))}</div>
      <div class="trace-summary">↳ ${escapeHtml(t.summary || "")}</div>
    `;
    tracesList.prepend(card);
  }
}

async function sendMessage(text) {
  const trimmed = text.trim();
  if (!trimmed) return;

  const sessionId = getOrCreateSessionId();
  const history = loadLocalHistory();

  appendMessage("user", trimmed);
  messageInput.value = "";
  messageInput.style.height = "auto";
  sendBtn.disabled = true;
  showTypingIndicator();
  sidebar.classList.remove("open");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: trimmed,
        session_id: sessionId,
        history: history,
      }),
    });

    const data = await res.json();
    removeTypingIndicator();

    if (!res.ok) {
      appendMessage(
        "assistant",
        `Tivemos uma oscilação momentânea: ${data.detail || "erro inesperado"}. Pode tentar novamente?`
      );
      return;
    }

    appendMessage("assistant", data.reply, data);
    recordToolTraces(trimmed, data.tool_traces, data.model_used);

    history.push({ role: "user", content: trimmed });
    history.push({ role: "assistant", content: data.reply });
    saveLocalHistory(history);
  } catch {
    removeTypingIndicator();
    appendMessage(
      "assistant",
      "Não foi possível conectar ao servidor da Empório da Música no momento. Verifique sua conexão e tente novamente."
    );
  } finally {
    sendBtn.disabled = false;
    messageInput.focus();
  }
}

async function fetchStoreHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) return;
    const data = await res.json();
    const pill = document.getElementById("storeStatusPill");
    const txt = document.getElementById("storeStatusText");
    if (data.store_hours) {
      const openLabel = data.store_hours.is_open_now
        ? `Loja Física Aberta (${data.store_hours.local_time} MS)`
        : `Loja Fechada (${data.store_hours.local_time} MS) • Bot 24h`;
      txt.textContent = openLabel;
      pill.classList.toggle("closed", !data.store_hours.is_open_now);
    }
  } catch {
    // Mantém rótulo padrão caso offline
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(messageInput.value);
});

messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage(messageInput.value);
  }
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = Math.min(messageInput.scrollHeight, 130) + "px";
});

document.querySelectorAll(".scenario-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const prompt = btn.getAttribute("data-prompt");
    if (prompt) sendMessage(prompt);
  });
});

document.getElementById("resetChatBtn").addEventListener("click", async () => {
  const sid = getOrCreateSessionId();
  localStorage.removeItem(STORAGE_HISTORY_KEY);
  localStorage.removeItem(STORAGE_SESSION_KEY);
  totalToolsUsed = 0;
  toolCountBadge.textContent = "0";
  tracesList.innerHTML = `<div class="empty-trace">Conversa reiniciada! Envie uma pergunta para acompanhar as ferramentas acionadas.</div>`;
  messagesContainer.innerHTML = "";
  appendMessage("assistant", WELCOME_MESSAGE);
  try {
    await fetch(`/api/session/${encodeURIComponent(sid)}`, { method: "DELETE" });
  } catch {}
});

function toggleInspector() {
  appShell.classList.toggle("inspector-closed");
  toggleInspectorBtn.classList.toggle(
    "active",
    !appShell.classList.contains("inspector-closed")
  );
}

toggleInspectorBtn.addEventListener("click", toggleInspector);
document.getElementById("closeInspectorBtn").addEventListener("click", toggleInspector);
document.getElementById("toggleSidebarBtn").addEventListener("click", () => {
  sidebar.classList.toggle("open");
});

// Inicialização da tela
(function init() {
  if (window.innerWidth <= 1120) {
    appShell.classList.add("inspector-closed");
    toggleInspectorBtn.classList.remove("active");
  }
  const saved = loadLocalHistory();
  appendMessage("assistant", WELCOME_MESSAGE);
  for (const item of saved) {
    appendMessage(item.role, item.content);
  }
  fetchStoreHealth();
})();
