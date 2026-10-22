// Staff login: POST /admin/login sets an httpOnly cookie, then we go to ?next=...
(function () {
  "use strict";

  // Only local paths like "/demo" - never "//other-site.com" or "https://..." (open redirect).
  function nextPath() {
    const next = new URLSearchParams(location.search).get("next") || "/admin";
    return next.startsWith("/") && !next.startsWith("//") ? next : "/admin";
  }

  const form = document.getElementById("login-form");
  const error = document.getElementById("login-error");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    const response = await fetch("/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: form.password.value }),
    });
    if (response.ok) {
      location.assign(nextPath());
    } else {
      const data = await response.json().catch(() => ({}));
      error.textContent = typeof data.detail === "string" ? data.detail : "Login failed.";
    }
  });
})();
