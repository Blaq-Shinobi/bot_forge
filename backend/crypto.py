"""Live crypto data from CoinGecko and Fear & Greed Index APIs."""

import httpx
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# CoinGecko free API (no key needed)
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Map common symbols to CoinGecko IDs
COIN_IDS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "ada": "cardano",
    "doge": "dogecoin",
    "avax": "avalanche-2",
    "dot": "polkadot",
    "matic": "matic-network",
    "link": "chainlink",
    "uni": "uniswap",
    "atom": "cosmos",
    "near": "near",
    "apt": "aptos",
    "arb": "arbitrum",
    "op": "optimism",
    "sui": "sui",
    "pepe": "pepe",
    "shib": "shiba-inu",
}


async def get_price(symbol: str) -> str:
    """Fetch live price for a coin. Returns formatted string."""
    coin_id = COIN_IDS.get(symbol.lower().strip())
    if not coin_id:
        supported = ", ".join(sorted(COIN_IDS.keys()))
        return f"Unknown coin '{symbol}'. Supported: {supported}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={
                    "ids": coin_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                },
            )
            r.raise_for_status()
            data = r.json()[coin_id]

            price = data["usd"]
            change = data.get("usd_24h_change", 0)
            mcap = data.get("usd_market_cap", 0)

            # Format price
            if price >= 1:
                price_str = f"${price:,.2f}"
            else:
                price_str = f"${price:.6f}"

            # Format change
            arrow = "▲" if change >= 0 else "▼"
            change_str = f"{arrow} {abs(change):.2f}%"

            # Format market cap
            if mcap >= 1e12:
                mcap_str = f"${mcap/1e12:.2f}T"
            elif mcap >= 1e9:
                mcap_str = f"${mcap/1e9:.2f}B"
            else:
                mcap_str = f"${mcap/1e6:.2f}M"

            return (
                f"{symbol.upper()} Live Price\n\n"
                f"💰 Price: {price_str}\n"
                f"📈 24h: {change_str}\n"
                f"🏦 Market Cap: {mcap_str}\n\n"
                f"Source: CoinGecko • {datetime.now(timezone.utc).strftime('%H:%M UTC')}"
            )
    except Exception as e:
        logger.error(f"Price fetch error for {symbol}: {e}")
        return f"Failed to fetch price for {symbol.upper()}. Try again in a moment."


async def get_market_overview() -> str:
    """Fetch top coins market overview."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Top coins
            r = await client.get(
                f"{COINGECKO_BASE}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "ids": "bitcoin,ethereum,solana,binancecoin,ripple",
                    "order": "market_cap_desc",
                },
            )
            r.raise_for_status()
            coins = r.json()

            # Fear & Greed Index
            fg_text = ""
            try:
                fg_r = await client.get("https://api.alternative.me/fng/?limit=1")
                if fg_r.status_code == 200:
                    fg_data = fg_r.json()["data"][0]
                    fg_value = int(fg_data["value"])
                    fg_class = fg_data["value_classification"]
                    fg_emoji = "😱" if fg_value <= 25 else "😐" if fg_value <= 50 else "😊" if fg_value <= 75 else "🤑"
                    fg_text = f"\n\n{fg_emoji} Fear & Greed: {fg_value}/100 ({fg_class})"
            except Exception:
                pass

            lines = ["📊 Market Overview\n"]
            for coin in coins:
                symbol = coin["symbol"].upper()
                price = coin["current_price"]
                change = coin.get("price_change_percentage_24h", 0) or 0
                arrow = "▲" if change >= 0 else "▼"

                if price >= 1:
                    price_str = f"${price:,.2f}"
                else:
                    price_str = f"${price:.6f}"

                lines.append(f"  {symbol}: {price_str} {arrow}{abs(change):.2f}%")

            lines.append(f"\n⏰ {datetime.now(timezone.utc).strftime('%b %d, %H:%M UTC')}")
            lines.append(fg_text)

            return "\n".join(lines)
    except Exception as e:
        logger.error(f"Market overview error: {e}")
        return "Failed to fetch market data. Try again in a moment."


async def get_top_movers() -> str:
    """Get top gainers and losers in top 50 coins."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{COINGECKO_BASE}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 50,
                    "page": 1,
                },
            )
            r.raise_for_status()
            coins = r.json()

            # Sort by 24h change
            coins_with_change = [c for c in coins if c.get("price_change_percentage_24h") is not None]
            gainers = sorted(coins_with_change, key=lambda c: c["price_change_percentage_24h"], reverse=True)[:5]
            losers = sorted(coins_with_change, key=lambda c: c["price_change_percentage_24h"])[:5]

            lines = ["🚀 Top Gainers (24h)\n"]
            for c in gainers:
                sym = c["symbol"].upper()
                chg = c["price_change_percentage_24h"]
                lines.append(f"  ▲ {sym}: +{chg:.2f}%")

            lines.append("\n📉 Top Losers (24h)\n")
            for c in losers:
                sym = c["symbol"].upper()
                chg = c["price_change_percentage_24h"]
                lines.append(f"  ▼ {sym}: {chg:.2f}%")

            lines.append(f"\n⏰ {datetime.now(timezone.utc).strftime('%b %d, %H:%M UTC')}")

            return "\n".join(lines)
    except Exception as e:
        logger.error(f"Top movers error: {e}")
        return "Failed to fetch top movers. Try again in a moment."
