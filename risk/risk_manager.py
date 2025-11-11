"""
Risk Management Layer
Implements safety controls and position sizing
"""

import numpy as np
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta


class RiskManager:
    """
    Risk manager for trading bot
    Enforces position limits, loss limits, and safety controls
    """

    def __init__(self, config: Dict):
        """
        Initialize risk manager

        Args:
            config: Risk configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Risk parameters
        self.max_position_size = config.get('max_position_size', 0.2)
        self.risk_per_trade = config.get('risk_per_trade', 0.02)
        self.max_daily_loss = config.get('max_daily_loss', 0.03)
        self.max_trades_per_day = config.get('max_trades_per_day', 20)
        self.max_consecutive_losses = config.get('max_consecutive_losses', 5)
        self.min_liquidation_distance = config.get('min_liquidation_distance', 0.15)

        # State tracking
        self.initial_equity = None
        self.current_equity = None
        self.daily_pnl = 0
        self.peak_equity = None
        self.current_drawdown = 0
        self.consecutive_losses = 0
        self.trades_today = 0
        self.last_reset_date = datetime.now().date()

        # Performance tracking
        self.recent_returns = []
        self.trade_history = []

    def can_trade(self) -> bool:
        """
        Check if trading is allowed based on risk rules

        Returns:
            True if can trade, False otherwise
        """
        # Reset daily counters if new day
        self._check_daily_reset()

        # Check 1: Daily loss limit
        if self.current_equity and self.initial_equity:
            daily_loss_pct = self.daily_pnl / self.initial_equity
            if daily_loss_pct <= -self.max_daily_loss:
                self.logger.warning(f"Daily loss limit reached: {daily_loss_pct:.2%}")
                return False

        # Check 2: Max trades per day
        if self.trades_today >= self.max_trades_per_day:
            self.logger.warning(f"Max trades per day reached: {self.trades_today}")
            return False

        # Check 3: Consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.logger.warning(f"Max consecutive losses reached: {self.consecutive_losses}")
            return False

        return True

    def validate_position(self, position_size: float, price: float, leverage: int) -> bool:
        """
        Validate if a position size is within risk limits

        Args:
            position_size: Proposed position size (in contracts)
            price: Entry price
            leverage: Leverage multiplier

        Returns:
            True if position is valid, False otherwise
        """
        if not self.current_equity:
            self.logger.warning("No equity information available")
            return False

        # Calculate position value
        position_value = position_size * price

        # Check position size limit
        max_position_value = self.current_equity * self.max_position_size * leverage
        if position_value > max_position_value:
            self.logger.warning(
                f"Position size too large: ${position_value:.2f} > ${max_position_value:.2f}"
            )
            return False

        # Check minimum position size
        if position_value < 10:  # Minimum $10
            self.logger.warning(f"Position size too small: ${position_value:.2f}")
            return False

        return True

    def calculate_position_size(
        self,
        equity: float,
        risk_per_trade: float,
        stop_distance: float,
        price: float,
        leverage: int
    ) -> float:
        """
        Calculate optimal position size based on risk parameters

        Args:
            equity: Current account equity
            risk_per_trade: Risk percentage per trade (e.g., 0.02 for 2%)
            stop_distance: Distance to stop loss in price units
            price: Entry price
            leverage: Leverage multiplier

        Returns:
            Position size in contracts
        """
        # Risk amount in dollars
        risk_amount = equity * risk_per_trade

        # Position size = Risk Amount / Stop Distance
        # Adjusted for leverage
        if stop_distance > 0 and price > 0:
            position_size = risk_amount / stop_distance
        else:
            # Fallback to conservative position size
            position_size = (equity * 0.1 * leverage) / price

        # Apply maximum position size constraint
        max_size = (equity * self.max_position_size * leverage) / price
        position_size = min(position_size, max_size)

        self.logger.debug(
            f"Position size: {position_size:.4f} contracts "
            f"(Risk: ${risk_amount:.2f}, Stop: ${stop_distance:.2f})"
        )

        return position_size

    def update(self, equity: float, daily_pnl: float, trades_today: int):
        """
        Update risk manager with current account state

        Args:
            equity: Current account equity
            daily_pnl: Today's PnL
            trades_today: Number of trades today
        """
        # Initialize if first update
        if self.initial_equity is None:
            self.initial_equity = equity
            self.peak_equity = equity

        self.current_equity = equity
        self.daily_pnl = daily_pnl
        self.trades_today = trades_today

        # Update peak equity and drawdown
        if equity > self.peak_equity:
            self.peak_equity = equity

        self.current_drawdown = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0

        self.logger.debug(
            f"Risk Update - Equity: ${equity:.2f}, Daily PnL: ${daily_pnl:.2f}, "
            f"Drawdown: {self.current_drawdown:.2%}, Trades: {trades_today}"
        )

    def record_trade(self, pnl: float):
        """
        Record trade result for tracking

        Args:
            pnl: Trade PnL
        """
        self.trade_history.append({
            'pnl': pnl,
            'timestamp': datetime.now()
        })

        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Track recent returns for Sharpe calculation
        if self.current_equity and self.current_equity > 0:
            trade_return = pnl / self.current_equity
            self.recent_returns.append(trade_return)

            # Keep last 50 returns
            if len(self.recent_returns) > 50:
                self.recent_returns = self.recent_returns[-50:]

    def get_recent_sharpe(self) -> float:
        """
        Calculate Sharpe ratio from recent trades

        Returns:
            Sharpe ratio
        """
        if len(self.recent_returns) < 5:
            return 0.0

        returns = np.array(self.recent_returns)
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualized Sharpe (assuming ~100 trades per year)
        sharpe = (mean_return / std_return) * np.sqrt(100)

        return sharpe

    def _check_daily_reset(self):
        """Reset daily counters if new day"""
        current_date = datetime.now().date()

        if current_date > self.last_reset_date:
            self.logger.info(f"Resetting daily counters for new day: {current_date}")
            self.daily_pnl = 0
            self.trades_today = 0
            self.last_reset_date = current_date
            self.initial_equity = self.current_equity

    def get_risk_metrics(self) -> Dict:
        """
        Get current risk metrics

        Returns:
            Dictionary of risk metrics
        """
        return {
            'equity': self.current_equity,
            'daily_pnl': self.daily_pnl,
            'drawdown': self.current_drawdown,
            'consecutive_losses': self.consecutive_losses,
            'trades_today': self.trades_today,
            'sharpe': self.get_recent_sharpe(),
            'can_trade': self.can_trade()
        }
