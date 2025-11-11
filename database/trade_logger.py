"""
Trade Logger
Logs all trades and account history to database
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os


class TradeLogger:
    """
    Log trades to database or file
    """

    def __init__(self, config: Dict):
        """
        Initialize trade logger

        Args:
            config: Database configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.log_file = "./logs/trades.jsonl"

        # Create logs directory
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # In production, would connect to PostgreSQL/TimescaleDB
        self.logger.info(f"Trade logger initialized (file mode: {self.log_file})")

    def log_entry(self, position: Dict):
        """
        Log position entry

        Args:
            position: Position dictionary
        """
        try:
            entry_log = {
                'type': 'entry',
                'timestamp': datetime.now().isoformat(),
                'direction': position.get('direction'),
                'entry_price': position.get('entry_price'),
                'size': position.get('size'),
                'stop_loss': position.get('stop_loss'),
                'take_profit': position.get('take_profit'),
                'ml_confidence': position.get('ml_confidence')
            }

            self._write_log(entry_log)
            self.logger.info(f"Position entry logged: {entry_log}")

        except Exception as e:
            self.logger.error(f"Error logging entry: {e}", exc_info=True)

    def log_exit(self, position: Dict, exit_price: float, pnl: float):
        """
        Log position exit

        Args:
            position: Position dictionary
            exit_price: Exit price
            pnl: Realized PnL
        """
        try:
            exit_log = {
                'type': 'exit',
                'timestamp': datetime.now().isoformat(),
                'direction': position.get('direction'),
                'entry_price': position.get('entry_price'),
                'exit_price': exit_price,
                'size': position.get('size'),
                'pnl': pnl,
                'pnl_pct': (pnl / (position['entry_price'] * position['size'])) * 100 if position.get('entry_price') and position.get('size') else 0,
                'duration': position.get('duration', 0)
            }

            self._write_log(exit_log)
            self.logger.info(f"Position exit logged: PnL=${pnl:.2f}")

        except Exception as e:
            self.logger.error(f"Error logging exit: {e}", exc_info=True)

    def log_equity(self, equity: float, pnl: float):
        """
        Log equity snapshot

        Args:
            equity: Current equity
            pnl: Current PnL
        """
        try:
            equity_log = {
                'type': 'equity',
                'timestamp': datetime.now().isoformat(),
                'equity': equity,
                'pnl': pnl
            }

            self._write_log(equity_log)

        except Exception as e:
            self.logger.error(f"Error logging equity: {e}", exc_info=True)

    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """
        Get recent trades

        Args:
            limit: Number of trades to return

        Returns:
            List of trade dictionaries
        """
        try:
            trades = []

            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()

                # Get last N exit entries
                for line in reversed(lines):
                    try:
                        log_entry = json.loads(line)
                        if log_entry.get('type') == 'exit':
                            trades.append(log_entry)
                            if len(trades) >= limit:
                                break
                    except:
                        continue

            return trades

        except Exception as e:
            self.logger.error(f"Error getting recent trades: {e}")
            return []

    def get_equity_history(self, days: int = 7):
        """
        Get equity history

        Args:
            days: Number of days to fetch

        Returns:
            DataFrame or list of equity records
        """
        try:
            import pandas as pd

            equity_records = []

            if os.path.exists(self.log_file):
                cutoff_time = datetime.now() - timedelta(days=days)

                with open(self.log_file, 'r') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line)
                            if log_entry.get('type') == 'equity':
                                timestamp = datetime.fromisoformat(log_entry['timestamp'])
                                if timestamp >= cutoff_time:
                                    equity_records.append({
                                        'timestamp': timestamp,
                                        'equity': log_entry['equity']
                                    })
                        except:
                            continue

            return pd.DataFrame(equity_records)

        except Exception as e:
            self.logger.error(f"Error getting equity history: {e}")
            import pandas as pd
            return pd.DataFrame()

    def get_trades_last_n_hours(self, hours: int) -> List[Dict]:
        """
        Get trades from last N hours

        Args:
            hours: Number of hours to look back

        Returns:
            List of trade dictionaries
        """
        try:
            trades = []
            cutoff_time = datetime.now() - timedelta(hours=hours)

            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line)
                            if log_entry.get('type') == 'exit':
                                timestamp = datetime.fromisoformat(log_entry['timestamp'])
                                if timestamp >= cutoff_time:
                                    trades.append(log_entry)
                        except:
                            continue

            return trades

        except Exception as e:
            self.logger.error(f"Error getting trades: {e}")
            return []

    def get_trades_last_n_days(self, days: int) -> List[Dict]:
        """Get trades from last N days"""
        return self.get_trades_last_n_hours(days * 24)

    def _write_log(self, log_entry: Dict):
        """Write log entry to file"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception as e:
            self.logger.error(f"Error writing log: {e}", exc_info=True)
