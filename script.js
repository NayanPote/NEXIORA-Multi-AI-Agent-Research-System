(() => {
  "use strict";

  const queryForm = document.getElementById("queryForm");
  const topicInput = document.getElementById("topicInput");
  const runBtn = document.getElementById("runBtn");
  const resetBtn = document.getElementById("resetBtn");

  const chatLog = document.getElementById("chatLog");
  const emptyState = document.getElementById("emptyState");
  const exampleRow = document.getElementById("exampleRow");
  const consoleEl = document.getElementById("console");

  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");

  const errorBanner = document.getElementById("errorBanner");
  const errorText = document.getElementById("errorText");

  // Full message history sent back to the server on every turn.
  let history = [];
  let isSending = false;

  function setStatus(state, label) {
    statusDot.className = "dot dot-" + state;
    statusText.textContent = label;
  }

  function showError(message) {
    errorText.textContent = message;
    errorBanner.hidden = false;
  }

  function hideError() {
    errorBanner.hidden = true;
    errorText.textContent = "";
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  /** Small markdown-ish inline + block renderer for assistant replies. */
  function renderMarkdown(rawText) {
    const lines = (rawText || "").split("\n");
    let html = "";
    let listType = null;
    let paragraphBuffer = [];

    const inlineFormat = (line) =>
      escapeHtml(line)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/(https?:\/\/[^\s)]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');

    const flushParagraph = () => {
      if (paragraphBuffer.length) {
        html += `<p>${inlineFormat(paragraphBuffer.join(" "))}</p>`;
        paragraphBuffer = [];
      }
    };

    const closeList = () => {
      if (listType) {
        html += `</${listType}>`;
        listType = null;
      }
    };

    lines.forEach((rawLine) => {
      const line = rawLine.trim();

      if (!line) {
        flushParagraph();
        closeList();
        return;
      }

      const headingMatch = line.match(/^#{1,3}\s*(.+)$/);
      if (headingMatch) {
        flushParagraph();
        closeList();
        html += `<h3>${inlineFormat(headingMatch[1])}</h3>`;
        return;
      }

      const bulletMatch = line.match(/^[-*]\s+(.*)$/);
      if (bulletMatch) {
        flushParagraph();
        if (listType !== "ul") {
          closeList();
          html += "<ul>";
          listType = "ul";
        }
        html += `<li>${inlineFormat(bulletMatch[1])}</li>`;
        return;
      }

      const numberedMatch = line.match(/^\d+[.)]\s+(.*)$/);
      if (numberedMatch) {
        flushParagraph();
        if (listType !== "ol") {
          closeList();
          html += "<ol>";
          listType = "ol";
        }
        html += `<li>${inlineFormat(numberedMatch[1])}</li>`;
        return;
      }

      closeList();
      paragraphBuffer.push(line);
    });

    flushParagraph();
    closeList();

    return html || `<p>${inlineFormat(rawText || "")}</p>`;
  }

  function scrollToBottom() {
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function addMessage(role, text) {
    emptyState.hidden = true;

    const row = document.createElement("div");
    row.className = "msg-row msg-" + role;

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";

    if (role === "user") {
      bubble.textContent = text;
    } else {
      bubble.innerHTML = renderMarkdown(text);
    }

    row.appendChild(bubble);
    chatLog.appendChild(row);
    scrollToBottom();
    return bubble;
  }

  function addThinkingBubble() {
    emptyState.hidden = true;

    const row = document.createElement("div");
    row.className = "msg-row msg-assistant";
    row.id = "thinkingRow";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble msg-thinking";
    bubble.innerHTML = '<span class="think-dot"></span><span class="think-dot"></span><span class="think-dot"></span>';

    row.appendChild(bubble);
    chatLog.appendChild(row);
    scrollToBottom();
  }

  function removeThinkingBubble() {
    const row = document.getElementById("thinkingRow");
    if (row) row.remove();
  }

  function addSources(sources) {
    if (!sources || sources.length === 0) return;

    const row = document.createElement("div");
    row.className = "msg-row msg-assistant";

    const panel = document.createElement("div");
    panel.className = "sources-inline";

    const label = document.createElement("span");
    label.className = "sources-inline-label";
    label.textContent = sources.length === 1 ? "1 source" : `${sources.length} sources`;
    panel.appendChild(label);

    const list = document.createElement("div");
    list.className = "sources-inline-list";
    sources.forEach((url) => {
      const a = document.createElement("a");
      a.href = url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = url;
      list.appendChild(a);
    });
    panel.appendChild(list);

    row.appendChild(panel);
    chatLog.appendChild(row);
    scrollToBottom();
  }

  function setSending(sending) {
    isSending = sending;
    runBtn.disabled = sending;
    topicInput.disabled = sending;
  }

  async function sendMessage(message) {
    hideError();
    addMessage("user", message);
    setStatus("active", "Thinking");
    addThinkingBubble();
    setSending(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Something went wrong. Please try again.");
      }

      removeThinkingBubble();
      addMessage("assistant", data.reply || "");
      addSources(data.sources || []);
      history = data.history || history;

      setStatus("done", "Ready");
    } catch (err) {
      removeThinkingBubble();
      setStatus("error", "Something went wrong");
      showError(err.message || "Something went wrong. Please try again.");
    } finally {
      setSending(false);
      topicInput.focus();
    }
  }

  function resetConversation() {
    history = [];
    chatLog.innerHTML = "";
    emptyState.hidden = false;
    hideError();
    setStatus("idle", "Ready");
    topicInput.value = "";
    topicInput.focus();
  }

  queryForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (isSending) return;
    const message = topicInput.value.trim();
    if (!message) return;
    topicInput.value = "";
    sendMessage(message);
  });

  exampleRow.addEventListener("click", (event) => {
    const chip = event.target.closest(".example-chip");
    if (!chip || isSending) return;
    topicInput.value = chip.dataset.topic;
    topicInput.focus();
  });

  resetBtn.addEventListener("click", () => {
    if (isSending) return;
    resetConversation();
  });
})();