"""
Reinforcement Learning Agent for Trading Decisions
Uses PPO (Proximal Policy Optimization) for action selection
"""

import numpy as np
import logging
import os
from typing import Dict, Optional
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback


class RLAgent:
    """
    RL Agent for making trading decisions
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.action_space = 6  # HOLD, ENTER_LONG, ENTER_SHORT, EXIT, SCALE_IN, SCALE_OUT

    @classmethod
    def load(cls, model_path: str) -> 'RLAgent':
        """
        Load trained RL agent from disk

        Args:
            model_path: Path to saved model file

        Returns:
            Loaded RLAgent instance
        """
        instance = cls()
        instance.logger.info(f"Loading RL agent from {model_path}")

        try:
            if os.path.exists(model_path):
                instance.model = PPO.load(model_path)
                instance.logger.info("RL agent loaded successfully")
            else:
                instance.logger.warning(f"Model file not found: {model_path}. Using dummy agent.")
                instance._init_dummy_agent()

        except Exception as e:
            instance.logger.error(f"Error loading RL agent: {e}. Using dummy agent.", exc_info=True)
            instance._init_dummy_agent()

        return instance

    def _init_dummy_agent(self):
        """Initialize a dummy agent for testing when real model is not available"""
        self.logger.warning("Initializing dummy RL agent for testing")
        # Dummy agent will make conservative decisions
        self.model = None

    def predict(self, state: np.ndarray, deterministic: bool = True) -> int:
        """
        Predict action given current state

        Args:
            state: State vector (numpy array)
            deterministic: Whether to use deterministic policy

        Returns:
            Action index (0-5)
        """
        try:
            if self.model is not None:
                action, _ = self.model.predict(state, deterministic=deterministic)
                action = int(action)
            else:
                # Dummy agent - mostly HOLD, occasionally trade
                action = self._dummy_policy(state)

            self.logger.debug(f"RL Agent action: {action} ({self._action_name(action)})")
            return action

        except Exception as e:
            self.logger.error(f"Error predicting action: {e}", exc_info=True)
            return 0  # Default to HOLD on error

    def _dummy_policy(self, state: np.ndarray) -> int:
        """
        Dummy policy for testing
        Makes conservative trading decisions based on simple rules
        """
        # Extract state components (assuming standardized state vector)
        if len(state) < 4:
            return 0  # HOLD

        position = state[0] if len(state) > 0 else 0
        ml_signal = state[3] if len(state) > 3 else 0
        ml_confidence = state[4] if len(state) > 4 else 0

        # Simple rule-based policy
        if position == 0:  # No position
            if ml_confidence > 0.65:
                if ml_signal > 0.5:
                    return 1  # ENTER_LONG
                elif ml_signal < -0.5:
                    return 2  # ENTER_SHORT
        elif position != 0:  # Has position
            # Exit if ML signal reversed or low confidence
            if ml_confidence < 0.5:
                return 3  # EXIT_POSITION

        return 0  # HOLD

    def _action_name(self, action: int) -> str:
        """Get action name from index"""
        action_names = ['HOLD', 'ENTER_LONG', 'ENTER_SHORT', 'EXIT', 'SCALE_IN', 'SCALE_OUT']
        return action_names[action] if 0 <= action < len(action_names) else 'UNKNOWN'

    def save(self, model_path: str):
        """
        Save RL agent to disk

        Args:
            model_path: Path to save model file
        """
        try:
            if self.model is not None:
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                self.model.save(model_path)
                self.logger.info(f"RL agent saved to {model_path}")
            else:
                self.logger.warning("No model to save (dummy agent)")

        except Exception as e:
            self.logger.error(f"Error saving RL agent: {e}", exc_info=True)

    def update(self, new_experiences: list):
        """
        Update RL agent with new experiences (online learning)

        Args:
            new_experiences: List of (state, action, reward, next_state, done) tuples
        """
        try:
            if self.model is not None and len(new_experiences) > 0:
                # This would involve adding to replay buffer and training
                # Simplified for now
                self.logger.info(f"Updating RL agent with {len(new_experiences)} new experiences")
                # Implementation would go here
            else:
                self.logger.debug("Skipping RL update (dummy agent or no experiences)")

        except Exception as e:
            self.logger.error(f"Error updating RL agent: {e}", exc_info=True)
