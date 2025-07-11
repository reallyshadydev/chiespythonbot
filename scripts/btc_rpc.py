import logging
from decimal import Decimal, getcontext
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from . import config
from . import utils

# Set precision for Decimal calculations
getcontext().prec = 10

class BitcoinRPC:
    def __init__(self):
        self.rpc_connection = None
        try:
            self.rpc_connection = AuthServiceProxy(
                f"http://{config.RPC_USER}:{config.RPC_PASSWORD}@{config.RPC_HOST}:{config.RPC_PORT}/"
            )
            self.rpc_connection.getblockchaininfo()
            logging.info("Successfully connected to Bitcoin Core RPC.")
        except Exception as e:
            logging.critical(f"Could not connect to Bitcoin Core RPC: {e}")
            exit(1)

    def get_rpc_for_wallet(self, wallet_name):
        return AuthServiceProxy(
            f"http://{config.RPC_USER}:{config.RPC_PASSWORD}@{config.RPC_HOST}:{config.RPC_PORT}/wallet/{wallet_name}"
        )

    def wallet_exists(self, wallet_name):
        return wallet_name in self.rpc_connection.listwallets()

    def get_or_create_wallet(self, user_id):
        wallet_name = utils.get_user_wallet_name(user_id)
        if self.wallet_exists(wallet_name):
            return f"Wallet '{wallet_name}' already exists."
        try:
            self.rpc_connection.createwallet(wallet_name)
            logging.info(f"Created new wallet '{wallet_name}' for user {user_id}")
            return f"Successfully created and loaded new wallet: '{wallet_name}'."
        except JSONRPCException as e:
            logging.error(f"Error creating wallet for {user_id}: {e.message}")
            return f"Error creating wallet: {e.message}"

    def get_balance(self, user_id):
        wallet_name = utils.get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return "Wallet not found. Use !createwallet first."
        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            balance_btc = wallet_rpc.getbalance()
            rate = utils.get_btc_usd_rate()
            if rate:
                balance_usd = balance_btc * Decimal(rate)
                return f"Balance: {balance_btc:.8f} BTC (~${balance_usd:,.2f} USD)"
            else:
                return f"Balance: {balance_btc:.8f} BTC (USD rate unavailable)"
        except JSONRPCException as e:
            logging.error(f"Error getting balance for {user_id}: {e.message}")
            return f"Error getting balance: {e.message}"

    def get_new_address(self, user_id):
        wallet_name = utils.get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return "Wallet not found. Use !createwallet first."
        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            address = wallet_rpc.getnewaddress()
            return f"Your address: {address}"
        except JSONRPCException as e:
            logging.error(f"Error getting address for {user_id}: {e.message}")
            return f"Error getting address: {e.message}"

    def prepare_payment_for_confirmation(self, user_id, to_address, amount_str):
        wallet_name = utils.get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return {"error": "Wallet not found. Use !createwallet first."}

        rate = utils.get_btc_usd_rate()
        if not rate:
            return {"error": "Cannot process transaction, exchange rate is unavailable."}

        try:
            amount_str = amount_str.replace(',', '') # Sanitize amount
            if amount_str.startswith('$'):
                amount_usd = Decimal(amount_str[1:])
                send_amount_btc = amount_usd / Decimal(rate)
            else:
                send_amount_btc = Decimal(amount_str)
        except ValueError:
            return {"error": "Invalid amount specified."}

        operator_fee_btc = send_amount_btc * (Decimal(config.NODE_OPERATOR_FEE_PERCENT) / Decimal(100))

        # Estimate miner fee
        try:
            # A typical 1-input, 2-output P2WPKH tx is ~141 vB
            TX_VBYTES = 141 
            fee_rate_btc_per_kvb = self.rpc_connection.estimatesmartfee(6)["feerate"]
            miner_fee_btc = (Decimal(fee_rate_btc_per_kvb) / Decimal(1000)) * Decimal(TX_VBYTES)
        except (JSONRPCException, KeyError) as e:
            logging.warning(f"Could not estimate miner fee, using fallback. Error: {e}")
            miner_fee_btc = Decimal("0.00001000") # Fallback fee

        total_btc = send_amount_btc + operator_fee_btc + miner_fee_btc
        
        wallet_rpc = self.get_rpc_for_wallet(wallet_name)
        balance_btc = wallet_rpc.getbalance()
        if balance_btc < total_btc:
            return {"error": f"Insufficient funds. Need ~{total_btc:.8f} BTC, have {balance_btc:.8f} BTC."}

        return {
            "user_id": user_id,
            "wallet_name": wallet_name,
            "outputs": {
                to_address: f"{send_amount_btc:.8f}",
                config.NODE_OPERATOR_ADDRESS: f"{operator_fee_btc:.8f}"
            },
            "miner_fee_btc": f"{miner_fee_btc:.8f}",
            "total_btc": f"{total_btc:.8f}"
        }

    def execute_payment(self, payment_details):
        wallet_name = payment_details["wallet_name"]
        outputs = payment_details["outputs"]
        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            txid = wallet_rpc.sendmany("", outputs)
            logging.info(f"Successfully sent transaction for user {payment_details['user_id']}. TXID: {txid}")
            return {"success": True, "txid": txid}
        except JSONRPCException as e:
            logging.error(f"Error executing payment for {payment_details['user_id']}: {e.message}")
            return {"success": False, "error": f"Error sending: {e.message}"}

    def get_transaction_history(self, user_id, count=3):
        wallet_name = utils.get_user_wallet_name(user_id)
        if not self.wallet_exists(wallet_name):
            return "Wallet not found. Use !createwallet first."
        try:
            wallet_rpc = self.get_rpc_for_wallet(wallet_name)
            transactions = wallet_rpc.listtransactions("*", count, 0, True)
            
            if not transactions:
                return "No transaction history found."

            history_lines = ["Last 3 transactions:"]
            for tx in reversed(transactions):
                cat = tx['category']
                amt = Decimal(tx['amount'])
                addr = tx.get('address', 'N/A')
                line = f"{cat.title()}: {abs(amt):.8f} BTC"
                if cat == 'send':
                    line += f" to {addr[:6]}..."
                elif cat == 'receive':
                    line += f" to {addr[:6]}..."
                history_lines.append(line)
            
            return "\n".join(history_lines)
        except JSONRPCException as e:
            logging.error(f"Error getting history for {user_id}: {e.message}")
            return "Error fetching history."
