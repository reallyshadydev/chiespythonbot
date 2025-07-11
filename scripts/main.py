import logging
from meshtastic_bot import MeshtasticBot
from logger_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    try:
        bot = MeshtasticBot()
        bot.start()
    except Exception as e:
        logging.critical(f"Bot failed to start or crashed: {e}", exc_info=True)
