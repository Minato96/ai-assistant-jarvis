"""Environment-backed settings. No secrets hardcoded — everything comes from .env."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. Copy .env.example to .env and fill it in."
        )
    return value


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    llm_api_key: str
    llm_base_url: str
    model_name: str
    allowed_telegram_user_id: int | None


def load_settings() -> Settings:
    allowed_id_raw = os.getenv("ALLOWED_TELEGRAM_USER_ID")
    return Settings(
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        llm_api_key=_require("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        model_name=os.getenv("MODEL_NAME", "deepseek-chat"),
        allowed_telegram_user_id=int(allowed_id_raw) if allowed_id_raw else None,
    )
