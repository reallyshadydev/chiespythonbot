# Meshtastic Bitcoin Bot

[![Built with v0](https://img.shields.io/badge/Built%20with-v0.dev-black?style=for-the-badge)](https://v0.dev/chat/projects/DCL7ACIfKYZ)
[![Python Version](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)](https://www.python.org/)

## 1. Overview

The Meshtastic Bitcoin Bot is a Python-based application that bridges the gap between a low-power, long-range [Meshtastic](https://meshtastic.org/) mesh network and the Bitcoin network. It allows users on the mesh to interact with a Bitcoin Core node using simple text commands sent from their Meshtastic devices.

This enhanced version includes critical safety features like a two-step transaction confirmation process, robust logging, transaction history, and deployment support via Docker and systemd.

---

## 2. Features

- **User-Specific Wallets**: Automatically creates and manages a separate Bitcoin wallet for each Meshtastic user ID.
- **Safe Transactions**: A **two-step confirmation process** prevents accidental sends.
- **Fee Transparency**: Estimates and displays the **Bitcoin miner fee** before sending.
- **Node Operator Fees**: Automatically deducts a configurable percentage from each transaction as a fee for the node operator.
- **Balance Inquiry**: Check wallet balance in both BTC and its real-time USD equivalent.
- **Flexible Sending**: Send Bitcoin by specifying an amount in either BTC or USD (e.g., `0.001` or `$5.00`).
- **Transaction History**: View your last few transactions with the `!history` command.
- **Robust & Deployable**: Features file-based logging, is fully modular, and includes `Dockerfile` and `systemd` examples for production deployment.

---

## 3. Installation & Setup

### Step 1: Install Python Dependencies
Clone the project, navigate to the `scripts` directory, and install the required libraries.

\`\`\`bash
cd scripts
pip install -r requirements.txt
\`\`\`

### Step 2: Configure Bitcoin Core
Ensure your Bitcoin Core node is configured to accept RPC commands. Add the following to your `bitcoin.conf` file and restart the node:

\`\`\`ini
server=1
rpcuser=your_rpc_username
rpcpassword=your_super_secret_password
testnet=1 # Recommended for testing
\`\`\`

### Step 3: Configure the Bot
Copy `.env.example` to `.env` and fill in your details.

\`\`\`bash
cp .env.example .env
\`\`\`
Edit the `.env` file with your RPC credentials and your personal Bitcoin address for receiving operator fees.

---

## 4. Device Configuration (One-Time Setup)

Before running the bot, configure your Meshtastic device (e.g., Heltec V3) with your channel settings.

1.  **Create `config.json`**: Copy `config.json.example` to `config.json` and edit it with your channel name, PSK, region, etc.
2.  **Apply Configuration**: Connect your device via USB and run:
    \`\`\`bash
    meshtastic --set-json config.json
    \`\`\`

---

## 5. Running the Bot

### Method 1: Direct Execution (for testing)
With your device connected and Bitcoin node running, start the bot:

\`\`\`bash
python scripts/main.py
\`\`\`
Logs will be printed to the console and saved to `bot.log`.

### Method 2: Using Docker (Recommended for deployment)
Build and run the bot in a container. Pass your credentials securely as environment variables.

\`\`\`bash
# Build the Docker image
docker build -t meshtastic-btc-bot .

# Run the container
docker run -d --name btc-bot --restart=always \
  --device=/dev/ttyUSB0 \
  -e RPC_USER="your_rpc_user" \
  -e RPC_PASSWORD="your_rpc_password" \
  -e NODE_OPERATOR_ADDRESS="your_btc_address" \
  meshtastic-btc-bot
\`\`\`

### Method 3: Using Systemd (for Linux servers)
Use the provided `meshtastic-btc-bot.service.example` as a template to run the bot as a background service.

1.  Edit the file with your user and project paths.
2.  Copy it to `/etc/systemd/system/meshtastic-btc-bot.service`.
3.  Run the following commands:
    \`\`\`bash
    sudo systemctl daemon-reload
    sudo systemctl enable meshtastic-btc-bot.service
    sudo systemctl start meshtastic-btc-bot.service
    \`\`\`

---

## 6. Usage (Commands)

### Sending Bitcoin (Two-Step Process)

**Step 1: Initiate the transaction**
Send the `!send` command. The bot will reply with a summary of the total cost (including fees) and a unique ID.

`!send tb1q... $5.00`

**Step 2: Confirm the transaction**
To approve the transaction, use the `!confirm` command with the ID you received.

`!confirm a3f8b1`

### All Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `!help` | Shows the list of available commands. | `!help` |
| `!createwallet` | Creates a new Bitcoin wallet tied to your Meshtastic ID. | `!createwallet` |
| `!balance` | Checks your current wallet balance in BTC and USD. | `!balance` |
| `!address` | Generates a new receiving address for your wallet. | `!address` |
| `!history` | Shows your last 3 transactions. | `!history` |
| `!send` | **Step 1:** Prepares a transaction for confirmation. | `!send <addr> 0.001` |
| `!confirm` | **Step 2:** Executes a prepared transaction. | `!confirm <id>` |

---

## 7. Security Warning

- **USE ON TESTNET.** This software handles private keys and money. It is strongly recommended to only use it on the Bitcoin **Testnet** until you are confident in its operation.
- **Node Security**: Ensure your Bitcoin Core RPC port is not exposed to the public internet.
- The author assumes no liability for any loss of funds. **Use at your own risk.**
