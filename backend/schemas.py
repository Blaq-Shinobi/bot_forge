"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
# ── Auth ──────────────────────────────────────────────
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    plan: str
    created_at: datetime
    model_config = {"from_attributes": True}
# ── Bot ───────────────────────────────────────────────
class CommandSchema(BaseModel):
    command: str
    response: str
class AutoReplySchema(BaseModel):
    trigger: str
    reply: str
class ScheduledMessageSchema(BaseModel):
    message: str
    cron_hour: int
    cron_minute: int
    enabled: bool = True
class BotCreate(BaseModel):
    name: str
    token: str
    description: str = ""
    welcome_message: str = "Hello! How can I help you?"
    fallback_message: str = "Sorry, I didn't understand that."
    commands: list[CommandSchema] = []
    auto_replies: list[AutoReplySchema] = []
    scheduled_messages: list[ScheduledMessageSchema] = []
class BotUpdate(BaseModel):
    name: Optional[str] = None
    token: Optional[str] = None
    description: Optional[str] = None
    welcome_message: Optional[str] = None
    fallback_message: Optional[str] = None
    commands: Optional[list[CommandSchema]] = None
    auto_replies: Optional[list[AutoReplySchema]] = None
    scheduled_messages: Optional[list[ScheduledMessageSchema]] = None
class BotResponse(BaseModel):
    id: int
    name: str
    description: str
    welcome_message: str
    fallback_message: str
    status: str
    created_at: datetime
    updated_at: datetime
    commands: list[CommandSchema] = []
    auto_replies: list[AutoReplySchema] = []
    scheduled_messages: list[ScheduledMessageSchema] = []
    model_config = {"from_attributes": True}
class BotListResponse(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}
