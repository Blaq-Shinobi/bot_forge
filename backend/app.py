"""BotForge — FastAPI backend.  Run with:  uvicorn app:app --reload"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from config import get_settings
from database import get_db, init_db
from models import (
    User, Bot, BotCommand, AutoReply, ScheduledMessage, BotStatus, Plan,
)
from schemas import (
    SignupRequest, LoginRequest, TokenResponse, UserResponse,
    BotCreate, BotUpdate, BotResponse, BotListResponse,
    CommandSchema, AutoReplySchema, ScheduledMessageSchema,
)
from auth import hash_password, verify_password, create_access_token, get_current_user
import bot_runner
import billing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")
    yield
    await bot_runner.stop_all_bots()
    logger.info("All bots stopped")


# ── App ───────────────────────────────────────────────
app = FastAPI(title="BotForge API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Paystack Webhook ──

@app.post("/api/billing/webhook")
async def paystack_webhook(request: Request):
    """Handle Paystack webhook events."""
    import json
    payload = await request.body()

    try:
        event = json.loads(payload)
    except Exception as e:
        logger.error(f"Webhook parse error: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event_type = event.get("event", "")
    logger.info(f"Paystack webhook: {event_type}")

    if event_type == "charge.success":
        await billing.handle_charge_success(event)
    elif event_type == "subscription.create":
        await billing.handle_subscription_create(event)
    elif event_type == "subscription.disable":
        await billing.handle_subscription_disable(event)

    return {"status": "ok"}


# ═══════════════════════════════════════════════════════
#  AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.post("/api/auth/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    # Check existing user
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


# ═══════════════════════════════════════════════════════
#  BOT CRUD ENDPOINTS
# ═══════════════════════════════════════════════════════

def _bot_to_response(bot: Bot) -> BotResponse:
    return BotResponse(
        id=bot.id,
        name=bot.name,
        description=bot.description,
        welcome_message=bot.welcome_message,
        fallback_message=bot.fallback_message,
        status=bot.status.value if bot.status else "paused",
        created_at=bot.created_at,
        updated_at=bot.updated_at,
        commands=[CommandSchema(command=c.command, response=c.response) for c in bot.commands],
        auto_replies=[AutoReplySchema(trigger=a.trigger, reply=a.reply) for a in bot.auto_replies],
        scheduled_messages=[
            ScheduledMessageSchema(message=s.message, cron_hour=s.cron_hour, cron_minute=s.cron_minute, enabled=s.enabled)
            for s in bot.scheduled_messages
        ],
    )


@app.get("/api/bots", response_model=list[BotListResponse])
async def list_bots(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bot).where(Bot.owner_id == user.id).order_by(Bot.created_at.desc())
    )
    return result.scalars().all()


@app.post("/api/bots", response_model=BotResponse, status_code=201)
async def create_bot(
    body: BotCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Plan limit check
    bot_count = await db.scalar(select(func.count()).where(Bot.owner_id == user.id).select_from(Bot))
    max_bots = {Plan.FREE: settings.free_max_bots, Plan.PRO: settings.pro_max_bots, Plan.BUSINESS: settings.business_max_bots}
    if bot_count >= max_bots.get(user.plan, 1):
        raise HTTPException(status_code=403, detail=f"Bot limit reached for {user.plan.value} plan. Upgrade to add more.")

    bot = Bot(
        owner_id=user.id,
        name=body.name,
        token=body.token,
        description=body.description,
        welcome_message=body.welcome_message,
        fallback_message=body.fallback_message,
    )
    db.add(bot)
    await db.flush()  # get bot.id

    # Add commands
    for cmd in body.commands:
        db.add(BotCommand(bot_id=bot.id, command=cmd.command, response=cmd.response))

    # Add auto-replies
    for ar in body.auto_replies:
        db.add(AutoReply(bot_id=bot.id, trigger=ar.trigger, reply=ar.reply))

    # Add scheduled messages
    for sm in body.scheduled_messages:
        db.add(ScheduledMessage(bot_id=bot.id, message=sm.message, cron_hour=sm.cron_hour, cron_minute=sm.cron_minute, enabled=sm.enabled))

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.commands), selectinload(Bot.auto_replies), selectinload(Bot.scheduled_messages))
        .where(Bot.id == bot.id)
    )
    bot = result.scalar_one()
    return _bot_to_response(bot)


@app.get("/api/bots/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.commands), selectinload(Bot.auto_replies), selectinload(Bot.scheduled_messages))
        .where(Bot.id == bot_id, Bot.owner_id == user.id)
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return _bot_to_response(bot)


@app.put("/api/bots/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: int,
    body: BotUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.commands), selectinload(Bot.auto_replies), selectinload(Bot.scheduled_messages))
        .where(Bot.id == bot_id, Bot.owner_id == user.id)
    )
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    # Update scalar fields
    if body.name is not None:
        bot.name = body.name
    if body.token is not None:
        bot.token = body.token
    if body.description is not None:
        bot.description = body.description
    if body.welcome_message is not None:
        bot.welcome_message = body.welcome_message
    if body.fallback_message is not None:
        bot.fallback_message = body.fallback_message

    # Replace commands
    if body.commands is not None:
        for cmd in bot.commands:
            await db.delete(cmd)
        for cmd in body.commands:
            db.add(BotCommand(bot_id=bot.id, command=cmd.command, response=cmd.response))

    # Replace auto-replies
    if body.auto_replies is not None:
        for ar in bot.auto_replies:
            await db.delete(ar)
        for ar in body.auto_replies:
            db.add(AutoReply(bot_id=bot.id, trigger=ar.trigger, reply=ar.reply))

    # Replace scheduled messages
    if body.scheduled_messages is not None:
        for sm in bot.scheduled_messages:
            await db.delete(sm)
        for sm in body.scheduled_messages:
            db.add(ScheduledMessage(bot_id=bot.id, message=sm.message, cron_hour=sm.cron_hour, cron_minute=sm.cron_minute, enabled=sm.enabled))

    await db.commit()

    # Reload
    result = await db.execute(
        select(Bot)
        .options(selectinload(Bot.commands), selectinload(Bot.auto_replies), selectinload(Bot.scheduled_messages))
        .where(Bot.id == bot.id)
    )
    bot = result.scalar_one()
    return _bot_to_response(bot)


@app.delete("/api/bots/{bot_id}", status_code=204)
async def delete_bot(
    bot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.owner_id == user.id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    await bot_runner.stop_bot(bot_id)
    await db.delete(bot)
    await db.commit()


# ═══════════════════════════════════════════════════════
#  BOT CONTROL ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.post("/api/bots/{bot_id}/start")
async def start_bot_endpoint(
    bot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Bot not found")

    success = await bot_runner.start_bot(bot_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start bot. Check the token.")
    return {"status": "started"}


@app.post("/api/bots/{bot_id}/stop")
async def stop_bot_endpoint(
    bot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Bot not found")

    await bot_runner.stop_bot(bot_id)
    return {"status": "stopped"}


@app.post("/api/bots/{bot_id}/restart")
async def restart_bot_endpoint(
    bot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Bot).where(Bot.id == bot_id, Bot.owner_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Bot not found")

    success = await bot_runner.restart_bot(bot_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to restart bot.")
    return {"status": "restarted"}


# ═══════════════════════════════════════════════════════
#  DASHBOARD STATS
# ═══════════════════════════════════════════════════════

@app.get("/api/stats")
async def get_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bot_count = await db.scalar(select(func.count()).where(Bot.owner_id == user.id).select_from(Bot))
    active_count = await db.scalar(
        select(func.count()).where(Bot.owner_id == user.id, Bot.status == BotStatus.ACTIVE).select_from(Bot)
    )
    running_ids = bot_runner.get_running_bot_ids()

    return {
        "total_bots": bot_count or 0,
        "active_bots": active_count or 0,
        "running_bots": len(running_ids),
        "plan": user.plan.value,
    }


# ═══════════════════════════════════════════════════════
#  HEALTH CHECK
# ═══════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "BotForge API"}


# ═══════════════════════════════════════════════════════
#  BILLING ENDPOINTS
# ═══════════════════════════════════════════════════════

class CheckoutRequest(BaseModel):
    plan: str  # "pro" or "business"

@app.post("/api/billing/checkout")
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
):
    """Create a Paystack Checkout session for plan upgrade."""
    if body.plan == "pro":
        plan_code = settings.paystack_pro_plan_code
    elif body.plan == "business":
        plan_code = settings.paystack_business_plan_code
    else:
        raise HTTPException(status_code=400, detail="Invalid plan. Use 'pro' or 'business'.")

    if not plan_code:
        raise HTTPException(
            status_code=503,
            detail=f"{body.plan.capitalize()} plan is not configured yet. Add the Paystack Plan Code to .env"
        )

    try:
        result = billing.create_checkout_session(
            user_email=user.email,
            plan_code=plan_code,
            user_id=user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/billing/status")
async def billing_status(user: User = Depends(get_current_user)):
    """Get current billing status."""
    return {
        "plan": user.plan.value,
        "has_subscription": bool(user.stripe_subscription_id),
        "stripe_configured": billing.is_configured(),
        "publishable_key": settings.paystack_public_key,
    }
