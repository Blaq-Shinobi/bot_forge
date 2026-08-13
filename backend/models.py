"""SQLAlchemy ORM models for users and bots."""
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from database import Base
class Plan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
class BotStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    plan = Column(Enum(Plan), default=Plan.FREE, nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    bots = relationship("Bot", back_populates="owner", cascade="all, delete-orphan")
class Bot(Base):
    __tablename__ = "bots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(120), nullable=False)
    token = Column(String(255), nullable=False)
    description = Column(Text, default="")
    welcome_message = Column(Text, default="Hello! How can I help you?")
    fallback_message = Column(Text, default="Sorry, I didn't understand that.")
    status = Column(Enum(BotStatus), default=BotStatus.PAUSED, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    owner = relationship("User", back_populates="bots")
    commands = relationship("BotCommand", back_populates="bot", cascade="all, delete-orphan")
    auto_replies = relationship("AutoReply", back_populates="bot", cascade="all, delete-orphan")
    scheduled_messages = relationship("ScheduledMessage", back_populates="bot", cascade="all, delete-orphan")
class BotCommand(Base):
    __tablename__ = "bot_commands"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    command = Column(String(64), nullable=False)  # e.g. /start, /help
    response = Column(Text, default="")
    bot = relationship("Bot", back_populates="commands")
class AutoReply(Base):
    __tablename__ = "auto_replies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    trigger = Column(String(255), nullable=False)  # keyword to match
    reply = Column(Text, default="")
    bot = relationship("Bot", back_populates="auto_replies")
class ScheduledMessage(Base):
    __tablename__ = "scheduled_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    message = Column(Text, nullable=False)
    cron_hour = Column(Integer, nullable=False)   # 0-23
    cron_minute = Column(Integer, nullable=False)  # 0-59
    enabled = Column(Boolean, default=True)
    bot = relationship("Bot", back_populates="scheduled_messages")
