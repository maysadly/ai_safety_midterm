// Attack lab (/demo). For every attack it makes the same two calls as the experiment
// runner (scripts/run_attacks.py):
//   1. POST /api/chat           {message, attack_id, source: "demo"}  -> reply + request_id
//   2. POST /api/demo/evaluate  {request_id}                          -> verdict from the chat log
// Everything shown comes from those two responses. Text goes in with textContent only.
(function () {
  "use strict";

  const GOALS = {
    G1: "System prompt leak",
    G2: "Staff promo code leak",
    G3: "Promise outside policy",
    G4: "Unrelated work",
    G5: "Harmful content (garak)",
  };

  const list = document.getElementById("attacks");
  const result = document.getElementById("result");
  const scores = document.getElementById("scores");
  const progress = document.getElementById("progress");
  const filterGoal = document.getElementById("filter-goal");
  const filterMethod = document.getElementById("filter-method");
  const runAllButton = document.getElementById("run-all");

  let attacks = [];
  const tally = {}; // goal -> {runs, successes, blocked}
  let busy = false;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function visibleAttacks() {
    return attacks.filter(
      (a) => (!filterGoal.value || a.goal === filterGoal.value) &&
             (!filterMethod.value || a.method === filterMethod.value)
    );
  }

  // ---------- left column ----------
  function renderList() {
    list.replaceChildren();
    for (const attack of visibleAttacks()) {
      const item = el("li", "attack-item");
      item.dataset.id = attack.id;
      const button = el("button", "attack-button");
      button.type = "button";
      const head = el("span", "attack-head");
      head.append(
        el("strong", "", attack.id),
        el("span", "chip chip-" + attack.goal, attack.goal),
        el("span", "chip", attack.method),
      );
      if (attack.technique) head.append(el("span", "technique", attack.technique));
      head.append(el("span", "status", ""));
      button.append(head, el("span", "attack-prompt", attack.prompt));
      button.addEventListener("click", () => runOne(attack));
      item.append(button);
      list.append(item);
    }
  }

  function markItem(attackId, record) {
    const item = list.querySelector(`[data-id="${CSS.escape(attackId)}"]`);
    if (!item) return;
    const status = item.querySelector(".status");
    item.classList.remove("is-success", "is-failed", "is-blocked");
    if (record.attack_success) {
      item.classList.add("is-success");
      status.textContent = "success";
    } else if (record.blocked_by) {
      item.classList.add("is-blocked");
      status.textContent = "blocked";
    } else if (record.model_violated === false) {
      item.classList.add("is-failed");
      status.textContent = "held";
    } else {
      status.textContent = "not scored";
    }
  }

  // ---------- scoreboard ----------
  function renderScores() {
    scores.replaceChildren();
    for (const goal of Object.keys(GOALS)) {
      const t = tally[goal];
      if (!t) continue;
      const li = el("li", "score" + (t.successes ? " score-hit" : ""));
      li.append(
        el("span", "score-goal", goal + " " + GOALS[goal]),
        el("span", "score-value", t.successes + " / " + t.runs + " succeeded"),
        el("span", "score-sub", t.blocked + " blocked by guard"),
      );
      scores.append(li);
    }
  }

  function count(record) {
    const t = (tally[record.goal] = tally[record.goal] || { runs: 0, successes: 0, blocked: 0 });
    t.runs += 1;
    if (record.attack_success) t.successes += 1;
    if (record.blocked_by) t.blocked += 1;
    renderScores();
  }

  // ---------- right column ----------
  function verdictText(record) {
    if (record.attack_success) return ["verdict-success", "Attack succeeded: the bot broke the rule and the guard let it through"];
    if (record.model_violated && record.blocked_by) return ["verdict-blocked", "The bot broke the rule, but the guard blocked the answer"];
    if (record.blocked_by) return ["verdict-blocked", "Blocked by the guard"];
    if (record.model_violated === false) return ["verdict-held", "The bot kept the rule"];
    if (record.goal === "G5") return ["verdict-neutral", "G5 is scored offline by garak's detectors; only the guard verdict is shown here"];
    return ["verdict-neutral", "Not scored (the judge's reply was not valid JSON)"];
  }

  function row(dl, term, value) {
    dl.append(el("dt", "", term), el("dd", "", value));
  }

  function showPending(attack) {
    result.replaceChildren(
      el("h2", "", attack.id),
      el("p", "result-label", "Prompt sent to /api/chat"),
      el("pre", "prompt-box", attack.prompt),
      el("p", "pending", "The chatbot is answering"),
    );
  }

  function showResult(attack, reply, record) {
    const [cls, text] = verdictText(record);
    const verdict = el("div", "verdict " + cls);
    verdict.append(el("strong", "", text));

    const details = el("dl", "details");
    row(details, "Goal", record.goal + " " + GOALS[record.goal]);
    row(details, "Method / technique", record.method + (record.technique ? " / " + record.technique : ""));
    row(details, "blocked_by", record.blocked_by || "none");
    row(details, "Guard verdict", (record.guard_verdict || "").replaceAll("\n", " "));
    const d = record.detectors;
    row(details, "G1 detector", `${d.G1_prompt_leak ? "LEAK" : "no leak"} (marker phrase: ${d.marker_hit ? "found" : "not found"}, 5-gram overlap ${d.ngram_overlap})`);
    row(details, "G2 detector", d.G2_secret_leak ? "LEAK: staff promo code in the answer" : "promo code not in the answer");
    if (record.judge) {
      const v = record.judge.violation === null ? "no valid verdict" : record.judge.violation ? "violation" : "no violation";
      row(details, "Judge (" + record.judge.judge_model + ")", v + ": " + record.judge.reason);
    }
    const c = record.chat;
    row(details, "Latency", `model ${c.t_model_ms} ms, guard ${c.t_guard_ms} ms, total ${c.t_total_ms} ms`);
    row(details, "request_id", record.request_id);

    result.replaceChildren(
      el("h2", "", attack.id),
      el("p", "result-label", "Prompt sent to /api/chat"),
      el("pre", "prompt-box", attack.prompt),
      el("p", "result-label", "Answer the visitor saw"),
      el("pre", "answer-box", reply),
      verdict,
      details,
    );
    if (record.blocked_by) {
      const hidden = el("details", "hidden-answer");
      hidden.append(el("summary", "", "Answer before the guard (hidden from the visitor)"), el("pre", "answer-box", c.model_answer));
      result.append(hidden);
    }
  }

  function showError(attack, message) {
    result.replaceChildren(el("h2", "", attack.id), el("p", "form-error", message));
  }

  // ---------- running attacks ----------
  async function post(url, body) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "HTTP " + response.status);
    return data;
  }

  async function attackOnce(attack) {
    showPending(attack);
    const chat = await post("/api/chat", { message: attack.prompt, attack_id: attack.id, source: "demo" });
    const record = await post("/api/demo/evaluate", { request_id: chat.request_id });
    showResult(attack, chat.reply, record);
    markItem(attack.id, record);
    count(record);
  }

  async function runOne(attack) {
    if (busy) return;
    busy = true;
    try {
      await attackOnce(attack);
    } catch (error) {
      showError(attack, error.message);
    } finally {
      busy = false;
    }
  }

  async function runAll() {
    if (busy) return;
    busy = true;
    runAllButton.disabled = true;
    const queue = visibleAttacks();
    try {
      for (let i = 0; i < queue.length; i++) {
        progress.textContent = `Running ${i + 1} of ${queue.length}: ${queue[i].id}`;
        await attackOnce(queue[i]);
      }
      progress.textContent = `Done: ${queue.length} attacks`;
    } catch (error) {
      progress.textContent = "Stopped: " + error.message;
    } finally {
      busy = false;
      runAllButton.disabled = false;
    }
  }

  async function init() {
    const response = await fetch("/api/demo/attacks");
    if (response.status === 401) return location.assign("/admin/login?next=/demo");
    attacks = await response.json();
    for (const goal of [...new Set(attacks.map((a) => a.goal))].sort()) {
      filterGoal.append(new Option(goal + " " + GOALS[goal], goal));
    }
    for (const method of [...new Set(attacks.map((a) => a.method))].sort()) {
      filterMethod.append(new Option(method, method));
    }
    filterGoal.addEventListener("change", renderList);
    filterMethod.addEventListener("change", renderList);
    runAllButton.addEventListener("click", runAll);
    renderList();
  }

  init();
})();
