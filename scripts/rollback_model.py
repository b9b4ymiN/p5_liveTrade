#!/usr/bin/env python3
"""
Model Rollback Script
Quick rollback to previous production model
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.model_registry import ModelRegistry
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Rollback to previous model')
    parser.add_argument('--execute', action='store_true',
                       help='Execute rollback (dry-run without this flag)')
    parser.add_argument('--registry-path', default='./models_saved',
                       help='Path to model registry')

    args = parser.parse_args()

    try:
        # Initialize registry
        registry = ModelRegistry(registry_path=args.registry_path)

        # Get current model
        current = registry.get_current_model()
        if not current:
            logger.error("No current production model found")
            return 1

        logger.info(f"Current model: {current['version']}")

        if not args.execute:
            logger.info("=" * 60)
            logger.info("DRY RUN - Use --execute to perform rollback")
            logger.info("=" * 60)

            # Show what would happen
            for event in reversed(registry.registry['history']):
                if event['action'] == 'promoted' and event.get('previous_version'):
                    prev_version = event['previous_version']
                    logger.info(f"Would rollback to: {prev_version}")

                    prev_model = registry.registry['models'].get(prev_version)
                    if prev_model:
                        logger.info(f"Previous model registered: {prev_model['registered_at']}")
                        logger.info(f"Checksum: {prev_model['checksum'][:16]}...")
                    break

            logger.info("=" * 60)
            return 0

        # Execute rollback
        logger.info("=" * 60)
        logger.info("EXECUTING ROLLBACK")
        logger.info("=" * 60)

        previous_version = registry.rollback()

        if previous_version:
            logger.info(f"✅ Rollback successful to {previous_version}")

            # Verify checksum
            logger.info("Verifying checksum...")
            if registry.verify_checksum(previous_version):
                logger.info("✅ Checksum verified")
            else:
                logger.error("❌ Checksum verification failed!")
                logger.error("Model file may be corrupted. Manual intervention required.")
                return 1

            logger.info("=" * 60)
            logger.info("ROLLBACK COMPLETE")
            logger.info("=" * 60)
            logger.info("Next steps:")
            logger.info("1. Restart trading bot")
            logger.info("2. Monitor logs for model loading")
            logger.info("3. Verify predictions are generated")
            logger.info("4. Watch dashboard for normal operation")

            return 0
        else:
            logger.error("❌ Rollback failed - no previous version found")
            logger.error("This may be the first model deployment.")
            logger.error("Manual model deployment required.")
            return 1

    except Exception as e:
        logger.error(f"❌ Rollback error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
