"""Application configuration via environment variables."""
import logging
import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # App
    app_name: str = "BotForge"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    # Database
    database_url: str = "sqlite+aiosqlite:///./botforge.db"
    # JWT Auth
    # No hardcoded default on purpose - a secret baked into the source code
    # isn't a secret. Set SECRET_KEY in the environment (openssl rand -hex 32).
    # Left blank here; see _require_secret_key below for what happens if it's missing.
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "https://chat-2-two-dun.vercel.app"]
    # Plans
    free_max_bots: int = 1
    free_max_commands: int = 5
    free_max_replies: int = 10
    free_max_messages_per_day: int = 100
    pro_max_bots: int = 5
    pro_max_messages_per_day: int = 10_000
    business_max_bots: int = 999
    business_max_messages_per_day: int = 999_999
    # Paystack Billing (sign up at https://paystack.com)
    paystack_secret_key: str = ""
    paystack_public_key: str = ""
    paystack_pro_plan_code: str = ""      # Paystack Plan code for Pro ($9/mo)
    paystack_business_plan_code: str = ""  # Paystack Plan code for Business ($29/mo)
    app_url: str = "http://localhost:3000"  # Frontend URL for redirects
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def _require_secret_key(self):
        if self.secret_key:
            return self
        if self.debug:
            # Local/dev convenience only: tokens issued this run become invalid
            # on the next restart, since the key isn't persisted anywhere.
            self.secret_key = secrets.token_hex(32)
            logger.warning(
                "SECRET_KEY not set - generated a temporary one for this run only. "
                "Existing/future JWTs will stop working on restart. "
                "Set SECRET_KEY in your environment before deploying."
            )
            return self
        raise ValueError(
            "SECRET_KEY is not set. Refusing to start with DEBUG=false and no "
            "secret key, since that would mean anyone could forge login tokens. "
            "Generate one with `openssl rand -hex 32` and set it as an "
            "environment variable."
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
