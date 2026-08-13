"""Paystack billing integration — checkout, webhooks, plan management.
Designed for Nigerian founders. Docs: https://paystack.com/docs/api/
"""

import httpx
import logging
from sqlalchemy import select

from config import get_settings
from database import async_session
from models import User, Plan

logger = logging.getLogger(__name__)
settings = get_settings()

# Paystack API base
PAYSTACK_API = "https://api.paystack.co"


def _headers() -> dict:
    """Paystack auth headers."""
    return {
        "Authorization": f"Bearer {settings.paystack_secret_key}",
        "Content-Type": "application/json",
    }


def is_configured() -> bool:
    """Check if Paystack is properly configured."""
    return bool(settings.paystack_secret_key and settings.paystack_public_key)


def create_checkout_session(user_email: str, plan_code: str, user_id: int) -> dict:
    """Create a Paystack checkout session for subscription."""
    if not is_configured():
        raise ValueError("Paystack is not configured. Add your API keys to .env")

    with httpx.Client() as client:
        resp = client.post(
            f"{PAYSTACK_API}/transaction/initialize",
            headers=_headers(),
            json={
                "email": user_email,
                "plan": plan_code,
                "callback_url": f"{settings.app_url}/pages/dashboard.html?upgrade=success",
                "metadata": {
                    "user_id": str(user_id),
                    "cancel_action": f"{settings.app_url}/index.html#pricing",
                },
            },
            timeout=15,
        )
        data = resp.json()

    if not data.get("status"):
        raise ValueError(f"Paystack error: {data.get('message', 'Unknown error')}")

    auth_url = data["data"]["authorization_url"]
    ref = data["data"]["reference"]
    return {"checkout_url": auth_url, "session_id": ref}


def verify_transaction(reference: str) -> dict:
    """Verify a completed Paystack transaction."""
    if not is_configured():
        raise ValueError("Paystack is not configured")

    with httpx.Client() as client:
        resp = client.get(
            f"{PAYSTACK_API}/transaction/verify/{reference}",
            headers=_headers(),
            timeout=15,
        )
        data = resp.json()

    if not data.get("status"):
        raise ValueError(f"Verification failed: {data.get('message', 'Unknown')}")

    return data["data"]


async def handle_charge_success(event: dict):
    """Handle charge.success webhook — user paid for a subscription."""
    data = event.get("data", {})
    metadata = data.get("metadata", {})
    user_id_str = metadata.get("user_id")
    if not user_id_str:
        logger.warning("charge.success webhook missing user_id in metadata")
        return

    user_id = int(user_id_str)
    plan_code = data.get("plan", {}).get("plan_code", "") if isinstance(data.get("plan"), dict) else ""

    # Determine plan from the Paystack plan code
    plan = Plan.PRO  # default
    if plan_code and plan_code == settings.paystack_business_plan_code:
        plan = Plan.BUSINESS
    elif plan_code and plan_code == settings.paystack_pro_plan_code:
        plan = Plan.PRO

    subscription_code = data.get("subscription", {}).get("subscription_code", "") if isinstance(data.get("subscription"), dict) else ""
    customer_email = data.get("customer", {}).get("email", "") if isinstance(data.get("customer"), dict) else ""

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.plan = plan
            user.stripe_customer_id = customer_email  # reuse field for customer identifier
            user.stripe_subscription_id = subscription_code  # reuse field for subscription code
            await db.commit()
            logger.info(f"User {user_id} upgraded to {plan.value} via Paystack")


async def handle_subscription_disable(event: dict):
    """Handle subscription.disable — user cancelled or payment failed repeatedly."""
    data = event.get("data", {})
    subscription_code = data.get("subscription_code", "")

    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.stripe_subscription_id == subscription_code)
        )
        user = result.scalar_one_or_none()
        if user:
            user.plan = Plan.FREE
            user.stripe_subscription_id = None
            await db.commit()
            logger.info(f"User {user.id} downgraded to Free (subscription disabled)")


async def handle_subscription_create(event: dict):
    """Handle subscription.create — new recurring subscription activated."""
    # The charge.success event already handles the upgrade,
    # but this confirms the recurring billing is active
    data = event.get("data", {})
    logger.info(f"Paystack subscription created: {data.get('subscription_code', 'unknown')}")
