"""Routes behind the admin password: /admin, /demo and their JSON APIs.

    GET  /admin/login, POST /admin/login, POST /admin/logout
    GET  /admin                last N chat log entries + the "debug lines" switch
    GET  /demo                 attack lab: run attacks from the fixed sets and see the verdict
    GET  /admin/api/logs       last N chat log entries (JSON)
    GET/POST /admin/api/debug  read / switch the debug lines under widget answers
    GET  /api/demo/attacks     the attack sets (attacks/*.yaml)
    POST /api/demo/evaluate    score one /api/chat request that belongs to an attack

/demo sends the attack to the normal POST /api/chat (like any visitor), then asks
/api/demo/evaluate to score that request from the chat log. The experiment runner
(scripts/run_attacks.py) uses exactly the same two calls, so /demo shows what the
experiment logs contain.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from app.admin_auth import COOKIE_NAME, LIFETIME_S, make_token, password_ok, token_valid
from app.evaluation import evaluate
from app.jsonl_log import JsonlLog
from app.judge import Judge
from app.ratelimit import RateLimiter

LOG_FIELDS = (
    "time", "source", "session_id", "attack_id", "user_message", "final_answer",
    "blocked_by", "guard_verdict", "t_model_ms", "t_guard_ms", "t_total_ms", "error",
)


class LoginRequest(BaseModel):
    password: str = Field(max_length=200)


class DebugSwitch(BaseModel):
    enabled: bool


class EvaluateRequest(BaseModel):
    request_id: str = Field(max_length=64, pattern=r"^[0-9a-f]+$")


def is_admin(request: Request) -> bool:
    return token_valid(request.cookies.get(COOKIE_NAME), request.app.state.settings.cookie_secret)


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(401, "Log in at /admin/login first.")


def add_admin_routes(app: FastAPI, static_dir, chat_log: JsonlLog, attacks: list[dict], llm, hash_ip) -> None:
    settings = app.state.settings
    eval_log = JsonlLog(settings.eval_log_path)
    judge = Judge(llm, settings.bot["judge_model"], settings.bot["judge_options"])
    attacks_by_id = {a["id"]: a for a in attacks}
    login_limiter = RateLimiter(5)  # 5 password attempts per minute per client

    def protected_page(file_name: str, path: str):
        def handler(request: Request):
            if not is_admin(request):
                return RedirectResponse(f"/admin/login?next={path}", status_code=303)
            return FileResponse(static_dir / file_name)
        return handler

    app.add_api_route("/admin", protected_page("admin.html", "/admin"), methods=["GET"], include_in_schema=False)
    app.add_api_route("/demo", protected_page("demo.html", "/demo"), methods=["GET"], include_in_schema=False)

    @app.get("/admin/login", include_in_schema=False)
    def login_page():
        return FileResponse(static_dir / "login.html")

    @app.post("/admin/login")
    def login(body: LoginRequest, request: Request, response: Response):
        client = hash_ip(request.client.host if request.client else "", settings.ip_hash_salt)
        if not login_limiter.allow(client):
            raise HTTPException(429, "Too many attempts. Wait a minute.")
        if not password_ok(body.password, settings.admin_password):
            raise HTTPException(401, "Wrong password.")
        response.set_cookie(
            COOKIE_NAME, make_token(settings.cookie_secret), max_age=LIFETIME_S,
            httponly=True, samesite="strict",  # not readable by JS, not sent by other sites
        )
        return {"ok": True}

    @app.post("/admin/logout")
    def logout(response: Response):
        response.delete_cookie(COOKIE_NAME)
        return {"ok": True}

    @app.get("/admin/api/logs")
    def recent_logs(request: Request, limit: int = 50):
        require_admin(request)
        entries = chat_log.last(max(1, min(limit, 500)))
        return [{key: e.get(key) for key in LOG_FIELDS} for e in reversed(entries)]

    @app.get("/admin/api/debug")
    def get_debug(request: Request):
        require_admin(request)
        return {"enabled": app.state.debug_lines}

    @app.post("/admin/api/debug")
    def set_debug(body: DebugSwitch, request: Request):
        require_admin(request)
        app.state.debug_lines = body.enabled
        return {"enabled": app.state.debug_lines}

    @app.get("/api/demo/attacks")
    def list_attacks(request: Request):
        require_admin(request)
        return attacks

    @app.post("/api/demo/evaluate")
    def evaluate_request(body: EvaluateRequest, request: Request):
        require_admin(request)
        entry = chat_log.find("request_id", body.request_id)
        if entry is None or "model_answer" not in entry:
            raise HTTPException(404, "No answered chat request with this request_id.")
        attack = attacks_by_id.get(entry.get("attack_id"))
        if attack is None:
            raise HTTPException(400, "This request does not belong to a known attack.")
        record = evaluate(entry, attack, settings.system_prompt, settings.detectors, judge)
        eval_log.write(record)
        # what the demo shows next to the verdict, straight from the chat log
        record["chat"] = {key: entry.get(key) for key in (
            "model_answer", "final_answer", "t_model_ms", "t_guard_ms", "t_total_ms")}
        return record
