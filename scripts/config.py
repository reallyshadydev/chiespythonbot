import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bitcoin Core RPC Configuration
RPC_HOST = os.getenv("RPC_HOST", "127.0.0.1")
RPC_PORT = os.getenv("RPC_PORT", "18332")
RPC_USER = os.getenv("RPC_USER")
RPC_PASSWORD = os.getenv("RPC_PASSWORD")

# Node Operator Configuration
NODE_OPERATOR_ADDRESS = os.getenv("NODE_OPERATOR_ADDRESS")
NODE_OPERATOR_FEE_PERCENT = float(os.getenv("NODE_OPERATOR_FEE_PERCENT", 0.5))

# API Configuration
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"

# Validation
if not RPC_USER or not RPC_PASSWORD:
    raise ValueError("RPC_USER and RPC_PASSWORD must be set in your .env file.")
if not NODE_OPERATOR_ADDRESS or "x" in NODE_OPERATOR_ADDRESS:
    print("WARNING: NODE_OPERATOR_ADDRESS is not set correctly in your .env file.")
