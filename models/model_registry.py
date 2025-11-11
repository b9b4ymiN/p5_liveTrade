"""
Model Registry and Version Management
Handles model versioning, checksums, and rollback
"""

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging


class ModelRegistry:
    """
    Manages model versions, checksums, and metadata
    """

    def __init__(self, registry_path: str = "./models_saved"):
        self.registry_path = Path(registry_path)
        self.registry_file = self.registry_path / "registry.json"
        self.logger = logging.getLogger(__name__)

        # Create registry directory
        self.registry_path.mkdir(parents=True, exist_ok=True)

        # Load or create registry
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        """Load model registry from disk"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {
            "models": {},
            "current_version": None,
            "history": []
        }

    def _save_registry(self):
        """Save model registry to disk"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)

    def register_model(
        self,
        model_path: str,
        version: str,
        metadata: Dict,
        model_type: str = "ensemble"
    ) -> Dict:
        """
        Register a new model version

        Args:
            model_path: Path to model file
            version: Version identifier (e.g., "v1.0.0", "20240115_001")
            metadata: Model metadata (metrics, training info, etc.)
            model_type: Type of model

        Returns:
            Registration info with checksum
        """
        try:
            # Calculate checksum
            checksum = self._calculate_checksum(model_path)

            # Copy model to versioned location
            versioned_path = self.registry_path / f"{model_type}_{version}.pkl"
            shutil.copy2(model_path, versioned_path)

            # Create registration entry
            registration = {
                "version": version,
                "model_type": model_type,
                "path": str(versioned_path),
                "checksum": checksum,
                "metadata": metadata,
                "registered_at": datetime.now().isoformat(),
                "status": "registered"
            }

            # Add to registry
            self.registry["models"][version] = registration
            self.registry["history"].append({
                "version": version,
                "action": "registered",
                "timestamp": datetime.now().isoformat()
            })

            self._save_registry()

            self.logger.info(f"Model {version} registered with checksum {checksum[:8]}...")

            return registration

        except Exception as e:
            self.logger.error(f"Error registering model: {e}")
            raise

    def promote_model(self, version: str, validation_metrics: Dict) -> bool:
        """
        Promote a model version to production

        Args:
            version: Version to promote
            validation_metrics: Validation metrics that justify promotion

        Returns:
            True if promotion successful
        """
        try:
            if version not in self.registry["models"]:
                raise ValueError(f"Version {version} not found in registry")

            # Check promotion criteria
            sharpe = validation_metrics.get("sharpe", 0)
            max_dd = validation_metrics.get("max_drawdown", 100)

            if sharpe < 1.8 or max_dd > 20:
                self.logger.warning(
                    f"Model {version} does not meet promotion criteria: "
                    f"Sharpe={sharpe:.2f}, MaxDD={max_dd:.1f}%"
                )
                return False

            # Store previous version for rollback
            previous_version = self.registry.get("current_version")

            # Promote model
            self.registry["models"][version]["status"] = "production"
            self.registry["current_version"] = version
            self.registry["history"].append({
                "version": version,
                "action": "promoted",
                "previous_version": previous_version,
                "validation_metrics": validation_metrics,
                "timestamp": datetime.now().isoformat()
            })

            self._save_registry()

            self.logger.info(f"Model {version} promoted to production")

            return True

        except Exception as e:
            self.logger.error(f"Error promoting model: {e}")
            return False

    def rollback(self) -> Optional[str]:
        """
        Rollback to previous production model

        Returns:
            Previous version identifier or None
        """
        try:
            # Find last promotion event
            for event in reversed(self.registry["history"]):
                if event["action"] == "promoted" and event.get("previous_version"):
                    previous_version = event["previous_version"]

                    # Rollback
                    self.registry["current_version"] = previous_version
                    self.registry["models"][previous_version]["status"] = "production"
                    self.registry["history"].append({
                        "version": previous_version,
                        "action": "rollback",
                        "timestamp": datetime.now().isoformat()
                    })

                    self._save_registry()

                    self.logger.info(f"Rolled back to version {previous_version}")

                    return previous_version

            self.logger.warning("No previous version found for rollback")
            return None

        except Exception as e:
            self.logger.error(f"Error during rollback: {e}")
            return None

    def get_current_model(self) -> Optional[Dict]:
        """Get current production model info"""
        version = self.registry.get("current_version")
        if version:
            return self.registry["models"].get(version)
        return None

    def list_models(self, status: Optional[str] = None) -> List[Dict]:
        """
        List all models, optionally filtered by status

        Args:
            status: Filter by status (e.g., "production", "registered")

        Returns:
            List of model entries
        """
        models = list(self.registry["models"].values())

        if status:
            models = [m for m in models if m.get("status") == status]

        return models

    def verify_checksum(self, version: str) -> bool:
        """
        Verify model checksum matches registry

        Args:
            version: Version to verify

        Returns:
            True if checksum matches
        """
        try:
            model_info = self.registry["models"].get(version)
            if not model_info:
                return False

            model_path = model_info["path"]
            expected_checksum = model_info["checksum"]

            actual_checksum = self._calculate_checksum(model_path)

            if actual_checksum != expected_checksum:
                self.logger.error(
                    f"Checksum mismatch for {version}: "
                    f"expected {expected_checksum[:8]}..., got {actual_checksum[:8]}..."
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error verifying checksum: {e}")
            return False

    @staticmethod
    def _calculate_checksum(file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()
