import os
import time
import atexit
import requests
import meshtastic
import meshtastic.serial_interface
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

# --- Configuration ---
# It's highly recommended to use environment variables for security.
RPC_HOST = os.getenv("RPC_HOST", "127.0.0.1")
RPC_PORT = os.getenv("RPC_PORT", "18332") # Default for testnet
RPC_USER = os.getenv("RPC_USER")
RPC_PASSWORD = os.getenv("RPC_PASSWORD")

# --- New Fee and Exchange Rate Configuration ---
# The address where node operator fees will be collected.
# IMPORTANT: Set this to your actual Bitcoin address.
NODE_OPERATOR_ADDRESS = os.getenv("NODE_OPERATOR_ADDRESS", "tb1qxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx") # CHANGE THIS
# The fee percentage (e.g., 0.5 for 0.5%).
NODE_OPERATOR_FEE_PERCENT = 0.5
# API for fetching BTC to USD exchange rate.
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"

# --- Helper Functions ---
def get_user_wallet_name(user_id):
    """Generates a unique, deterministic wallet name from a Meshtastic user ID."""
    return f"meshtastic_{user_id.lstrip('!')}"

def get_btc_usd_rate():
    """Fetches the current BTC to USD exchange rate from CoinGecko."""
    try:
        response = requests.get(COINGECKO_API_URL, timeout=10)
        response.raise_for_status() # Raises an exception for bad status codes
        data = response.json()
        return float(data['bitcoin']['usd'])
    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        print(f"Error fetching exchange rate: {e}")
        return None

# --- Bitcoin RPC Interaction Class ---
class BitcoinRPC:
    def __init__(self):
        if not RPC_USER or not RPC_PASSWORD:
            raise ValueError("RPC_USER and RPC_PASSWORD environment variables must be set.")
        if "x" in NODE_OPERATOR_ADDRESS: # Basic check for default address
             print("WARNING: NODE_OPERATOR_ADDRESS is not set. Please configure it.")
        
        self.rpc_connection = None
        try:
            self.rpc_connection = AuthServiceProxy(
                f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}/"
            )
            # Test connection
            self.rpc_connection.getblockchaininfo()
            print("Successfully connected to Bitcoin Core RPC.")
        except Exception as e:
            print(f"Error: Could not connect to Bitcoin Core RPC.")
            print(f"Please ensure your bitcoin.conf is set up correctly and bitcoind is running.")
            print(f"Details: {e}")
            exit(1)

    def get_rpc_for_wallet(self, wallet_name):
        """Returns an RPC proxy instance for a specific wallet."""
        return AuthServiceProxy(
            f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}/wallet/{wallet_name}"
        )

    def wallet_exists(self, wallet_name):
        """Checks if a wallet is loaded."""
        return wallet_name in self.rpc_connection.listwallets()

    def get_or_create_wallet(self, user_id):
        """Creates a new wallet for a user if it doesn't exist."""
        wallet_name = get_user_wallet_name(user_id)
        if self.wallet_exists(wallet_name):
            return f"Wallet '{wallet_name}' already exists."
        
        try:
            self.rpc_connection.createwallet(wallet_name)
            return f"Successfully created and loaded new wallet: '{wallet_name}'."
        except JSONRPCException as e:
            return f"Error creating wallet: {e.message}"

    def get_balance(self, user_id):
        """Gets the balance of a user's wallet in BTC and USD."""
        wallet_name = get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return "Wallet not found. Use !createwallet first."
        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            balance_btc = wallet_rpc.getbalance()
            
            rate = get_btc_usd_rate()
            if rate:
                balance_usd = balance_btc * rate
                return f"Balance: {balance_btc:.8f} BTC (~${balance_usd:,.2f} USD)"
            else:
                return f"Balance: {balance_btc:.8f} BTC (USD rate unavailable)"
        except JSONRPCException as e:
            return f"Error getting balance: {e.message}"

    def get_new_address(self, user_id):
        """Gets a new receiving address for the user."""
        wallet_name = get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return "Wallet not found. Use !createwallet first."
        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            address = wallet_rpc.getnewaddress()
            return f"Your address: {address}"
        except JSONRPCException as e:
            return f"Error getting address: {e.message}"

    def get_private_key(self, user_id, address):
        """Dumps the private key for a given address."""
        wallet_name = get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return "Wallet not found. Use !createwallet first."
        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            priv_key = wallet_rpc.dumpprivkey(address)
            return f"WARNING: Private key for {address}: {priv_key}"
        except JSONRPCException as e:
            return f"Error getting private key: {e.message}"

    def send_payment(self, user_id, to_address, amount_str):
        """
        Processes a payment, handling USD conversion and node fees.
        Uses sendmany for atomic transactions with multiple outputs.
        """
        wallet_name = get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return "Wallet not found. Use !createwallet first."

        rate = get_btc_usd_rate()
        if not rate:
            return "Error: Cannot process transaction, exchange rate is unavailable."

        try:
            # Convert amount from USD or parse as BTC
            if amount_str.startswith('$'):
                amount_usd = float(amount_str[1:])
                send_amount_btc = amount_usd / rate
            else:
                send_amount_btc = float(amount_str)
                amount_usd = send_amount_btc * rate
        except ValueError:
            return "Error: Invalid amount specified."

        # Calculate node fee
        fee_btc = send_amount_btc * (NODE_OPERATOR_FEE_PERCENT / 100.0)
        total_btc = send_amount_btc + fee_btc
        total_usd = total_btc * rate
        fee_usd = fee_btc * rate

        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            
            # Check for sufficient funds
            balance_btc = wallet_rpc.getbalance()
            if balance_btc < total_btc:
                return f"Error: Insufficient funds. Need {total_btc:.8f} BTC, have {balance_btc:.8f} BTC."

            # Prepare outputs for sendmany
            outputs = {
                to_address: f"{send_amount_btc:.8f}",
                NODE_OPERATOR_ADDRESS: f"{fee_btc:.8f}"
            }

            # Use sendmany to send to recipient and fee address in one transaction
            txid = wallet_rpc.sendmany("", outputs) # First arg is a dummy

            # Build detailed response
            response = (
                f"Success! Sent ${amount_usd:,.2f} ({send_amount_btc:.8f} BTC).\n"
                f"Fee ({NODE_OPERATOR_FEE_PERCENT}%): ${fee_usd:,.2f} ({fee_btc:.8f} BTC).\n"
                f"Total: ${total_usd:,.2f} ({total_btc:.8f} BTC).\n"
                f"TXID: {txid}"
            )
            return response

        except JSONRPCException as e:
            return f"Error sending transaction: {e.message}"
        except Exception as e:
            return f"An unexpected error occurred during send: {e}"

