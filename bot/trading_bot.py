"""
AI Trading Bot
Main autonomous trading system integrating all components
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
import numpy as np
import json

from data_collector.websocket_streamer import BinanceWebSocketStreamer
from features.feature_engineer import FeatureEngineer
from models.ensemble import EnsembleModel
from rl.rl_agent import RLAgent
from execution.order_executor import OrderExecutor
from risk.risk_manager import RiskManager
from monitoring.telegram_bot import TelegramNotifier
from database.trade_logger import TradeLogger


class AITradingBot:
    """
    Main autonomous trading bot integrating all components
    """

    def __init__(self, config: Dict, redis_client):
        """
        Initialize AI Trading Bot

        Args:
            config: Configuration dictionary
            redis_client: Redis client instance
        """
        self.config = config
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)

        # State
        self.is_running = False
        self.current_position = None
        self.daily_pnl = 0
        self.trades_today = 0
        self.latest_data = {}

        # Initialize components
        self.logger.info("Initializing AI Trading Bot components...")

        self.feature_engineer = FeatureEngineer()
        self.ml_model = self._load_ml_models()
        self.rl_agent = self._load_rl_agent()
        self.order_executor = OrderExecutor(config['binance'])
        self.risk_manager = RiskManager(config['risk'])
        self.notifier = TelegramNotifier(config['telegram'])
        self.trade_logger = TradeLogger(config['database'])

        # WebSocket streamer (will be started later)
        self.websocket_streamer = None

        self.logger.info("AI Trading Bot initialized successfully")

    def _load_ml_models(self):
        """Load trained ML models"""
        self.logger.info("Loading ML models...")
        try:
            ensemble = EnsembleModel.load(self.config['models']['ensemble_path'])
            return ensemble
        except Exception as e:
            self.logger.error(f"Error loading ML models: {e}", exc_info=True)
            return EnsembleModel()  # Return dummy model

    def _load_rl_agent(self):
        """Load trained RL agent"""
        self.logger.info("Loading RL agent...")
        try:
            agent = RLAgent.load(self.config['models']['rl_agent_path'])
            return agent
        except Exception as e:
            self.logger.error(f"Error loading RL agent: {e}", exc_info=True)
            return RLAgent()  # Return dummy agent

    async def start(self):
        """Start the trading bot"""
        self.logger.info("=" * 60)
        self.logger.info("STARTING AI TRADING BOT")
        self.logger.info("=" * 60)

        self.is_running = True

        # Set leverage
        try:
            self.order_executor.set_leverage(
                symbol=self.config['symbol'],
                leverage=self.config['leverage']
            )
        except Exception as e:
            self.logger.error(f"Error setting leverage: {e}")

        # Start WebSocket data feed
        self.logger.info("Starting WebSocket data feed...")
        self.websocket_streamer = BinanceWebSocketStreamer(
            symbols=[self.config['symbol']],
            redis_client=self.redis,
            api_key=self.config['binance'].get('api_key'),
            api_secret=self.config['binance'].get('api_secret')
        )
        self.websocket_streamer.start()

        # Send startup notification
        await self.notifier.send_message(
            f"AI Trading Bot Started!\n"
            f"Symbol: {self.config['symbol']}\n"
            f"Leverage: {self.config['leverage']}x\n"
            f"Paper Trading: {self.config['safety']['paper_trading_mode']}"
        )

        # Main trading loop
        await self.run_trading_loop()

    async def run_trading_loop(self):
        """
        Main trading loop - runs continuously
        """
        self.logger.info("Starting main trading loop...")

        while self.is_running:
            try:
                # 1. Get latest market data
                market_data = await self._get_latest_market_data()

                if market_data is None:
                    await asyncio.sleep(1)
                    continue

                self.latest_data = market_data

                # 2. Compute features
                features = self.feature_engineer.compute_features(market_data)

                if not features:
                    await asyncio.sleep(5)
                    continue

                # 3. Get ML predictions
                ml_prediction = self.ml_model.predict(features)

                # 4. Get RL agent decision
                state = self._construct_rl_state(features, ml_prediction)
                action = self.rl_agent.predict(state)

                # 5. Risk checks
                if not self.risk_manager.can_trade():
                    self.logger.warning("Risk manager blocked trading")
                    await asyncio.sleep(5)
                    continue

                # 6. Execute action
                await self._execute_action(action, market_data, ml_prediction)

                # 7. Update monitoring
                await self._update_monitoring()

                # Wait before next iteration
                await asyncio.sleep(self.config['check_interval'])

            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}", exc_info=True)
                await self.notifier.send_error(f"Trading loop error: {str(e)}")
                await asyncio.sleep(10)

    async def _get_latest_market_data(self) -> Optional[Dict]:
        """
        Get latest market data from WebSocket or API
        """
        try:
            symbol = self.config['symbol']

            # Get latest kline data
            kline_data = self.websocket_streamer.get_latest_kline(symbol) if self.websocket_streamer else None

            # Get latest funding data
            funding_data = self.websocket_streamer.get_latest_funding(symbol) if self.websocket_streamer else None

            # Get OI data (would fetch from API)
            oi_data = await self.order_executor.fetch_open_interest_hist(
                symbol=symbol,
                period='5m',
                limit=1
            )

            if kline_data:
                oi_value = oi_data.iloc[-1]['sum_open_interest'] if len(oi_data) > 0 else 0

                return {
                    'price': kline_data,
                    'oi': {'sum_open_interest': oi_value},
                    'funding': funding_data if funding_data else {},
                    'timestamp': datetime.now()
                }

            return None

        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            return None

    def _construct_rl_state(self, features: Dict, ml_prediction: Dict) -> np.ndarray:
        """
        Construct state vector for RL agent
        """
        # Position status
        position = self.current_position['direction'] if self.current_position else 0
        position_pnl = self.current_position['unrealized_pnl'] if self.current_position else 0
        time_in_position = self.current_position['duration'] if self.current_position else 0

        # ML predictions
        ml_signal = ml_prediction['signal'] - 1  # Convert to -1, 0, 1
        ml_confidence = ml_prediction['confidence']
        ml_target = ml_prediction['target']

        # Market conditions
        market_features = [
            features.get('return_20', 0),
            features.get('natr', 0.02),
            features.get('rsi_14', 50) / 100,
            features.get('oi_price_divergence_20', 0),
            features.get('oi_change_20', 0),
            features.get('funding_rate', 0) * 100,
            features.get('volume_ratio', 1),
            features.get('bb_position', 0.5)
        ]

        # Account status
        account = self.order_executor.get_account_info()
        equity = account['total_balance']
        equity_ratio = equity / self.config['initial_balance'] if self.config['initial_balance'] > 0 else 1
        balance_ratio = account['available_balance'] / equity if equity > 0 else 1

        # Construct state
        state = np.array([
            position,
            position_pnl / equity if equity > 0 else 0,
            min(time_in_position / 100, 1.0),
            ml_signal,
            ml_confidence,
            ml_target,
            *market_features,
            equity_ratio,
            self.risk_manager.current_drawdown,
            balance_ratio,
            self.risk_manager.get_recent_sharpe(),
            self._calculate_liquidation_distance(),
            self.trades_today / 20  # Normalize
        ], dtype=np.float32)

        return state

    async def _execute_action(self, action: int, market_data: Dict, ml_prediction: Dict):
        """
        Execute RL agent's action
        """
        current_price = float(market_data['price']['close'])

        try:
            if action == 0:  # HOLD
                pass

            elif action == 1:  # ENTER_LONG
                if self.current_position is None:
                    await self._open_position('LONG', current_price, ml_prediction)

            elif action == 2:  # ENTER_SHORT
                if self.current_position is None:
                    await self._open_position('SHORT', current_price, ml_prediction)

            elif action == 3:  # EXIT_POSITION
                if self.current_position is not None:
                    await self._close_position(current_price)

            elif action == 4:  # SCALE_IN
                if self.current_position is not None:
                    self.logger.info("SCALE_IN action (not implemented)")

            elif action == 5:  # SCALE_OUT
                if self.current_position is not None:
                    self.logger.info("SCALE_OUT action (not implemented)")

        except Exception as e:
            self.logger.error(f"Error executing action: {e}", exc_info=True)
            await self.notifier.send_error(f"Execution error: {str(e)}")

    async def _open_position(self, side: str, price: float, ml_prediction: Dict):
        """
        Open new position
        """
        # Calculate position size
        account = self.order_executor.get_account_info()
        equity = account['total_balance']

        # Risk 2% per trade
        risk_amount = equity * 0.02
        atr = self.latest_data.get('atr_14', price * 0.02)
        stop_distance = 1.5 * atr

        position_size = self.risk_manager.calculate_position_size(
            equity=equity,
            risk_per_trade=0.02,
            stop_distance=stop_distance,
            price=price,
            leverage=self.config['leverage']
        )

        # Risk checks
        if not self.risk_manager.validate_position(position_size, price, self.config['leverage']):
            self.logger.warning("Position size rejected by risk manager")
            return

        # Check if paper trading mode
        if self.config['safety'].get('paper_trading_mode', True):
            self.logger.info(f"[PAPER TRADING] Would open {side} position: {position_size:.4f} @ ${price:.2f}")

            # Simulate position
            self.current_position = {
                'direction': 1 if side == 'LONG' else -1,
                'entry_price': price,
                'size': position_size,
                'entry_time': datetime.now(),
                'duration': 0,
                'unrealized_pnl': 0,
                'stop_loss': price - (stop_distance if side == 'LONG' else -stop_distance),
                'take_profit': price + (ml_prediction['target'] * price),
                'ml_confidence': ml_prediction['confidence']
            }

            self.trades_today += 1
            self.trade_logger.log_entry(self.current_position)

            await self.notifier.send_trade_alert(
                f"[PAPER] OPENED {side} POSITION\n"
                f"Entry: ${price:.2f}\n"
                f"Size: {position_size:.4f}\n"
                f"SL: ${self.current_position['stop_loss']:.2f}\n"
                f"TP: ${self.current_position['take_profit']:.2f}\n"
                f"ML Confidence: {ml_prediction['confidence']:.2%}"
            )

            return

        # Execute order (real trading)
        order = await self.order_executor.place_market_order(
            symbol=self.config['symbol'],
            side=side,
            quantity=position_size
        )

        if order['status'] == 'FILLED':
            self.current_position = {
                'direction': 1 if side == 'LONG' else -1,
                'entry_price': order['average_price'],
                'size': position_size,
                'entry_time': datetime.now(),
                'duration': 0,
                'unrealized_pnl': 0,
                'stop_loss': price - (stop_distance if side == 'LONG' else -stop_distance),
                'take_profit': price + (ml_prediction['target'] * price),
                'ml_confidence': ml_prediction['confidence']
            }

            self.trades_today += 1
            self.trade_logger.log_entry(self.current_position)

            await self.notifier.send_trade_alert(
                f"OPENED {side} POSITION\n"
                f"Entry: ${price:.2f}\n"
                f"Size: {position_size:.4f}\n"
                f"SL: ${self.current_position['stop_loss']:.2f}\n"
                f"TP: ${self.current_position['take_profit']:.2f}\n"
                f"ML Confidence: {ml_prediction['confidence']:.2%}"
            )

    async def _close_position(self, price: float):
        """
        Close current position
        """
        if self.current_position is None:
            return

        side = 'SELL' if self.current_position['direction'] == 1 else 'BUY'

        # Check if paper trading mode
        if self.config['safety'].get('paper_trading_mode', True):
            # Calculate PnL
            exit_price = price
            pnl = (exit_price - self.current_position['entry_price']) * \
                  self.current_position['size'] * self.current_position['direction']

            self.daily_pnl += pnl

            self.logger.info(f"[PAPER TRADING] Would close position: PnL=${pnl:.2f}")

            self.trade_logger.log_exit(self.current_position, exit_price, pnl)
            self.risk_manager.record_trade(pnl)

            pnl_emoji = "✅" if pnl > 0 else "❌"
            await self.notifier.send_trade_alert(
                f"{pnl_emoji} [PAPER] CLOSED POSITION\n"
                f"Entry: ${self.current_position['entry_price']:.2f}\n"
                f"Exit: ${exit_price:.2f}\n"
                f"PnL: ${pnl:.2f} ({pnl/self.current_position['entry_price']*100:.2f}%)\n"
                f"Duration: {self.current_position['duration']} periods"
            )

            self.current_position = None
            return

        # Execute close order (real trading)
        order = await self.order_executor.place_market_order(
            symbol=self.config['symbol'],
            side=side,
            quantity=self.current_position['size']
        )

        if order['status'] == 'FILLED':
            exit_price = order['average_price']
            pnl = (exit_price - self.current_position['entry_price']) * \
                  self.current_position['size'] * self.current_position['direction']

            self.daily_pnl += pnl
            self.trade_logger.log_exit(self.current_position, exit_price, pnl)
            self.risk_manager.record_trade(pnl)

            pnl_emoji = "✅" if pnl > 0 else "❌"
            await self.notifier.send_trade_alert(
                f"{pnl_emoji} CLOSED POSITION\n"
                f"Entry: ${self.current_position['entry_price']:.2f}\n"
                f"Exit: ${exit_price:.2f}\n"
                f"PnL: ${pnl:.2f}\n"
                f"Duration: {self.current_position['duration']} periods"
            )

            self.current_position = None

    def _calculate_liquidation_distance(self) -> float:
        """
        Calculate distance to liquidation
        """
        if self.current_position is None:
            return 1.0

        current_price = float(self.latest_data.get('close', self.current_position['entry_price']))
        leverage = self.config['leverage']
        direction = self.current_position['direction']
        entry_price = self.current_position['entry_price']

        if direction == 1:  # Long
            liq_price = entry_price * (1 - 0.9 / leverage)
            distance = (current_price - liq_price) / current_price if current_price > 0 else 0
        else:  # Short
            liq_price = entry_price * (1 + 0.9 / leverage)
            distance = (liq_price - current_price) / current_price if current_price > 0 else 0

        return max(0, min(1, distance))

    async def _update_monitoring(self):
        """
        Update monitoring metrics
        """
        # Update current position unrealized PnL
        if self.current_position:
            current_price_data = self.latest_data.get('price', {})
            current_price = float(current_price_data.get('close', 0))

            if current_price > 0:
                self.current_position['unrealized_pnl'] = (
                    (current_price - self.current_position['entry_price']) *
                    self.current_position['size'] *
                    self.current_position['direction']
                )
                self.current_position['duration'] += 1

        # Update risk manager
        account = self.order_executor.get_account_info()
        self.risk_manager.update(
            equity=account['total_balance'],
            daily_pnl=self.daily_pnl,
            trades_today=self.trades_today
        )

        # Log equity
        self.trade_logger.log_equity(account['total_balance'], self.daily_pnl)

    async def stop(self):
        """
        Stop the trading bot gracefully
        """
        self.logger.info("Stopping trading bot...")
        self.is_running = False

        # Close any open positions
        if self.current_position:
            current_price_data = self.latest_data.get('price', {})
            current_price = float(current_price_data.get('close', 0))
            if current_price > 0:
                await self._close_position(current_price)

        # Stop WebSocket
        if self.websocket_streamer:
            self.websocket_streamer.stop()

        # Send shutdown notification
        account = self.order_executor.get_account_info()
        await self.notifier.send_message(
            f"AI Trading Bot Stopped\n"
            f"Final Equity: ${account['total_balance']:.2f}\n"
            f"Daily PnL: ${self.daily_pnl:.2f}\n"
            f"Trades Today: {self.trades_today}"
        )

        self.logger.info("Trading bot stopped")
