# Model Rollback Playbook

## Quick Reference

**Rollback Command:**
```bash
python scripts/rollback_model.py --execute
```

**Estimated Time:** 2-5 minutes
**Risk Level:** LOW (reverting to previously validated model)

---

## When to Rollback

### Automatic Triggers
- Sharpe ratio drops below 1.0 for 24 hours
- Max drawdown exceeds 25%
- 10+ consecutive losses
- Critical model loading errors
- Checksum validation failures

### Manual Triggers
- Unusual trading behavior observed
- Excessive position sizing
- Systematic prediction errors
- Risk manager discretion

---

## Rollback Procedure

### Step 1: Assess Situation (2 minutes)

```bash
# Check current model status
python -c "
from models.model_registry import ModelRegistry
registry = ModelRegistry()
current = registry.get_current_model()
print(f'Current Model: {current[\"version\"]}')
print(f'Registered: {current[\"registered_at\"]}')
print(f'Checksum: {current[\"checksum\"][:8]}...')
"

# Check recent performance
tail -n 50 logs/trades.jsonl | grep '"type": "exit"'
```

**Decision Point:** Confirm rollback is necessary

---

### Step 2: Stop Trading Bot (1 minute)

```bash
# If running via Docker Compose
docker-compose stop bot

# If running directly
# Send SIGTERM to bot process (Ctrl+C or kill <PID>)
pkill -f "python main.py"
```

**Verify:** Bot is stopped and no orders are pending

```bash
# Check for open positions
python -c "
from execution.order_executor import OrderExecutor
import yaml

with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

executor = OrderExecutor(config['binance'])
position = executor.get_position(config['symbol'])
print(f'Open Position: {position}')
"
```

---

### Step 3: Execute Rollback (1 minute)

```bash
# Rollback to previous model version
python scripts/rollback_model.py --execute

# Expected output:
# [INFO] Current version: v2.1.0
# [INFO] Rolling back to: v2.0.0
# [INFO] Verifying checksum...
# [INFO] Checksum valid: a3f5d9b1...
# [INFO] Rollback complete
# [INFO] Current production model: v2.0.0
```

**Verify rollback:**
```bash
# Confirm new current version
python -c "
from models.model_registry import ModelRegistry
registry = ModelRegistry()
current = registry.get_current_model()
print(f'Current Model: {current[\"version\"]}')
"

# Should show previous version
```

---

### Step 4: Restart Bot (1 minute)

```bash
# If using Docker Compose
docker-compose start bot
docker-compose logs -f bot

# If running directly
python main.py
```

**Verify:** Bot reloads correct model

Check logs for:
```
Loading ML models...
Loading ensemble model from ./models_saved/ensemble_v2.0.0.pkl
Ensemble model loaded successfully
Loading RL agent from ./models_saved/rl_agent_v2.0.0.zip
RL agent loaded successfully
```

---

### Step 5: Monitor (15-30 minutes)

```bash
# Watch logs in real-time
tail -f logs/trading_bot.log

# Monitor dashboard
# Open http://localhost:8501

# Check Telegram alerts
# Should receive "Bot restarted" notification
```

**Key metrics to watch:**
- Model predictions are generating
- Risk checks are passing
- No immediate errors
- Positions are managed correctly

---

### Step 6: Post-Rollback Validation (1 hour)

```bash
# Check prediction distribution
python scripts/analyze_predictions.py --last-hour 1

# Verify model behavior
python scripts/model_diagnostics.py --version <rolled-back-version>

# Compare with pre-rollback behavior
# Should see return to normal prediction patterns
```

---

## Rollback Script

Create `scripts/rollback_model.py`:

```python
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Rollback to previous model')
    parser.add_argument('--execute', action='store_true',
                       help='Execute rollback (dry-run without this flag)')
    parser.add_argument('--registry-path', default='./models_saved',
                       help='Path to model registry')

    args = parser.parse_args()

    # Initialize registry
    registry = ModelRegistry(registry_path=args.registry_path)

    # Get current model
    current = registry.get_current_model()
    if not current:
        logger.error("No current production model found")
        return 1

    logger.info(f"Current model: {current['version']}")

    if not args.execute:
        logger.info("DRY RUN - Use --execute to perform rollback")

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

        return 0

    # Execute rollback
    logger.info("Executing rollback...")

    previous_version = registry.rollback()

    if previous_version:
        logger.info(f"✅ Rollback successful to {previous_version}")

        # Verify checksum
        if registry.verify_checksum(previous_version):
            logger.info("✅ Checksum verified")
        else:
            logger.error("❌ Checksum verification failed!")
            return 1

        return 0
    else:
        logger.error("❌ Rollback failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## Testing Rollback Procedure

**It is critical to test rollback BEFORE production deployment**

```bash
# Test 1: Register test models
python scripts/test_rollback.py --setup

# Test 2: Perform rollback
python scripts/rollback_model.py --execute

# Test 3: Verify bot can restart
python main.py --dry-run

# Test 4: Cleanup
python scripts/test_rollback.py --cleanup
```

---

## Rollback Checklist

### Pre-Rollback
- [ ] Confirm rollback is necessary
- [ ] Identify source of issue
- [ ] Check for open positions
- [ ] Notify team/stakeholders
- [ ] Document reason for rollback

### During Rollback
- [ ] Stop trading bot
- [ ] Execute rollback command
- [ ] Verify checksum
- [ ] Restart bot
- [ ] Confirm model loaded correctly

### Post-Rollback
- [ ] Monitor for 1 hour minimum
- [ ] Verify predictions returning to normal
- [ ] Check all safety mechanisms working
- [ ] Document incident
- [ ] Schedule post-mortem
- [ ] Plan fix for problematic model

---

## Common Issues

### Issue: "No previous version found"
**Cause:** First model deployment, no history
**Solution:** Cannot rollback. Deploy known-good model manually.

### Issue: "Checksum mismatch"
**Cause:** Model file corrupted
**Solution:** Restore from backup, redeploy validated model.

### Issue: Bot won't start after rollback
**Cause:** Model compatibility issue
**Solution:** Check logs, verify model format, ensure dependencies match.

### Issue: Predictions look wrong after rollback
**Cause:** Feature engineering mismatch
**Solution:** Verify feature engineer version matches rolled-back model.

---

## Emergency Contacts

- **Risk Manager:** [Contact]
- **MLOps On-Call:** [Contact]
- **Trading Ops:** [Contact]

---

## Rollback History Template

Document each rollback:

```markdown
## Rollback Incident: YYYY-MM-DD HH:MM

**From Version:** vX.Y.Z
**To Version:** vX.Y.Z-1
**Reason:** [Brief description]
**Triggered By:** [Auto/Manual]
**Duration:** [Minutes]
**Impact:** [Description of trading impact]
**Root Cause:** [Technical cause]
**Prevention:** [How to prevent in future]
**Status:** [Resolved/Monitoring/Under Investigation]
```

---

**Last Updated:** 2024-01-15
**Owner:** MLOps Team
**Review Frequency:** Quarterly or after each rollback
