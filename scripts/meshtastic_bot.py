import time
import atexit
import logging
import secrets
from datetime import datetime, timedelta
import meshtastic
import meshtastic.serial_interface
from .btc_rpc import BitcoinRPC

# Time in seconds before a pending transaction expires
PENDING_TX_EXPIRATION = 120

class MeshtasticBot:
    def __init__(self):
        self.btc_rpc = BitcoinRPC()
        self.interface = None
        self.pending_transactions = {}
        logging.info("Meshtastic Bitcoin Bot initializing...")

    def connect(self):
        try:
            self.interface = meshtastic.serial_interface.SerialInterface()
            atexit.register(self.cleanup)
            logging.info("Connected to Meshtastic device.")
        except Exception as e:
            logging.critical(f"Could not connect to Meshtastic device: {e}")
            exit(1)

    def cleanup_expired_txs(self):
        now = datetime.now()
        expired_ids = [
            tx_id for tx_id, tx in self.pending_transactions.items()
            if now > tx['timestamp'] + timedelta(seconds=PENDING_TX_EXPIRATION)
        ]
        for tx_id in expired_ids:
            del self.pending_transactions[tx_id]
            logging.info(f"Expired pending transaction {tx_id}")

    def on_receive(self, packet, interface):
        if packet.get('decoded') and packet['decoded'].get('portnum') == 'TEXT_MESSAGE_APP':
            msg = packet['decoded']['text']
            sender_id = packet['fromId']
            
            logging.info(f"Received message: '{msg}' from user: {sender_id}")

            if msg.startswith('!'):
                self.handle_command(msg, sender_id)

    def handle_command(self, msg, sender_id):
        self.cleanup_expired_txs()
        parts = msg.strip().split()
        command = parts[0].lower()
        args = parts[1:]
        response = ""

        try:
            if command == "!help":
                response = (
                    "Commands:\n!createwallet\n!balance\n!address\n"
                    "!send <addr> <amt>\n!confirm <id>\n!history"
                )
            elif command == "!createwallet":
                response = self.btc_rpc.get_or_create_wallet(sender_id)
            elif command == "!balance":
                response = self.btc_rpc.get_balance(sender_id)
            elif command == "!address":
                response = self.btc_rpc.get_new_address(sender_id)
            elif command == "!history":
                response = self.btc_rpc.get_transaction_history(sender_id)
            elif command == "!send":
                if len(args) == 2:
                    response = self.handle_send_command(sender_id, args)
                else:
                    response = "Usage: !send <bitcoin_address> <amount_in_btc_or_$usd>"
            elif command == "!confirm":
                if len(args) == 1:
                    response = self.handle_confirm_command(sender_id, args[0])
                else:
                    response = "Usage: !confirm <confirmation_id>"
            else:
                response = f"Unknown command: {command}"
        except Exception as e:
            logging.error(f"An unexpected error occurred while handling command '{msg}': {e}", exc_info=True)
            response = "An unexpected error occurred."

        if response:
            logging.info(f"Sending response to {sender_id}: '{response}'")
            self.interface.sendText(response, destinationId=sender_id, wantAck=True)

    def handle_send_command(self, sender_id, args):
        to_address, amount_str = args[0], args[1]
        details = self.btc_rpc.prepare_payment_for_confirmation(sender_id, to_address, amount_str)

        if "error" in details:
            return details["error"]

        conf_id = secrets.token_hex(3) # 6-char hex ID
        self.pending_transactions[conf_id] = {
            "user_id": sender_id,
            "details": details,
            "timestamp": datetime.now()
        }
        
        return (
            f"CONFIRM SEND:\n"
            f"Total: {details['total_btc']} BTC\n"
            f"(incl. miner fee ~{details['miner_fee_btc']} BTC)\n"
            f"Reply with: !confirm {conf_id}"
        )

    def handle_confirm_command(self, sender_id, conf_id):
        pending_tx = self.pending_transactions.get(conf_id)

        if not pending_tx:
            return "Error: Confirmation ID not found or expired."
        
        if pending_tx["user_id"] != sender_id:
            logging.warning(f"User {sender_id} tried to confirm tx {conf_id} from user {pending_tx['user_id']}")
            return "Error: This is not your transaction to confirm."

        result = self.btc_rpc.execute_payment(pending_tx["details"])
        del self.pending_transactions[conf_id]

        if result["success"]:
            return f"Success! Transaction sent. TXID: {result['txid'][:12]}..."
        else:
            return result["error"]
        
    def start(self):
        self.connect()
        meshtastic.pub.subscribe("meshtastic.receive", self.on_receive)
        
        logging.info("Bot is running. Listening for commands on the mesh...")
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logging.info("Shutting down...")
                break
    
    def cleanup(self):
        if self.interface:
            logging.info("Closing Meshtastic connection.")
            self.interface.close()
