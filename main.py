"""
Main entry point for AI Trading Bot
Initializes and runs the autonomous trading system
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
import yaml
import redis
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.trading_bot import AITradingBot


def setup_logging(log_level: str = "INFO", log_file: str = "./logs/trading_bot.log"):
    """
    Setup logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
    """
    # Create logs directory
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")

    return logger


def load_config(config_path: str = "./config/config.yaml") -> dict:
    """
    Load configuration from YAML file

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    # Load environment variables
    load_dotenv()

    # Load config file
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Replace environment variables in config
    def replace_env_vars(obj):
        """Recursively replace ${VAR} with environment variable values"""
        if isinstance(obj, dict):
            return {k: replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            var_name = obj[2:-1]
            return os.getenv(var_name, obj)
        else:
            return obj

    config = replace_env_vars(config)

    return config


def initialize_redis(config: dict):
    """
    Initialize Redis connection

    Args:
        config: Redis configuration

    Returns:
        Redis client
    """
    redis_config = config.get('redis', {})

    try:
        redis_client = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            decode_responses=redis_config.get('decode_responses', True)
        )

        # Test connection
        redis_client.ping()
        logging.info("Redis connection established")

        return redis_client

    except Exception as e:
        logging.error(f"Failed to connect to Redis: {e}")
        logging.warning("Creating in-memory Redis mock for testing")

        # Create simple in-memory mock
        class RedisMock:
            def __init__(self):
                self.data = {}

            def set(self, key, value):
                self.data[key] = value

            def get(self, key):
                return self.data.get(key)

            def expire(self, key, seconds):
                pass

            def ping(self):
                return True

        return RedisMock()


async def main():
    """Main async function"""
    # Load configuration
    config = load_config()

    # Setup logging
    logger = setup_logging(
        log_level=config['monitoring']['log_level'],
        log_file=config['monitoring']['log_file']
    )

    logger.info("=" * 80)
    logger.info("AI TRADING BOT - PHASE 5: LIVE DEPLOYMENT")
    logger.info("=" * 80)

    # Initialize Redis
    redis_client = initialize_redis(config)

    # Initialize trading bot
    bot = AITradingBot(config=config, redis_client=redis_client)

    # Start bot
    try:
        await bot.start()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        await bot.stop()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
