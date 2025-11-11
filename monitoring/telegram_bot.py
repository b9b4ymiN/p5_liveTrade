"""
Telegram Notification Bot
Sends real-time alerts and notifications
"""

import logging
from typing import Dict
import asyncio


class TelegramNotifier:
    """
    Send notifications via Telegram
    """

    def __init__(self, config: Dict):
        """
        Initialize Telegram notifier

        Args:
            config: Telegram configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enabled = config.get('enabled', False)

        if self.enabled:
            try:
                from telegram import Bot
                self.bot = Bot(token=config['token'])
                self.chat_id = config['chat_id']
                self.logger.info("Telegram notifier initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Telegram bot: {e}")
                self.enabled = False
                self.bot = None
        else:
            self.bot = None
            self.logger.info("Telegram notifications disabled")

    async def send_message(self, message: str):
        """
        Send message to Telegram

        Args:
            message: Message text
        """
        if not self.enabled or not self.bot:
            self.logger.debug(f"Telegram message (not sent): {message}")
            return

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            self.logger.debug("Telegram message sent successfully")

        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")

    async def send_trade_alert(self, message: str):
        """
        Send trade alert

        Args:
            message: Trade alert message
        """
        await self.send_message(f"*TRADE ALERT*\n\n{message}")

    async def send_error(self, error_message: str):
        """
        Send error notification

        Args:
            error_message: Error description
        """
        await self.send_message(f"*ERROR*\n\n{error_message}")

    async def send_daily_summary(self, summary: Dict):
        """
        Send daily performance summary

        Args:
            summary: Summary statistics dictionary
        """
        message = (
            f"*Daily Summary*\n\n"
            f"PnL: ${summary.get('pnl', 0):.2f} ({summary.get('pnl_pct', 0):.2f}%)\n"
            f"Trades: {summary.get('total_trades', 0)}\n"
            f"Win Rate: {summary.get('win_rate', 0):.1f}%\n"
            f"Sharpe: {summary.get('sharpe', 0):.2f}\n"
            f"Max DD: {summary.get('max_dd', 0):.2f}%"
        )
        await self.send_message(message)
