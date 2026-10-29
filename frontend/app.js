/**
 * Ayush AI - Modern Frontend Controller
 * Handles chat communication, dynamic tool cards, approval actions,
 * live Ollama health telemetry, and modal managers.
 */

document.addEventListener("DOMContentLoaded", () => {
  const chatHistory = document.getElementById("chatHistory");
  const chatForm = document.getElementById("chatForm");
  const messageInput = document.getElementById("messageInput");
  const sendBtn = document.getElementById("sendBtn");
  const clearChatBtn = document.getElementById("clearChatBtn");

  const statusDot = document.getElementById("statusDot");
  const statusLabel = document.getElementById("statusLabel");
  const modelBadge = document.getElementById("modelBadge");

  // Modals
  const memoryBtn = document.getElementById("memoryBtn");
  const memoryModal = document.getElementById("memoryModal");
  const closeMemoryModal = document.getElementById("closeMemoryModal");
  const memoryJsonDisplay = document.getElementById("memoryJsonDisplay");
  const prefKeyInput = document.getElementById("prefKeyInput");
  const prefValInput = document.getElementById("prefValInput");
  const savePrefBtn = document.getElementById("savePrefBtn");

  const filesBtn = document.getElementById("filesBtn");
  const filesModal = document.getElementById("filesModal");
  const closeFilesModal = document.getElementById("closeFilesModal");
  const wordFilesList = document.getElementById("wordFilesList");
  const excelFilesList = document.getElementById("excelFilesList");
  const pptFilesList = document.getElementById("pptFilesList");
  const workspaceFilesList = document.getElementById("workspaceFilesList");

  // ---------------------------------------------------------
  // Health Polling
  // ---------------------------------------------------------
  async function checkHealth() {
    try {
      const res = await fetch("/health");
      if (!res.ok) throw new Error("Health endpoint error");
      const data = await res.json();

      const isConnected = data.ollama && data.ollama.connected;
      const model = data.ollama?.configured_model || "qwen3:8b";

      if (isConnected) {
        statusDot.className = "status-dot connected";
        statusLabel.textContent = "Ollama: Connected";
        modelBadge.textContent = `Model: ${model}`;
      } else {
        statusDot.className = "status-dot disconnected";
        statusLabel.textContent = "Ollama: Disconnected";
        modelBadge.textContent = "Start Ollama local server";
      }
    } catch (err) {
      statusDot.className = "status-dot disconnected";
      statusLabel.textContent = "Server Offline";
      modelBadge.textContent = "Connecting...";
    }
  }

  // Initial check & interval
  checkHealth();
  setInterval(checkHealth, 10000);

  // ---------------------------------------------------------
  // Auto-resize textarea
  // ---------------------------------------------------------
  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 140) + "px";
  });

  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  // ---------------------------------------------------------
  // Quick Prompts
  // ---------------------------------------------------------
  document.querySelectorAll(".prompt-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      messageInput.value = prompt;
      messageInput.focus();
      chatForm.dispatchEvent(new Event("submit"));
    });
  });

  // ---------------------------------------------------------
  // Chat History Helpers
  // ---------------------------------------------------------
  function scrollToBottom() {
    chatHistory.scrollTop = chatHistory.scrollHeight;
  }

  function appendUserMessage(text) {
    const group = document.createElement("div");
    group.className = "message-group user";
    group.innerHTML = `
      <div class="avatar">👤</div>
      <div class="message-body">
        <div class="message-meta">You</div>
        <div class="bubble">
          <p>${escapeHtml(text)}</p>
        </div>
      </div>
    `;
    chatHistory.appendChild(group);
    scrollToBottom();
  }

  function showThinkingIndicator() {
    const group = document.createElement("div");
    group.className = "message-group assistant thinking-group";
    group.id = "thinkingIndicator";
    group.innerHTML = `
      <div class="avatar">⚡</div>
      <div class="message-body">
        <div class="message-meta">Ayush AI</div>
        <div class="bubble">
          <p><em>Ayush AI is thinking and inspecting tools...</em></p>
        </div>
      </div>
    `;
    chatHistory.appendChild(group);
    scrollToBottom();
  }

  function removeThinkingIndicator() {
    const el = document.getElementById("thinkingIndicator");
    if (el) el.remove();
  }

  function renderAssistantResponse(data) {
    const group = document.createElement("div");
    group.className = "message-group assistant";

    let toolActivityHtml = "";
    if (data.tool_activities && data.tool_activities.length > 0) {
      toolActivityHtml = data.tool_activities
        .map((act) => {
          const statusClass = act.status || "running";
          return `
            <div class="tool-activity-card">
              <div class="tool-header">
                <span class="tool-tag">🔧 Tool: ${escapeHtml(act.tool)}</span>
                <span class="tool-status ${statusClass}">${escapeHtml(act.action)}</span>
              </div>
              ${act.details ? `<div class="tool-details">${escapeHtml(act.details)}</div>` : ""}
            </div>
          `;
        })
        .join("");
    }

    // Process file download pills
    let downloadPillsHtml = "";
    const responseText = data.response || "";
    const fileMatches = responseText.match(/(\/files\/(word|excel|ppt)\/[^\s\)\]]+)/g);
    if (fileMatches) {
      const uniqueFiles = Array.from(new Set(fileMatches));
      downloadPillsHtml = uniqueFiles
        .map((fileUrl) => {
          const filename = fileUrl.split("/").pop();
          return `<a href="${fileUrl}" target="_blank" class="file-download-pill">📥 Download ${escapeHtml(filename)}</a>`;
        })
        .join(" ");
    }

    // Approval Request Card
    let approvalHtml = "";
    if (data.pending_approval) {
      const appr = data.pending_approval;
      approvalHtml = `
        <div class="approval-card" id="approval-${appr.id}">
          <div class="approval-header">
            <span>⚠️</span> Approval Required for Action
          </div>
          <div class="approval-meta">
            <div><strong>Tool:</strong> <code>${escapeHtml(appr.tool)}</code></div>
            <div><strong>Reason:</strong> ${escapeHtml(appr.reason)}</div>
            <pre>${escapeHtml(JSON.stringify(appr.arguments, null, 2))}</pre>
          </div>
          <div class="approval-buttons">
            <button class="btn-approve" onclick="window.handleApproval('${appr.id}', true)">APPROVE</button>
            <button class="btn-reject" onclick="window.handleApproval('${appr.id}', false)">REJECT</button>
          </div>
        </div>
      `;
    }

    // Format paragraphs
    const formattedParagraphs = responseText
      .split("\n\n")
      .map((p) => `<p>${formatMarkdown(p)}</p>`)
      .join("");

    group.innerHTML = `
      <div class="avatar">⚡</div>
      <div class="message-body">
        <div class="message-meta">Ayush AI</div>
        <div class="bubble">
          ${toolActivityHtml}
          <div class="response-content" style="margin-top: ${toolActivityHtml ? "12px" : "0"}">
            ${formattedParagraphs}
          </div>
          ${downloadPillsHtml ? `<div style="margin-top: 10px">${downloadPillsHtml}</div>` : ""}
          ${approvalHtml}
        </div>
      </div>
    `;

    chatHistory.appendChild(group);
    scrollToBottom();
  }

  // ---------------------------------------------------------
  // Chat Submission
  // ---------------------------------------------------------
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (!message) return;

    appendUserMessage(message);
    messageInput.value = "";
    messageInput.style.height = "auto";
    sendBtn.disabled = true;

    showThinkingIndicator();

    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message }),
      });

      removeThinkingIndicator();

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        renderAssistantResponse({
          response: `Error (${response.status}): ${errorData.detail || "Server communication issue."}`,
          tool_activities: []
        });
      } else {
        const data = await response.json();
        renderAssistantResponse(data);
      }
    } catch (err) {
      removeThinkingIndicator();
      renderAssistantResponse({
        response: `Could not reach Ayush AI server: ${err.message}`,
        tool_activities: []
      });
    } finally {
      sendBtn.disabled = false;
      messageInput.focus();
    }
  });

  // ---------------------------------------------------------
  // Approval Callback
  // ---------------------------------------------------------
  window.handleApproval = async function (approvalId, isApproved) {
    const card = document.getElementById(`approval-${approvalId}`);
    if (card) {
      card.innerHTML = `<em>Processing approval decision (${isApproved ? "Approved" : "Rejected"})...</em>`;
    }

    const endpoint = isApproved
      ? `/approvals/${approvalId}/approve`
      : `/approvals/${approvalId}/reject`;

    try {
      const res = await fetch(endpoint, { method: "POST" });
      const data = await res.json();
      renderAssistantResponse(data);
    } catch (err) {
      alert(`Approval error: ${err.message}`);
    }
  };

  // ---------------------------------------------------------
  // Clear Chat
  // ---------------------------------------------------------
  clearChatBtn.addEventListener("click", () => {
    if (confirm("Clear active chat conversation display?")) {
      chatHistory.innerHTML = "";
    }
  });

  // ---------------------------------------------------------
  // Memory Modal
  // ---------------------------------------------------------
  async function loadMemoryModal() {
    try {
      const res = await fetch("/memory");
      const data = await res.json();
      memoryJsonDisplay.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      memoryJsonDisplay.textContent = "Error loading memory: " + err.message;
    }
    memoryModal.classList.remove("hidden");
  }

  memoryBtn.addEventListener("click", loadMemoryModal);
  closeMemoryModal.addEventListener("click", () => memoryModal.classList.add("hidden"));

  savePrefBtn.addEventListener("click", async () => {
    const key = prefKeyInput.value.trim();
    const value = prefValInput.value.trim();
    if (!key || !value) {
      alert("Please provide both category and value.");
      return;
    }

    try {
      const res = await fetch("/memory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, value }),
      });
      const data = await res.json();
      prefKeyInput.value = "";
      prefValInput.value = "";
      memoryJsonDisplay.textContent = JSON.stringify(data.memory, null, 2);
    } catch (err) {
      alert("Error saving memory preference: " + err.message);
    }
  });

  // ---------------------------------------------------------
  // Files Modal
  // ---------------------------------------------------------
  async function loadFilesModal() {
    try {
      const res = await fetch("/files");
      const data = await res.json();

      const renderList = (container, items) => {
        if (!items || items.length === 0) {
          container.innerHTML = "<li>None generated yet</li>";
          return;
        }
        container.innerHTML = items
          .map(
            (item) => `
            <li>
              <a href="${item.download_url}" target="_blank">📄 ${escapeHtml(item.name)}</a>
              <span class="file-size">${item.size_kb} KB</span>
            </li>
          `
          )
          .join("");
      };

      renderList(wordFilesList, data.word_documents);
      renderList(excelFilesList, data.excel_spreadsheets);
      renderList(pptFilesList, data.powerpoint_presentations);
      renderList(workspaceFilesList, data.workspace_files);
    } catch (err) {
      alert("Error loading files list: " + err.message);
    }
    filesModal.classList.remove("hidden");
  }

  filesBtn.addEventListener("click", loadFilesModal);
  closeFilesModal.addEventListener("click", () => filesModal.classList.add("hidden"));

  // Close modals on background click
  window.addEventListener("click", (e) => {
    if (e.target === memoryModal) memoryModal.classList.add("hidden");
    if (e.target === filesModal) filesModal.classList.add("hidden");
  });

  // ---------------------------------------------------------
  // String Utilities
  // ---------------------------------------------------------
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let safe = escapeHtml(text);
    // Bold
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Inline code
    safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Bullet replacement
    safe = safe.replace(/^[•\-\*]\s+(.*)$/gm, "• $1");
    // Line breaks
    safe = safe.replace(/\n/g, "<br/>");
    return safe;
  }
});
