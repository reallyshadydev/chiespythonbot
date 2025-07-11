# Meshtastic Bitcoin Bot

[![Built with v0](https://img.shields.io/badge/Built%20with-v0.dev-black?style=for-the-badge)](https://v0.dev/chat/projects/DCL7ACIfKYZ)
[![Python Version](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)](https://www.python.org/)

## 1. Overview

The Meshtastic Bitcoin Bot is a Python-based application that bridges the gap between a low-power, long-range [Meshtastic](https://meshtastic.org/) mesh network and the Bitcoin network. It allows users on the mesh to interact with a Bitcoin Core node using simple text commands sent from their Meshtastic devices.

Each user is identified by their unique Meshtastic node ID, for which the bot creates and manages a dedicated wallet on the Bitcoin node. This project is ideal for enabling Bitcoin transactions in off-grid or communication-restricted environments.

---

## 2. Features

- **User-Specific Wallets**: Automatically creates and manages a separate Bitcoin wallet for each Meshtastic user ID.
- **Balance Inquiry**: Check wallet balance in both BTC and its real-time USD equivalent.
- **Flexible Transactions**: Send Bitcoin by specifying an amount in either BTC or USD (e.g., `0.001` or `$5.00`).
- **Node Operator Fees**: Automatically deducts a configurable percentage from each transaction as a fee for the node operator.
- **Secure & Modular**: Uses a `.env` file to manage sensitive credentials and is structured into logical Python modules for maintainability.
- **Simple Commands**: Interact with the bot using intuitive commands like `!balance` and `!send`.

---

## 3. Architecture

The bot is designed with a modular structure to separate concerns and improve readability:

- **`main.py`**: The main entry point that initializes and starts the bot.
- **`meshtastic_bot.py`**: Handles all communication with the Meshtastic network, listening for commands and sending back responses.
- **`btc_rpc.py`**: Manages all interactions with the Bitcoin Core node via RPC, including wallet creation, balance checks, and transactions.
- **`config.py`**: Loads all configuration settings from the `.env` file.
- **`utils.py`**: Contains helper functions, such as the BTC-to-USD exchange rate fetcher.
- **`.env`**: Stores all your private keys, API credentials, and configuration variables.

---

## 4. Prerequisites

### Hardware
- A [Meshtastic-compatible device](https://meshtastic.org/docs/hardware) (e.g., T-Beam, Heltec) connected to the machine running the bot.
- At least one other Meshtastic device to send commands from.

### Software
- **Python 3.8+**
- A running **Bitcoin Core node** (or a compatible fork like Bitcoin-Qt).
  - The node must be fully synced.
  - The RPC server must be enabled.
  - **IMPORTANT**: It is **highly recommended** to run the node on **Testnet** for development and testing to avoid risking real funds.

---

## 5. Installation & Setup

### Step 1: Install Python Dependencies
Clone or download the project, navigate to the `scripts` directory, and install the required libraries using the `requirements.txt` file.

\`\`\`bash
cd scripts
pip install -r requirements.txt
\`\`\`

### Step 2: Configure Bitcoin Core
Ensure your Bitcoin Core node is configured to accept RPC commands. Add the following lines to your `bitcoin.conf` file:

\`\`\`ini
# Enable the RPC server
server=1

# Set your RPC username and password
rpcuser=your_rpc_username
rpcpassword=your_super_secret_password

# Recommended: Run on Testnet
testnet=1 
\`\`\`
Restart your Bitcoin Core node for the changes to take effect.

### Step 3: Configure the Bot
In the project's root directory, you'll find a file named `.env.example`. Create a copy of this file and name it `.env`.

\`\`\`bash
# In the root directory of the project
cp .env.example .env
\`\`\`

Now, open the `.env` file and fill in your details:

\`\`\`ini
# .env file

# Bitcoin Core RPC Configuration
RPC_HOST=127.0.0.1
RPC_PORT=18332 # Use 8332 for mainnet, 18332 for testnet
RPC_USER=your_rpc_username      # Must match bitcoin.conf
RPC_PASSWORD=your_super_secret_password # Must match bitcoin.conf

# Node Operator Configuration
# This is the address that will receive the transaction fees.
# IMPORTANT: Replace with your actual Bitcoin address.
NODE_OPERATOR_ADDRESS=tb1qxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NODE_OPERATOR_FEE_PERCENT=0.5 # Fee percentage (e.g., 0.5 for 0.5%)
\`\`\`

---

## 6. Device Configuration (One-Time Setup)

Before running the bot, you must configure your Meshtastic device (e.g., your Heltec V3) with the correct channel, LoRa, and other settings. The easiest way to do this is with a JSON configuration file.

### Step 1: Create Your Configuration File
A `config.json.example` file is included in this project. Copy it to a new file named `config.json`.

\`\`\`bash
cp config.json.example config.json
\`\`\`

### Step 2: Edit Your `config.json`
Open `config.json` and customize the settings for your needs. At a minimum, you should review:
- **`channel.name`**: The name of your mesh channel.
- **`channel.psk`**: The pre-shared key for your channel. Use `meshtastic --gen-psk` to create a new one. `AQ==` is the default "public" key.
- **`wifi.ssid`** and **`wifi.password`**: Your WiFi credentials if you want to enable WiFi.
- **`position`**: Your fixed latitude, longitude, and altitude if the device is stationary.
- **`lora.region`**: Your geographical region (e.g., `US`, `EU_868`).

### Step 3: Apply the Configuration
Connect your Meshtastic device to your computer via USB and run the following command from the project's root directory:

\`\`\`bash
meshtastic --set-json config.json
\`\`\`

This command writes the settings from the JSON file to your device's memory. You only need to do this once, or whenever you want to change the device's core settings. After this, the bot will connect to the pre-configured device.

---

## 7. Running the Bot

With your Meshtastic device connected and your Bitcoin node running, start the bot by executing the `main.py` script:

\`\`\`bash
python scripts/main.py
\`\`\`

If successful, you will see confirmation messages that the bot has connected to both your Meshtastic device and the Bitcoin Core RPC server.

---

## 8. Usage (Commands)

From any other device on your Meshtastic network, send the following commands as text messages. The bot will process them and send a direct message back to your device with the result.

| Command | Description | Example |
| :--- | :--- | :--- |
| `!help` | Shows the list of available commands. | `!help` |
| `!createwallet` | Creates a new Bitcoin wallet tied to your Meshtastic ID. | `!createwallet` |
| `!balance` | Checks your current wallet balance in BTC and USD. | `!balance` |
| `!address` | Generates a new receiving address for your wallet. | `!address` |
| `!send` | Sends Bitcoin to a specified address. Amount can be in BTC or USD. | `!send <address> 0.001` <br> `!send <address> $5.25` |

---

## 9. Security Warning

- **DO NOT USE ON MAINNET WITHOUT EXTENSIVE TESTING.** This software handles private keys and real money. It is strongly recommended to only use it on the Bitcoin **Testnet**.
- **Private Keys**: The `!privatekey` command was removed from the help menu for security. While the underlying functionality might exist in the RPC, exposing private keys over any network is extremely risky.
- **Node Security**: Ensure your Bitcoin Core RPC port is not exposed to the public internet.
- The author assumes no liability for any loss of funds. **Use at your own risk.**
