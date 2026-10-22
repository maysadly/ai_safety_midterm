"""Settings of the prototype.

Two sources, on purpose:
- .env (not in git): secrets and runtime switches - admin password, cookie key,
  salt for hashing IPs, rate limit on/off, log paths. Template: .env.example.
- configs/ (in git): everything that defines the experiment - models, generation
  options, the system prompt and the detector settings. These must not change
  during the experiment, so they are versioned, and the system prompt hash is
  written into every log line.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "configs"


def _flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _path(name: str, default: str) -> Path:
    path = Path(os.environ.get(name, default))
    return path if path.is_absolute() else ROOT / path


@dataclass
class Settings:
    ollama_url: str
    admin_password: str
    cookie_secret: str
    ip_hash_salt: str
    rate_limit_enabled: bool
    rate_limit_per_minute: int
    debug_lines: bool          # start value of the admin "debug lines" switch
    chat_log_path: Path
    eval_log_path: Path
    bot: dict                  # configs/bot.json
    detectors: dict            # configs/detectors.json
    system_prompt: str         # configs/system_prompt.txt
    system_prompt_sha256: str


def load_settings(env_file: Path | None = ROOT / ".env") -> Settings:
    if env_file is not None:
        load_dotenv(env_file)  # variables already set in the shell win over .env

    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    cookie_secret = os.environ.get("COOKIE_SECRET", "")
    if len(admin_password) < 8 or len(cookie_secret) < 16:
        raise RuntimeError(
            "Set ADMIN_PASSWORD (8+ characters) and COOKIE_SECRET (16+ characters) in .env, "
            "see .env.example"
        )

    system_prompt = (CONFIGS / "system_prompt.txt").read_text(encoding="utf-8").strip()
    bot = json.loads((CONFIGS / "bot.json").read_text())
    # Only for the laptop fallback demo, where the experiment's judge does not fit in memory.
    # Every evaluation record stores the judge model it used.
    if os.environ.get("JUDGE_MODEL"):
        bot["judge_model"] = os.environ["JUDGE_MODEL"]
    return Settings(
        ollama_url=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"),
        admin_password=admin_password,
        cookie_secret=cookie_secret,
        ip_hash_salt=os.environ.get("IP_HASH_SALT", ""),
        rate_limit_enabled=_flag("RATE_LIMIT_ENABLED", "true"),
        rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10")),
        debug_lines=_flag("DEBUG_LINES", "false"),
        chat_log_path=_path("CHAT_LOG_PATH", "logs/chat.jsonl"),
        eval_log_path=_path("EVAL_LOG_PATH", "logs/evaluations.jsonl"),
        bot=bot,
        detectors=json.loads((CONFIGS / "detectors.json").read_text()),
        system_prompt=system_prompt,
        system_prompt_sha256=hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
    )
