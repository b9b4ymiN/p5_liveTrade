"""
Shadow Mode Deployment
Run new model in parallel without trading to evaluate performance
"""

import logging
from typing import Dict, Optional
from datetime import datetime
import json
import os


class ShadowDeployment:
    """
    Runs models in shadow mode for safe evaluation
    """

    def __init__(self, log_dir: str = "./logs/shadow"):
        self.logger = logging.getLogger(__name__)
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        self.shadow_models = {}
        self.shadow_results = []

    def add_shadow_model(self, model_id: str, model, description: str = ""):
        """
        Add a model to shadow deployment

        Args:
            model_id: Identifier for the shadow model
            model: Model instance
            description: Description of the model
        """
        self.shadow_models[model_id] = {
            "model": model,
            "description": description,
            "predictions": [],
            "started_at": datetime.now().isoformat()
        }

        self.logger.info(f"Added shadow model: {model_id} - {description}")

    def run_shadow_inference(
        self,
        prod_model,
        features: Dict,
        market_data: Dict
    ) -> Dict:
        """
        Run inference on both production and shadow models

        Args:
            prod_model: Production model
            features: Feature dictionary
            market_data: Market data

        Returns:
            Comparison results
        """
        timestamp = datetime.now().isoformat()

        # Production model prediction
        prod_prediction = prod_model.predict(features)

        # Shadow model predictions
        shadow_predictions = {}
        for model_id, shadow_info in self.shadow_models.items():
            try:
                shadow_model = shadow_info["model"]
                shadow_pred = shadow_model.predict(features)
                shadow_predictions[model_id] = shadow_pred

                # Store prediction
                shadow_info["predictions"].append({
                    "timestamp": timestamp,
                    "prediction": shadow_pred,
                    "features_hash": hash(json.dumps(features, sort_keys=True))
                })

            except Exception as e:
                self.logger.error(f"Shadow model {model_id} error: {e}")
                shadow_predictions[model_id] = None

        # Compare predictions
        comparison = {
            "timestamp": timestamp,
            "production": prod_prediction,
            "shadow": shadow_predictions,
            "market_data": {
                "price": market_data.get("price", {}).get("close", 0),
                "symbol": "SOLUSDT"  # From config
            }
        }

        # Log comparison
        self._log_shadow_comparison(comparison)
        self.shadow_results.append(comparison)

        return comparison

    def get_shadow_metrics(self, model_id: str, window_hours: int = 24) -> Dict:
        """
        Calculate performance metrics for shadow model

        Args:
            model_id: Shadow model ID
            window_hours: Time window for metrics (hours)

        Returns:
            Performance metrics
        """
        if model_id not in self.shadow_models:
            return {}

        shadow_info = self.shadow_models[model_id]
        predictions = shadow_info["predictions"]

        # Calculate metrics (simplified)
        total_predictions = len(predictions)

        # Agreement rate with production (from stored comparisons)
        agreement_count = 0
        for result in self.shadow_results[-100:]:  # Last 100
            prod_signal = result["production"].get("signal")
            shadow_signal = result["shadow"].get(model_id, {}).get("signal")

            if prod_signal == shadow_signal:
                agreement_count += 1

        agreement_rate = agreement_count / len(self.shadow_results[-100:]) if self.shadow_results else 0

        metrics = {
            "model_id": model_id,
            "total_predictions": total_predictions,
            "agreement_rate": agreement_rate,
            "started_at": shadow_info["started_at"],
            "duration_hours": (
                datetime.now() - datetime.fromisoformat(shadow_info["started_at"])
            ).total_seconds() / 3600
        }

        return metrics

    def evaluate_promotion_criteria(
        self,
        model_id: str,
        min_hours: int = 168  # 7 days
    ) -> Dict:
        """
        Evaluate if shadow model meets promotion criteria

        Args:
            model_id: Shadow model ID
            min_hours: Minimum hours in shadow mode

        Returns:
            Evaluation results with recommendation
        """
        metrics = self.get_shadow_metrics(model_id)

        duration_hours = metrics.get("duration_hours", 0)
        agreement_rate = metrics.get("agreement_rate", 0)

        # Criteria
        meets_duration = duration_hours >= min_hours
        sufficient_data = metrics.get("total_predictions", 0) >= 100

        evaluation = {
            "model_id": model_id,
            "meets_criteria": meets_duration and sufficient_data,
            "checks": {
                "duration_hours": {
                    "value": duration_hours,
                    "required": min_hours,
                    "passed": meets_duration
                },
                "total_predictions": {
                    "value": metrics.get("total_predictions", 0),
                    "required": 100,
                    "passed": sufficient_data
                }
            },
            "recommendation": "PROMOTE" if (meets_duration and sufficient_data) else "CONTINUE_SHADOW",
            "evaluated_at": datetime.now().isoformat()
        }

        return evaluation

    def _log_shadow_comparison(self, comparison: Dict):
        """Log shadow comparison to file"""
        log_file = os.path.join(self.log_dir, "shadow_eval.jsonl")

        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(comparison) + '\n')
        except Exception as e:
            self.logger.error(f"Error logging shadow comparison: {e}")

    def export_shadow_report(self, model_id: str, output_path: str):
        """
        Export comprehensive shadow deployment report

        Args:
            model_id: Shadow model ID
            output_path: Output file path
        """
        metrics = self.get_shadow_metrics(model_id)
        evaluation = self.evaluate_promotion_criteria(model_id)

        report = {
            "model_id": model_id,
            "metrics": metrics,
            "evaluation": evaluation,
            "generated_at": datetime.now().isoformat()
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Shadow report exported to {output_path}")
