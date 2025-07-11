import time
import atexit
import meshtastic
import meshtastic.serial_interface
from .btc_rpc import BitcoinRPC

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
            elif command == "!send":
                if len(args) == 2:
                    to_address, amount_str = args[0], args[1]
                    response = self.btc_rpc.send_payment(sender_id, to_address, amount_str)
                else:
                    response = "Usage: !send <bitcoin_address> <amount_in_btc_or_$usd>"
            else:
                response = f"Unknown command: {command}"
        except Exception as e:
            response = f"An unexpected error occurred: {e}"

        if response:
            print(f"Sending response to {sender_id}: '{response}'")
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
