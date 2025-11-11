"""
Order Execution System
Handles order placement, modification, and tracking on Binance Futures
"""

import asyncio
import logging
from typing import Dict, Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException
import time


class OrderExecutor:
    """
    Execute orders on Binance Futures with retry logic and safety checks
    """

    def __init__(self, config: Dict):
        """
        Initialize order executor

        Args:
            config: Binance API configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize Binance client
        api_key = config.get('api_key', '')
        api_secret = config.get('api_secret', '')
        testnet = config.get('testnet', True)

        if testnet:
            self.logger.info("Connecting to Binance TESTNET")
            self.client = Client(api_key, api_secret, testnet=True)
        else:
            self.logger.warning("Connecting to Binance LIVE - Real money trading!")
            self.client = Client(api_key, api_secret)

        # Order tracking
        self.active_orders = {}
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> Dict:
        """
        Place a market order with retry logic

        Args:
            symbol: Trading symbol (e.g., 'SOLUSDT')
            side: 'BUY' or 'SELL' or 'LONG' or 'SHORT'
            quantity: Order quantity

        Returns:
            Order result dictionary
        """
        # Normalize side
        if side == 'LONG':
            side = 'BUY'
        elif side == 'SHORT':
            side = 'SELL'

        self.logger.info(f"Placing {side} market order for {quantity} {symbol}")

        for attempt in range(self.max_retries):
            try:
                # Place market order
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=self._format_quantity(quantity, symbol)
                )

                self.logger.info(f"Order placed successfully: {order['orderId']}")

                # Store order
                self.active_orders[order['orderId']] = order

                # Get filled price
                filled_price = float(order.get('avgPrice', 0))
                if filled_price == 0:
                    # Fetch order details
                    order_status = self.client.futures_get_order(
                        symbol=symbol,
                        orderId=order['orderId']
                    )
                    filled_price = float(order_status.get('avgPrice', 0))

                return {
                    'order_id': order['orderId'],
                    'status': order['status'],
                    'side': side,
                    'quantity': float(order['executedQty']),
                    'average_price': filled_price,
                    'timestamp': order['updateTime']
                }

            except BinanceAPIException as e:
                self.logger.error(f"Binance API error (attempt {attempt + 1}): {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    # Final attempt failed
                    return {
                        'status': 'FAILED',
                        'error': str(e)
                    }

            except Exception as e:
                self.logger.error(f"Unexpected error placing order: {e}", exc_info=True)
                return {
                    'status': 'FAILED',
                    'error': str(e)
                }

        return {'status': 'FAILED', 'error': 'Max retries exceeded'}

    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> Dict:
        """
        Place a limit order

        Args:
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Limit price

        Returns:
            Order result dictionary
        """
        self.logger.info(f"Placing {side} limit order for {quantity} {symbol} @ ${price}")

        try:
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                timeInForce='GTC',
                quantity=self._format_quantity(quantity, symbol),
                price=self._format_price(price, symbol)
            )

            self.active_orders[order['orderId']] = order

            return {
                'order_id': order['orderId'],
                'status': order['status'],
                'side': side,
                'quantity': float(order['origQty']),
                'price': float(order['price']),
                'timestamp': order['updateTime']
            }

        except BinanceAPIException as e:
            self.logger.error(f"Error placing limit order: {e}")
            return {'status': 'FAILED', 'error': str(e)}

    async def cancel_order(self, symbol: str, order_id: int) -> bool:
        """
        Cancel an open order

        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        try:
            result = self.client.futures_cancel_order(
                symbol=symbol,
                orderId=order_id
            )

            self.logger.info(f"Order {order_id} cancelled successfully")

            if order_id in self.active_orders:
                del self.active_orders[order_id]

            return True

        except BinanceAPIException as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    def get_account_info(self) -> Dict:
        """
        Get account balance and position information

        Returns:
            Dictionary with account information
        """
        try:
            account = self.client.futures_account()

            total_balance = float(account['totalWalletBalance'])
            available_balance = float(account['availableBalance'])
            unrealized_pnl = float(account['totalUnrealizedProfit'])

            return {
                'total_balance': total_balance,
                'available_balance': available_balance,
                'unrealized_pnl': unrealized_pnl,
                'margin_balance': total_balance + unrealized_pnl
            }

        except Exception as e:
            self.logger.error(f"Error getting account info: {e}", exc_info=True)
            return {
                'total_balance': 0,
                'available_balance': 0,
                'unrealized_pnl': 0,
                'margin_balance': 0
            }

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get current position for a symbol

        Args:
            symbol: Trading symbol

        Returns:
            Position information or None
        """
        try:
            positions = self.client.futures_position_information(symbol=symbol)

            for position in positions:
                if position['symbol'] == symbol:
                    position_amt = float(position['positionAmt'])

                    if position_amt != 0:
                        return {
                            'symbol': symbol,
                            'size': abs(position_amt),
                            'direction': 1 if position_amt > 0 else -1,
                            'entry_price': float(position['entryPrice']),
                            'unrealized_pnl': float(position['unRealizedProfit']),
                            'leverage': int(position['leverage'])
                        }

            return None

        except Exception as e:
            self.logger.error(f"Error getting position: {e}", exc_info=True)
            return None

    async def fetch_open_interest_hist(self, symbol: str, period: str = '5m', limit: int = 1):
        """
        Fetch Open Interest history (placeholder)

        Args:
            symbol: Trading symbol
            period: Time period
            limit: Number of records

        Returns:
            DataFrame or dict with OI data
        """
        try:
            # This is a placeholder - implement actual OI fetching
            import pandas as pd
            # In real implementation, fetch from Binance futures_open_interest_hist
            return pd.DataFrame({'sum_open_interest': [1000000]})

        except Exception as e:
            self.logger.error(f"Error fetching OI: {e}")
            import pandas as pd
            return pd.DataFrame({'sum_open_interest': [0]})

    def set_leverage(self, symbol: str, leverage: int):
        """
        Set leverage for a symbol

        Args:
            symbol: Trading symbol
            leverage: Leverage multiplier (1-125)
        """
        try:
            result = self.client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )
            self.logger.info(f"Leverage set to {leverage}x for {symbol}")

        except Exception as e:
            self.logger.error(f"Error setting leverage: {e}", exc_info=True)

    def _format_quantity(self, quantity: float, symbol: str) -> str:
        """Format quantity according to symbol precision"""
        # Simplified - in production, fetch from exchange info
        return f"{quantity:.3f}"

    def _format_price(self, price: float, symbol: str) -> str:
        """Format price according to symbol precision"""
        # Simplified - in production, fetch from exchange info
        return f"{price:.2f}"
