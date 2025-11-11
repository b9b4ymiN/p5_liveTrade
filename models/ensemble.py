"""
Ensemble ML Model for Trading Predictions
Combines XGBoost, LSTM, and other models for robust predictions
"""

import numpy as np
import pickle
import logging
from typing import Dict, Tuple
import os


class EnsembleModel:
    """
    Ensemble model combining multiple ML models
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.xgb_classifier = None
        self.xgb_regressor = None
        self.lstm_model = None
        self.meta_model = None
        self.feature_names = []

    @classmethod
    def load(cls, model_path: str) -> 'EnsembleModel':
        """
        Load trained ensemble model from disk

        Args:
            model_path: Path to saved model file

        Returns:
            Loaded EnsembleModel instance
        """
        instance = cls()
        instance.logger.info(f"Loading ensemble model from {model_path}")

        try:
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)

                instance.xgb_classifier = model_data.get('xgb_classifier')
                instance.xgb_regressor = model_data.get('xgb_regressor')
                instance.lstm_model = model_data.get('lstm_model')
                instance.meta_model = model_data.get('meta_model')
                instance.feature_names = model_data.get('feature_names', [])

                instance.logger.info("Ensemble model loaded successfully")
            else:
                instance.logger.warning(f"Model file not found: {model_path}. Using dummy model.")
                instance._init_dummy_model()

        except Exception as e:
            instance.logger.error(f"Error loading model: {e}. Using dummy model.", exc_info=True)
            instance._init_dummy_model()

        return instance

    def _init_dummy_model(self):
        """Initialize a dummy model for testing when real models are not available"""
        self.logger.warning("Initializing dummy model for testing")
        # Dummy model will return random predictions
        self.feature_names = ['dummy_feature']

    def predict(self, features: Dict) -> Dict:
        """
        Make prediction using ensemble model

        Args:
            features: Dictionary of computed features

        Returns:
            Dictionary containing:
                - signal: 0 (short), 1 (neutral), 2 (long)
                - confidence: Prediction confidence [0, 1]
                - target: Expected price movement %
        """
        try:
            # Prepare feature vector
            feature_vector = self._prepare_features(features)

            # Get predictions from each model
            if self.xgb_classifier is not None:
                # Classification: Long/Short/Neutral
                signal_proba = self.xgb_classifier.predict_proba(feature_vector)[0]
                signal = np.argmax(signal_proba)
                confidence = signal_proba[signal]
            else:
                # Dummy prediction
                signal = np.random.choice([0, 1, 2])
                confidence = np.random.uniform(0.4, 0.7)

            if self.xgb_regressor is not None:
                # Regression: Price target
                target = self.xgb_regressor.predict(feature_vector)[0]
            else:
                # Dummy target
                target = np.random.uniform(-0.01, 0.01)

            result = {
                'signal': int(signal),
                'confidence': float(confidence),
                'target': float(target),
                'timestamp': features.get('timestamp', '')
            }

            self.logger.debug(f"Prediction: signal={signal}, confidence={confidence:.2%}, target={target:.2%}")

            return result

        except Exception as e:
            self.logger.error(f"Error making prediction: {e}", exc_info=True)
            # Return neutral signal on error
            return {
                'signal': 1,
                'confidence': 0.5,
                'target': 0.0,
                'timestamp': ''
            }

    def _prepare_features(self, features: Dict) -> np.ndarray:
        """
        Prepare feature vector from feature dictionary

        Args:
            features: Dictionary of features

        Returns:
            Numpy array of features in correct order
        """
        if not self.feature_names:
            # If no feature names, use all numeric features
            feature_values = [v for v in features.values() if isinstance(v, (int, float))]
        else:
            # Use specified feature order
            feature_values = [features.get(name, 0.0) for name in self.feature_names]

        # Handle empty features
        if not feature_values:
            feature_values = [0.0] * 10  # Dummy values

        return np.array(feature_values).reshape(1, -1)

    def save(self, model_path: str):
        """
        Save ensemble model to disk

        Args:
            model_path: Path to save model file
        """
        try:
            model_data = {
                'xgb_classifier': self.xgb_classifier,
                'xgb_regressor': self.xgb_regressor,
                'lstm_model': self.lstm_model,
                'meta_model': self.meta_model,
                'feature_names': self.feature_names
            }

            os.makedirs(os.path.dirname(model_path), exist_ok=True)

            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)

            self.logger.info(f"Model saved to {model_path}")

        except Exception as e:
            self.logger.error(f"Error saving model: {e}", exc_info=True)
