from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from . import config
from . import utils

class BitcoinRPC:
    def __init__(self):
        self.rpc_connection = None
        try:
            self.rpc_connection = AuthServiceProxy(
                f"http://{config.RPC_USER}:{config.RPC_PASSWORD}@{config.RPC_HOST}:{config.RPC_PORT}/"
            )
            self.rpc_connection.getblockchaininfo()
            print("Successfully connected to Bitcoin Core RPC.")
        except Exception as e:
            print(f"Error: Could not connect to Bitcoin Core RPC.")
            print(f"Please ensure your bitcoin.conf and .env are set up correctly and bitcoind is running.")
            print(f"Details: {e}")
            exit(1)

    def get_rpc_for_wallet(self, wallet_name):
        """Returns an RPC proxy instance for a specific wallet."""
        return AuthServiceProxy(
            f"http://{config.RPC_USER}:{config.RPC_PASSWORD}@{config.RPC_HOST}:{config.RPC_PORT}/wallet/{wallet_name}"
        )

    def wallet_exists(self, wallet_name):
        """Checks if a wallet is loaded."""
        return wallet_name in self.rpc_connection.listwallets()

    def get_or_create_wallet(self, user_id):
        """Creates a new wallet for a user if it doesn't exist."""
        wallet_name = utils.get_user_wallet_name(user_id)
        if self.wallet_exists(wallet_name):
            return f"Wallet '{wallet_name}' already exists."
        
        try:
            self.rpc_connection.createwallet(wallet_name)
            return f"Successfully created and loaded new wallet: '{wallet_name}'."
        except JSONRPCException as e:
            return f"Error creating wallet: {e.message}"

    def get_balance(self, user_id):
        """Gets the balance of a user's wallet in BTC and USD."""
        wallet_name = utils.get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return "Wallet not found. Use !createwallet first."
        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            balance_btc = wallet_rpc.getbalance()
            
            rate = utils.get_btc_usd_rate()
            if rate:
                balance_usd = balance_btc * rate
                return f"Balance: {balance_btc:.8f} BTC (~${balance_usd:,.2f} USD)"
            else:
                return f"Balance: {balance_btc:.8f} BTC (USD rate unavailable)"
        except JSONRPCException as e:
            return f"Error getting balance: {e.message}"

    def get_new_address(self, user_id):
        """Gets a new receiving address for the user."""
        wallet_name = utils.get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return "Wallet not found. Use !createwallet first."
        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            address = wallet_rpc.getnewaddress()
            return f"Your address: {address}"
        except JSONRPCException as e:
            return f"Error getting address: {e.message}"

    def send_payment(self, user_id, to_address, amount_str):
        """Processes a payment, handling USD conversion and node fees."""
        wallet_name = utils.get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return "Wallet not found. Use !createwallet first."

        rate = utils.get_btc_usd_rate()
        if not rate:
            return "Error: Cannot process transaction, exchange rate is unavailable."

        try:
            if amount_str.startswith('$'):
                amount_usd = float(amount_str[1:])
                send_amount_btc = amount_usd / rate
            else:
                send_amount_btc = float(amount_str)
                amount_usd = send_amount_btc * rate
        except ValueError:
            return "Error: Invalid amount specified."

        fee_btc = send_amount_btc * (config.NODE_OPERATOR_FEE_PERCENT / 100.0)
        total_btc = send_amount_btc + fee_btc
        total_usd = total_btc * rate
        fee_usd = fee_btc * rate

        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            balance_btc = wallet_rpc.getbalance()
            if balance_btc < total_btc:
                return f"Error: Insufficient funds. Need {total_btc:.8f} BTC, have {balance_btc:.8f} BTC."

            outputs = {
                to_address: f"{send_amount_btc:.8f}",
                config.NODE_OPERATOR_ADDRESS: f"{fee_btc:.8f}"
            }
            txid = wallet_rpc.sendmany("", outputs)

            response = (
                f"Success! Sent ${amount_usd:,.2f} ({send_amount_btc:.8f} BTC).\n"
                f"Fee ({config.NODE_OPERATOR_FEE_PERCENT}%): ${fee_usd:,.2f} ({fee_btc:.8f} BTC).\n"
                f"Total: ${total_usd:,.2f} ({total_btc:.8f} BTC).\n"
                f"TXID: {txid}"
            )
            return response
        except JSONRPCException as e:
            return f"Error sending transaction: {e.message}"
        except Exception as e:
            return f"An unexpected error occurred during send: {e}"