# --- Meshtastic Bot Class ---
class MeshtasticBot:
    def __init__(self):
        self.btc_rpc = BitcoinRPC()
        self.interface = None
        print("Meshtastic Bitcoin Bot initializing...")

    def connect(self):
        """Connects to the Meshtastic device."""
        try:
            self.interface = meshtastic.serial_interface.SerialInterface()
            atexit.register(self.cleanup)
            print("Connected to Meshtastic device.")
        except Exception as e:
            print(f"Error: Could not connect to Meshtastic device on serial port.")
            print(f"Details: {e}")
            exit(1)

    def on_receive(self, packet, interface):
        """Callback for when a packet is received."""
        if packet.get('decoded') and packet['decoded'].get('portnum') == 'TEXT_MESSAGE_APP':
            msg = packet['decoded']['text']
            sender_id = packet['fromId']
            
            print(f"Received message: '{msg}' from user: {sender_id}")

            if msg.startswith('!'):
                self.handle_command(msg, sender_id)

    def on_connection(self, interface, topic=None):
        """Callback for when a connection is established."""
        print("Connection to Meshtastic node established.")

    def handle_command(self, msg, sender_id):
        """Parses and executes commands."""
        parts = msg.strip().split()
        command = parts[0].lower()
        args = parts[1:]
        response = ""

        try:
            if command == "!help":
                response = (
                    "Commands:\n"
                    "!createwallet\n"
                    "!balance\n"
                    "!address\n"
                    "!send <addr> <amt_btc_or_$usd>"
                )
            elif command == "!createwallet":
                response = self.btc_rpc.get_or_create_wallet(sender_id)
            elif command == "!balance":
                response = self.btc_rpc.get_balance(sender_id)
            elif command == "!address":
                response = self.btc_rpc.get_new_address(sender_id)
            elif command == "!privatekey":
                # For simplicity, we get a new address and then its key.
                # A real app might ask the user which address's key they want.
                address_response = self.btc_rpc.get_new_address(sender_id)
                if "Your address: " in address_response:
                    address = address_response.split("Your address: ")[1]
                    response = self.btc_rpc.get_private_key(sender_id, address)
                else:
                    response = address_response # Propagate error
            elif command == "!send":
                if len(args) == 2:
                    to_address, amount_str = args[0], args[1]
                    # Call the new send_payment method
                    response = self.btc_rpc.send_payment(sender_id, to_address, amount_str)
                else:
                    response = "Usage: !send <bitcoin_address> <amount_in_btc_or_$usd>"
            else:
                response = f"Unknown command: {command}"
        except Exception as e:
            response = f"An unexpected error occurred: {e}"

        if response:
            print(f"Sending response to {sender_id}: '{response}'")
            # Use sendText with wantAck=True for more reliable delivery
            self.interface.sendText(response, destinationId=sender_id, wantAck=True)
        
    def cleanup(self):
        """Closes the connection to the device."""
        if self.interface:
            print("Closing Meshtastic connection.")
            self.interface.close()

    def start(self):
        """Starts the bot's main loop."""
        self.connect()
        meshtastic.pub.subscribe("meshtastic.receive", self.on_receive)
        meshtastic.pub.subscribe("meshtastic.connection.established", self.on_connection)
        
        print("Bot is running. Listening for commands on the mesh...")
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
                break

if __name__ == "__main__":
    bot = MeshtasticBot()
    bot.start()
