// Admin panel: debug switch + latest chat log entries. All text goes in with textContent.
(function () {
  "use strict";

  const rows = document.getElementById("log-rows");
  const debugSwitch = document.getElementById("debug-switch");

  function cell(text, className) {
    const td = document.createElement("td");
    td.textContent = text === null || text === undefined ? "" : String(text);
    if (className) td.className = className;
    return td;
  }

  function short(text, n) {
    if (!text) return "";
    return text.length > n ? text.slice(0, n) + "..." : text;
  }

  async function loadLogs() {
    const response = await fetch("/admin/api/logs?limit=50");
    if (response.status === 401) return location.assign("/admin/login?next=/admin");
    const entries = await response.json();
    rows.replaceChildren();
    for (const e of entries) {
      const tr = document.createElement("tr");
      if (e.blocked_by) tr.className = "row-blocked";
      tr.append(
        cell((e.time || "").replace("T", " ").slice(0, 19)),
        cell(e.source),
        cell(e.attack_id || (e.session_id ? "session " + e.session_id.slice(0, 8) : "single message")),
        cell(short(e.user_message, 140), "cell-text"),
        cell(short(e.final_answer || e.error, 200), "cell-text"),
        cell(e.blocked_by || "none"),
        cell((e.guard_verdict || "").replaceAll("\n", " ")),
        cell(e.t_total_ms),
      );
      rows.append(tr);
    }
  }

  async function loadDebug() {
    const response = await fetch("/admin/api/debug");
    if (response.ok) debugSwitch.checked = (await response.json()).enabled;
  }

  debugSwitch.addEventListener("change", async () => {
    await fetch("/admin/api/debug", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: debugSwitch.checked }),
    });
  });

  document.getElementById("refresh").addEventListener("click", loadLogs);
  document.getElementById("logout").addEventListener("click", async () => {
    await fetch("/admin/logout", { method: "POST" });
    location.assign("/");
  });

  loadDebug();
  loadLogs();
})();
