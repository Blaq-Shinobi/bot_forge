"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings
from functools import lru_cache
class Settings(BaseSettings):
    # App
    app_name: str = "BotForge"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    # Database
    database_url: str = "sqlite+aiosqlite:///./botforge.db"
    # JWT Auth
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
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
@lru_cache
def get_settings() -> Settings:
    return Settings()
