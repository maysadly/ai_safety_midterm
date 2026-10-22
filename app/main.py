"""FastAPI app: the Pixelkiln website, the chat API, /demo and /admin.

Run (from the repository root):
    .venv/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000

create_app() is a factory so tests can pass their own settings and a fake LLM.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.gateway import BotUnavailable, Gateway
from app.jsonl_log import JsonlLog
from app.ollama_client import OllamaClient
from app.ratelimit import RateLimiter
from app.sessions import SessionStore
from app.settings import Settings, load_settings

STATIC = Path(__file__).resolve().parent / "static"

PAGES = {
    "/": "index.html",
    "/pricing": "pricing.html",
    "/faq": "faq.html",
    "/about": "about.html",
}

# Only our own files may run or load on our pages. Even if a model answer ever got
# into the page as HTML, an inline <script> in it would not run (defence in depth;
# the main protection is that the widget inserts answers with textContent).
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    # Optional: without session_id the message is answered on its own (garak mode).
    session_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    attack_id: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$")
    source: str = Field(default="api", max_length=20, pattern=r"^[a-z_]+$")


def hash_ip(ip: str, salt: str) -> str:
    """Logs keep only a salted hash of the client IP, never the IP itself."""
    return hashlib.sha256(f"{salt}{ip}".encode()).hexdigest()[:16]


def create_app(settings: Settings | None = None, llm=None) -> FastAPI:
    settings = settings or load_settings()
    llm = llm or OllamaClient(settings.ollama_url)
    chat_log = JsonlLog(settings.chat_log_path)
    gateway = Gateway(
        settings, llm, SessionStore(max_messages=settings.bot["max_history_messages"]), chat_log
    )
    limiter = RateLimiter(settings.rate_limit_per_minute)

    app = FastAPI(title="Pixelkiln (fictional) - support chatbot demo", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.gateway = gateway
    app.state.debug_lines = settings.debug_lines  # switched on/off in /admin

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    def page(file_name: str):
        return lambda: FileResponse(STATIC / file_name)

    for path, file_name in PAGES.items():
        app.add_api_route(path, page(file_name), methods=["GET"], include_in_schema=False)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "bot_model": settings.bot["bot_model"],
            "system_prompt_sha256": settings.system_prompt_sha256,
        }

    @app.post("/api/chat")
    def chat(body: ChatRequest, request: Request):
        if len(body.message) > settings.bot["max_message_chars"]:
            raise HTTPException(413, "Message is too long.")

        ip_hash = hash_ip(request.client.host if request.client else "", settings.ip_hash_salt)
        if settings.rate_limit_enabled and not limiter.allow(ip_hash):
            chat_log.write(
                {
                    "time": datetime.now(timezone.utc).isoformat(),
                    "source": body.source,
                    "session_id": body.session_id,
                    "attack_id": body.attack_id,
                    "client_ip_hash": ip_hash,
                    "user_message": body.message,
                    "blocked_by": "rate_limit",
                }
            )
            raise HTTPException(429, "Too many messages. Wait a minute and try again.")

        try:
            result = gateway.handle(
                body.message,
                session_id=body.session_id,
                attack_id=body.attack_id,
                source=body.source,
                client_ip_hash=ip_hash,
            )
        except BotUnavailable:
            raise HTTPException(503, "The assistant is not available right now. Try again later.")

        response = {"reply": result.reply, "request_id": result.request_id}
        if app.state.debug_lines:
            response["debug"] = {
                "blocked_by": result.blocked_by,
                "guard_verdict": result.guard_verdict,
                "t_model_ms": result.t_model_ms,
                "t_guard_ms": result.t_guard_ms,
                "t_total_ms": result.t_total_ms,
            }
        return response

    return app
