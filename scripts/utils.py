import requests
from . import config

def get_user_wallet_name(user_id: str) -> str:
    """Generates a unique, deterministic wallet name from a Meshtastic user ID."""
    return f"meshtastic_{user_id.lstrip('!')}"

def get_btc_usd_rate() -> float | None:
    """Fetches the current BTC to USD exchange rate from CoinGecko."""
    try:
        response = requests.get(config.COINGECKO_API_URL, timeout=10)
        response.raise_for_status()  # Raises an exception for bad status codes
        data = response.json()
        return float(data['bitcoin']['usd'])
    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        print(f"Error fetching exchange rate: {e}")
        return None
