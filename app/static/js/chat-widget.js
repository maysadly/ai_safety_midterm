// Chat widget shown in the corner of every page.
// Sends messages to POST /api/chat with a session_id, so the server keeps the
// conversation history. The messages shown are kept in sessionStorage, so they
// stay when the visitor moves to another page in the same tab.
//
// Security: answers come from a language model and are untrusted. They are
// always inserted with textContent, never innerHTML, so "<script>" in an answer
// is shown as text and never runs.
(function () {
  "use strict";

  const SESSION_KEY = "pixelkiln-session-id";
  const HISTORY_KEY = "pixelkiln-chat-history";

  function sessionId() {
    let id = sessionStorage.getItem(SESSION_KEY);
    if (!id) {
      id = crypto.randomUUID().replaceAll("-", "");
      sessionStorage.setItem(SESSION_KEY, id);
    }
    return id;
  }

  function loadHistory() {
    try {
      return JSON.parse(sessionStorage.getItem(HISTORY_KEY)) || [];
    } catch {
      return [];
    }
  }

  function saveHistory(history) {
    sessionStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function debugText(debug) {
    return (
      "blocked_by: " + (debug.blocked_by || "none") +
      " | guard: " + debug.guard_verdict.replaceAll("\n", " ") +
      " | model " + debug.t_model_ms + " ms, guard " + debug.t_guard_ms +
      " ms, total " + debug.t_total_ms + " ms"
    );
  }

  // --- build the widget ---
  const toggle = el("button", "chat-toggle");
  toggle.type = "button";
  toggle.setAttribute("aria-expanded", "false");
  toggle.setAttribute("aria-controls", "chat-panel");
  toggle.append(el("span", "dot"), el("span", "", "Ask Kiln"));

  const panel = el("section", "chat-panel");
  panel.id = "chat-panel";
  panel.hidden = true;
  panel.setAttribute("aria-label", "Chat with Kiln, Pixelkiln support");

  const head = el("div", "chat-head");
  const title = el("strong", "", "Kiln, Pixelkiln support");
  const close = el("button", "chat-close", "×");
  close.type = "button";
  close.setAttribute("aria-label", "Close chat");
  head.append(title, close);

  const log = el("div", "chat-log");
  log.setAttribute("role", "log");
  log.setAttribute("aria-live", "polite");

  const typing = el("div", "chat-typing", "Kiln is writing");
  typing.hidden = true;

  const form = el("form", "chat-form");
  const input = el("textarea");
  input.name = "message";
  input.placeholder = "Ask about plans, credits or billing";
  input.setAttribute("aria-label", "Your message");
  const send = el("button", "", "Send");
  send.type = "submit";
  form.append(input, send);

  const note = el("p", "chat-note", "Kiln is an AI model and can make mistakes.");

  panel.append(head, log, typing, form, note);
  document.body.append(panel, toggle);

  // --- behaviour ---
  const history = loadHistory();

  function render(item) {
    const bubble = el("div", "msg msg-" + item.role);
    bubble.append(el("p", "", item.text));
    if (item.debug) bubble.append(el("p", "msg-debug", debugText(item.debug)));
    log.append(bubble);
    log.scrollTop = log.scrollHeight;
  }

  function add(item) {
    history.push(item);
    saveHistory(history);
    render(item);
  }

  function setOpen(open) {
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    if (open) input.focus();
  }

  function setBusy(busy) {
    typing.hidden = !busy;
    send.disabled = busy;
    input.disabled = busy;
  }

  if (history.length === 0) {
    history.push({ role: "bot", text: "Hi, I'm Kiln. Ask me about Pixelkiln plans, credits or your account." });
    saveHistory(history);
  }
  history.forEach(render);

  toggle.addEventListener("click", () => setOpen(panel.hidden));
  close.addEventListener("click", () => setOpen(false));

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    add({ role: "user", text: text });
    setBusy(true);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId(), source: "widget" }),
      });
      const data = await response.json();
      if (response.ok) {
        add({ role: "bot", text: data.reply, debug: data.debug });
      } else {
        const detail = typeof data.detail === "string" ? data.detail : "The message could not be sent.";
        add({ role: "error", text: detail });
      }
    } catch {
      add({ role: "error", text: "No connection to the server. Check that it is running." });
    } finally {
      setBusy(false);
      input.focus();
    }
  });
})();
