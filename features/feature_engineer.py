"""
Feature Engineering for Live Trading
Computes features in real-time from market data
"""

import numpy as np
import pandas as pd
from typing import Dict, List
import logging


class FeatureEngineer:
    """
    Compute trading features from real-time market data
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Store historical data for rolling calculations
        self.price_history = []
        self.oi_history = []
        self.volume_history = []
        self.funding_history = []

    def compute_features(self, market_data: Dict) -> Dict:
        """
        Compute all features from market data

        Args:
            market_data: Dictionary containing price, OI, funding data

        Returns:
            Dictionary of computed features
        """
        try:
            # Extract data
            price_data = market_data.get('price', {})
            oi_data = market_data.get('oi', {})
            funding_data = market_data.get('funding', {})

            # Update history
            self._update_history(price_data, oi_data, funding_data)

            # Compute features
            features = {}

            # Price features
            features.update(self._compute_price_features())

            # OI features
            features.update(self._compute_oi_features())

            # Volume features
            features.update(self._compute_volume_features())

            # Funding features
            features.update(self._compute_funding_features())

            # Cross features
            features.update(self._compute_cross_features())

            return features

        except Exception as e:
            self.logger.error(f"Error computing features: {e}", exc_info=True)
            return {}

    def _update_history(self, price_data: Dict, oi_data: Dict, funding_data: Dict):
        """Update historical data buffers"""
        if price_data:
            self.price_history.append({
                'close': price_data.get('close', 0),
                'high': price_data.get('high', 0),
                'low': price_data.get('low', 0),
                'open': price_data.get('open', 0),
                'volume': price_data.get('volume', 0)
            })

        if oi_data:
            self.oi_history.append(oi_data.get('sum_open_interest', 0))

        if funding_data:
            self.funding_history.append(funding_data.get('funding_rate', 0))

        # Keep last 100 periods
        max_history = 100
        if len(self.price_history) > max_history:
            self.price_history = self.price_history[-max_history:]
        if len(self.oi_history) > max_history:
            self.oi_history = self.oi_history[-max_history:]
        if len(self.funding_history) > max_history:
            self.funding_history = self.funding_history[-max_history:]

    def _compute_price_features(self) -> Dict:
        """Compute price-based features"""
        features = {}

        if len(self.price_history) < 2:
            return features

        # Convert to arrays
        closes = np.array([p['close'] for p in self.price_history])
        highs = np.array([p['high'] for p in self.price_history])
        lows = np.array([p['low'] for p in self.price_history])
        volumes = np.array([p['volume'] for p in self.price_history])

        # Returns
        if len(closes) >= 2:
            features['return_1'] = (closes[-1] - closes[-2]) / closes[-2] if closes[-2] != 0 else 0
        if len(closes) >= 5:
            features['return_5'] = (closes[-1] - closes[-5]) / closes[-5] if closes[-5] != 0 else 0
        if len(closes) >= 20:
            features['return_20'] = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] != 0 else 0

        # Volatility (ATR-based)
        if len(closes) >= 14:
            tr_list = []
            for i in range(1, len(closes)):
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i - 1]),
                    abs(lows[i] - closes[i - 1])
                )
                tr_list.append(tr)
            atr_14 = np.mean(tr_list[-14:])
            features['atr_14'] = atr_14
            features['natr'] = atr_14 / closes[-1] if closes[-1] != 0 else 0

        # RSI
        if len(closes) >= 14:
            features['rsi_14'] = self._calculate_rsi(closes, 14)

        # Bollinger Bands
        if len(closes) >= 20:
            bb_features = self._calculate_bollinger_bands(closes, 20, 2)
            features.update(bb_features)

        # Moving averages
        if len(closes) >= 20:
            features['sma_20'] = np.mean(closes[-20:])
            features['price_to_sma20'] = closes[-1] / features['sma_20'] - 1 if features['sma_20'] != 0 else 0

        # Volume
        if len(volumes) >= 20:
            features['volume_ratio'] = volumes[-1] / np.mean(volumes[-20:]) if np.mean(volumes[-20:]) != 0 else 1

        return features

    def _compute_oi_features(self) -> Dict:
        """Compute Open Interest features"""
        features = {}

        if len(self.oi_history) < 2:
            return features

        oi = np.array(self.oi_history)

        # OI changes
        if len(oi) >= 2:
            features['oi_change_1'] = (oi[-1] - oi[-2]) / oi[-2] if oi[-2] != 0 else 0
        if len(oi) >= 5:
            features['oi_change_5'] = (oi[-1] - oi[-5]) / oi[-5] if oi[-5] != 0 else 0
        if len(oi) >= 20:
            features['oi_change_20'] = (oi[-1] - oi[-20]) / oi[-20] if oi[-20] != 0 else 0

        # OI velocity & acceleration
        if len(oi) >= 3:
            velocity = (oi[-1] - oi[-2]) / oi[-2] if oi[-2] != 0 else 0
            prev_velocity = (oi[-2] - oi[-3]) / oi[-3] if oi[-3] != 0 else 0
            features['oi_velocity'] = velocity
            features['oi_acceleration'] = velocity - prev_velocity

        # OI Z-score
        if len(oi) >= 20:
            oi_mean = np.mean(oi[-20:])
            oi_std = np.std(oi[-20:])
            features['oi_zscore'] = (oi[-1] - oi_mean) / oi_std if oi_std != 0 else 0

        return features

    def _compute_volume_features(self) -> Dict:
        """Compute volume features"""
        features = {}

        if len(self.price_history) < 2:
            return features

        volumes = np.array([p['volume'] for p in self.price_history])

        # Volume changes
        if len(volumes) >= 2:
            features['volume_change_1'] = (volumes[-1] - volumes[-2]) / volumes[-2] if volumes[-2] != 0 else 0

        # Volume Z-score
        if len(volumes) >= 20:
            vol_mean = np.mean(volumes[-20:])
            vol_std = np.std(volumes[-20:])
            features['volume_zscore'] = (volumes[-1] - vol_mean) / vol_std if vol_std != 0 else 0

        return features

    def _compute_funding_features(self) -> Dict:
        """Compute funding rate features"""
        features = {}

        if len(self.funding_history) < 1:
            return features

        funding = np.array(self.funding_history)

        # Latest funding rate
        features['funding_rate'] = funding[-1]

        # Funding changes
        if len(funding) >= 2:
            features['funding_change_1'] = funding[-1] - funding[-2]

        # Cumulative funding
        if len(funding) >= 8:
            features['funding_cumulative_8'] = np.sum(funding[-8:])

        # Funding Z-score
        if len(funding) >= 20:
            funding_mean = np.mean(funding[-20:])
            funding_std = np.std(funding[-20:])
            features['funding_zscore'] = (funding[-1] - funding_mean) / funding_std if funding_std != 0 else 0

        return features

    def _compute_cross_features(self) -> Dict:
        """Compute cross-feature interactions"""
        features = {}

        # OI-Price divergence
        if len(self.price_history) >= 20 and len(self.oi_history) >= 20:
            closes = np.array([p['close'] for p in self.price_history])

            price_change_20 = (closes[-1] - closes[-20]) / closes[-20] if closes[-20] != 0 else 0
            oi_change_20 = (self.oi_history[-1] - self.oi_history[-20]) / self.oi_history[-20] \
                if self.oi_history[-20] != 0 else 0

            features['oi_price_divergence_20'] = oi_change_20 - price_change_20

        return features

    @staticmethod
    def _calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def _calculate_bollinger_bands(prices: np.ndarray, period: int = 20, num_std: float = 2) -> Dict:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return {}

        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])

        upper_band = sma + (num_std * std)
        lower_band = sma - (num_std * std)

        # BB Position: where is price relative to bands (0 = lower, 0.5 = middle, 1 = upper)
        bb_range = upper_band - lower_band
        bb_position = (prices[-1] - lower_band) / bb_range if bb_range != 0 else 0.5

        return {
            'bb_upper': upper_band,
            'bb_middle': sma,
            'bb_lower': lower_band,
            'bb_width': bb_range / sma if sma != 0 else 0,
            'bb_position': bb_position
        }
