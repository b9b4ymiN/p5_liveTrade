"""
Real-time WebSocket data streamer for Binance Futures
Streams klines, mark price, and other real-time data to Redis
"""

import json
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
import websockets
from binance.client import Client
from binance.streams import ThreadedWebsocketManager


class BinanceWebSocketStreamer:
    """
    WebSocket streamer for real-time Binance Futures data
    """

    def __init__(self, symbols: List[str], redis_client, api_key: str = None, api_secret: str = None):
        """
        Initialize WebSocket streamer

        Args:
            symbols: List of trading symbols (e.g., ['SOLUSDT'])
            redis_client: Redis client for caching
            api_key: Binance API key
            api_secret: Binance API secret
        """
        self.symbols = symbols
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)

        # Initialize Binance client
        self.client = Client(api_key, api_secret) if api_key else None
        self.ws_manager = None
        self.is_running = False

    def start(self):
        """Start WebSocket streams"""
        self.logger.info("Starting WebSocket streams...")
        self.is_running = True

        try:
            # Initialize WebSocket Manager
            self.ws_manager = ThreadedWebsocketManager(
                api_key=self.client.API_KEY if self.client else None,
                api_secret=self.client.API_SECRET if self.client else None
            )
            self.ws_manager.start()

            # Subscribe to streams for each symbol
            for symbol in self.symbols:
                self._subscribe_streams(symbol)

            self.logger.info(f"WebSocket streams started for {self.symbols}")

        except Exception as e:
            self.logger.error(f"Error starting WebSocket streams: {e}", exc_info=True)
            self.is_running = False

    def _subscribe_streams(self, symbol: str):
        """
        Subscribe to all required streams for a symbol

        Args:
            symbol: Trading symbol
        """
        symbol_lower = symbol.lower()

        # 1. Kline/Candlestick Stream (5m)
        self.ws_manager.start_kline_futures_socket(
            callback=self._handle_kline_message,
            symbol=symbol,
            interval='5m'
        )
        self.logger.info(f"Subscribed to {symbol} 5m kline stream")

        # 2. Mark Price Stream (for funding rate)
        self.ws_manager.start_mark_price_socket(
            callback=self._handle_mark_price_message,
            symbol=symbol
        )
        self.logger.info(f"Subscribed to {symbol} mark price stream")

        # 3. Aggregated Trade Stream
        self.ws_manager.start_aggtrade_futures_socket(
            callback=self._handle_trade_message,
            symbol=symbol
        )
        self.logger.info(f"Subscribed to {symbol} trade stream")

    def _handle_kline_message(self, msg: Dict):
        """
        Handle kline/candlestick messages

        Args:
            msg: WebSocket message
        """
        try:
            if msg['e'] == 'kline':
                kline = msg['k']
                symbol = msg['s']

                # Extract kline data
                data = {
                    'timestamp': datetime.fromtimestamp(kline['t'] / 1000).isoformat(),
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'close': float(kline['c']),
                    'volume': float(kline['v']),
                    'is_closed': kline['x']
                }

                # Store in Redis
                key = f"latest_kline:{symbol}"
                self.redis.set(key, json.dumps(data))
                self.redis.expire(key, 3600)  # Expire in 1 hour

                if kline['x']:  # If candle is closed
                    self.logger.debug(f"{symbol} - New 5m candle closed: {data['close']}")

        except Exception as e:
            self.logger.error(f"Error handling kline message: {e}", exc_info=True)

    def _handle_mark_price_message(self, msg: Dict):
        """
        Handle mark price messages (includes funding rate)

        Args:
            msg: WebSocket message
        """
        try:
            if msg['e'] == 'markPriceUpdate':
                symbol = msg['s']

                data = {
                    'timestamp': datetime.fromtimestamp(msg['E'] / 1000).isoformat(),
                    'mark_price': float(msg['p']),
                    'index_price': float(msg['i']),
                    'funding_rate': float(msg['r']),
                    'next_funding_time': datetime.fromtimestamp(msg['T'] / 1000).isoformat()
                }

                # Store in Redis
                key = f"latest_mark:{symbol}"
                self.redis.set(key, json.dumps(data))
                self.redis.expire(key, 3600)

                self.logger.debug(f"{symbol} - Funding rate: {data['funding_rate']:.4%}")

        except Exception as e:
            self.logger.error(f"Error handling mark price message: {e}", exc_info=True)

    def _handle_trade_message(self, msg: Dict):
        """
        Handle aggregated trade messages

        Args:
            msg: WebSocket message
        """
        try:
            if msg['e'] == 'aggTrade':
                symbol = msg['s']

                data = {
                    'timestamp': datetime.fromtimestamp(msg['T'] / 1000).isoformat(),
                    'price': float(msg['p']),
                    'quantity': float(msg['q']),
                    'is_buyer_maker': msg['m']
                }

                # Store latest trade in Redis
                key = f"latest_trade:{symbol}"
                self.redis.set(key, json.dumps(data))
                self.redis.expire(key, 60)  # Expire in 1 minute

        except Exception as e:
            self.logger.error(f"Error handling trade message: {e}", exc_info=True)

    def get_latest_kline(self, symbol: str) -> Optional[Dict]:
        """
        Get latest kline data from Redis

        Args:
            symbol: Trading symbol

        Returns:
            Latest kline data or None
        """
        try:
            key = f"latest_kline:{symbol}"
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            self.logger.error(f"Error getting latest kline: {e}")
            return None

    def get_latest_funding(self, symbol: str) -> Optional[Dict]:
        """
        Get latest funding rate from Redis

        Args:
            symbol: Trading symbol

        Returns:
            Latest funding data or None
        """
        try:
            key = f"latest_mark:{symbol}"
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            self.logger.error(f"Error getting latest funding: {e}")
            return None

    def stop(self):
        """Stop WebSocket streams"""
        self.logger.info("Stopping WebSocket streams...")
        self.is_running = False

        if self.ws_manager:
            self.ws_manager.stop()
            self.logger.info("WebSocket streams stopped")
