"""Script to create and deploy CryptoPulseBot with pre-configured commands.

NOTE: TOKEN and BOT_TOKEN below were originally hardcoded with real live secrets.
They've been redacted here. Get a fresh Telegram bot token from @BotFather
(after revoking the old exposed one) and load it from an environment variable
instead of hardcoding it in this file.
"""

import httpx
import os

TOKEN = os.environ.get("BOTFORGE_ADMIN_JWT", "")  # your BotForge JWT, not a secret to hardcode
BASE = os.environ.get("BOTFORGE_API_BASE", "http://localhost:8000/api")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

bot_config = {
    "name": "CryptoPulseBot",
    "token": os.environ.get("CRYPTOPULSE_BOT_TOKEN", ""),  # get a fresh token from @BotFather
    "description": "Real-time crypto signals, prices, and market alerts.",
    "welcome_message": "Welcome to CryptoPulse! I track crypto markets for you.\n\nUse these commands:\n/price BTC - Check price\n/market - Market overview\n/signals - Latest signals\n/help - All commands",
    "fallback_message": "I didn't catch that. Try /help to see what I can do, or /price BTC to check a coin!",
    "commands": [
        {"command": "/start", "response": "Hey! I'm CryptoPulse - your crypto market assistant.\n\nTry:\n/price BTC - Bitcoin price\n/price ETH - Ethereum price\n/market - Market overview\n/signals - Latest trading signals\n/help - All commands"},
        {"command": "/help", "response": "Available commands:\n\n/price <coin> - Check coin price (BTC, ETH, SOL, etc.)\n/market - Full market overview\n/signals - Latest trading signals\n/alerts - Set price alerts\n/about - About CryptoPulse"},
        {"command": "/price", "response": "To check a price, type: /price BTC, /price ETH, /price SOL, etc.\n\nCurrently tracking: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX"},
        {"command": "/market", "response": "Market Overview:\n\nThe crypto market is dynamic right now! Check individual coins with /price <coin>.\n\nFear & Greed Index updates available via /signals.\nFor real-time data, upgrade to Pro for live API integration!"},
        {"command": "/signals", "response": "Latest Signals:\n\nBTC - Neutral (watching $65K support)\nETH - Bullish (breaking resistance)\nSOL - Bullish (strong momentum)\n\nUpgrade to Pro for real-time automated signals with entry/exit points!"},
        {"command": "/alerts", "response": "Price Alerts (Pro Feature):\n\nSet custom alerts like:\n- BTC drops below $60,000\n- ETH hits $4,000\n- SOL rises 10% in 24h\n\nUpgrade to Pro at botforge.io to unlock alerts!"},
        {"command": "/about", "response": "CryptoPulse by BotForge\n\nI help you stay on top of crypto markets with real-time prices, signals, and alerts.\n\nBuilt with BotForge - the no-code Telegram bot builder.\nVisit botforge.io to build your own bot!"},
    ],
    "auto_replies": [
        {"trigger": "bitcoin", "reply": "Bitcoin (BTC) - Check the latest price with /price BTC. For real-time tracking, upgrade to Pro!"},
        {"trigger": "ethereum", "reply": "Ethereum (ETH) - Check the latest price with /price ETH. For real-time tracking, upgrade to Pro!"},
        {"trigger": "solana", "reply": "Solana (SOL) - Check the latest price with /price SOL. For real-time tracking, upgrade to Pro!"},
        {"trigger": "signal", "reply": "Check latest signals with /signals. For real-time automated signals, upgrade to Pro at botforge.io!"},
        {"trigger": "price", "reply": "Use /price <coin> to check prices. E.g. /price BTC, /price ETH, /price SOL"},
        {"trigger": "buy", "reply": "I can't give financial advice, but check /signals for market analysis and /market for the overall trend!"},
        {"trigger": "sell", "reply": "I can't give financial advice, but check /signals for market analysis and /market for the overall trend!"},
    ],
    "scheduled_messages": [],
}

# Create bot
print("Creating bot...")
r = httpx.post(f"{BASE}/bots", json=bot_config, headers=HEADERS, timeout=10)
print(f"Create: {r.status_code} - {r.text}")

if r.status_code == 201:
    bot_id = r.json()["id"]
    # Start bot
    print(f"Starting bot #{bot_id}...")
    r2 = httpx.post(f"{BASE}/bots/{bot_id}/start", headers=HEADERS, timeout=10)
    print(f"Start: {r2.status_code} - {r2.text}")
    print("\nCryptoPulseBot is LIVE! Go message @CryptoPulse17_Bot on Telegram!")
else:
    print("Failed to create bot")
