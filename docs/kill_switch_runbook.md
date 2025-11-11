# Manual Kill Switch Runbook

## 🚨 Emergency Kill Switch Procedures

**Purpose:** Immediately halt trading activity in emergency situations

**Authority:** Risk Manager, Trading Ops Lead, System Administrators

**Activation Time:** <2 minutes

---

## Quick Actions

### IMMEDIATE KILL (Emergency)

```bash
# Method 1: Via Python API
python scripts/kill_switch.py --mode immediate --reason "Emergency stop"

# Method 2: Stop container
docker-compose stop bot

# Method 3: Emergency shutdown file
touch /tmp/EMERGENCY_KILL_SWITCH

# Method 4: Process kill
pkill -f "python main.py"
```

### GRACEFUL STOP (Planned)

```bash
# Allow positions to close at targets
python scripts/kill_switch.py --mode graceful --reason "Planned maintenance"
```

### PAUSE ONLY (Temporary)

```bash
# Stop new entries, keep existing positions
python scripts/kill_switch.py --mode pause --reason "Investigating anomaly"
```

---

## When to Activate Kill Switch

### Automatic Triggers (Already Handled by Circuit Breakers)
- ✓ Daily loss ≥ 3%
- ✓ 5+ consecutive losses
- ✓ Liquidation risk
- ✓ System health critical

### Manual Triggers (Requires Kill Switch)

#### 🔴 IMMEDIATE ACTIVATION REQUIRED

1. **Suspected Security Breach**
   - Unauthorized API access detected
   - Unusual trade patterns
   - Credentials potentially compromised

2. **Exchange Issues**
   - Binance system-wide outage
   - Known exchange bug affecting trades
   - Position discrepancies with exchange

3. **Model Malfunction**
   - Predictions showing extreme bias
   - All signals in one direction
   - Confidence scores invalid

4. **Data Feed Issues**
   - Stale data being used for decisions
   - WebSocket disconnected for >60 seconds
   - Price feed showing impossible values

5. **Uncontrolled Losses**
   - Losses exceeding all circuit breaker limits
   - Flash crash scenario
   - Liquidation imminent

#### 🟡 GRACEFUL STOP SCENARIOS

1. **Planned Maintenance**
   - System upgrades
   - Model deployment
   - Configuration changes

2. **End of Trading Period**
   - Close positions before weekend
   - End of testing phase
   - Regulatory requirements

3. **Market Conditions**
   - Extreme volatility
   - Low liquidity periods
   - Major news events

#### 🟢 PAUSE-ONLY SCENARIOS

1. **Investigation**
   - Unusual performance needs review
   - Model behavior verification
   - Data quality check

2. **Temporary Conditions**
   - Exchange maintenance window
   - High spread environment
   - System resource constraints

---

## Kill Switch Activation Procedure

### Step 1: Assess Situation (30 seconds)

```bash
# Check system status
python scripts/system_status.py

# Check current positions
python scripts/check_positions.py

# Check recent trades
tail -n 20 logs/trades.jsonl
```

**Decision Point:**
- Immediate stop needed? → Use IMMEDIATE mode
- Can close positions gracefully? → Use GRACEFUL mode
- Just pause new entries? → Use PAUSE mode

---

### Step 2: Activate Kill Switch (30 seconds)

#### Via Script (Recommended)

```bash
cd /home/user/p5_liveTrade

# Immediate stop
python scripts/kill_switch.py \
  --mode immediate \
  --reason "Security breach suspected" \
  --auth-token YOUR_TOKEN

# Expected output:
# [KILL SWITCH] Activating immediate mode
# [KILL SWITCH] Closing all positions...
# [KILL SWITCH] Halting trading bot...
# [KILL SWITCH] Audit log created: logs/kill_switch_audit.log
# [KILL SWITCH] Status: TRADING HALTED
```

#### Via Emergency File

```bash
# Creates immediate stop signal
touch /tmp/EMERGENCY_KILL_SWITCH

# Bot checks for this file every loop iteration
# and immediately halts when detected
```

#### Via Docker

```bash
# Stop bot container
docker-compose stop bot

# Verify stopped
docker-compose ps

# Check if positions remain open (manual close may be needed)
docker-compose run --rm bot python scripts/check_positions.py
```

---

### Step 3: Verify Halt (30 seconds)

```bash
# Check bot status
ps aux | grep "python main.py"
# Should show no running process

# Check Docker status
docker-compose ps bot
# Should show "Exited" or not running

# Verify no open positions
python scripts/check_positions.py --exchange binance

# Check audit log
tail -n 10 logs/kill_switch_audit.log
```

**Verification Checklist:**
- [ ] Bot process not running
- [ ] All positions closed (or closing)
- [ ] No pending orders
- [ ] Kill switch logged and notified
- [ ] Stakeholders notified (if needed)

---

### Step 4: Immediate Follow-up (5 minutes)

```bash
# Secure the system
# 1. Backup current state
./scripts/backup_system_state.sh

# 2. Review logs for root cause
tail -n 100 logs/trading_bot.log > /tmp/incident_logs.txt

# 3. Document incident
python scripts/create_incident_report.py \
  --type kill_switch \
  --reason "Your reason" \
  --output docs/incidents/
```

---

## Post-Kill Switch Actions

### Immediate Actions (Within 15 minutes)

1. **Document Incident**
   ```markdown
   ## Kill Switch Incident Report

   **Date/Time:** YYYY-MM-DD HH:MM:SS UTC
   **Activated By:** [Name/Role]
   **Mode:** [Immediate/Graceful/Pause]
   **Reason:** [Detailed reason]
   **Open Positions at Time:** [Count/Details]
   **Estimated Impact:** [PnL, positions closed]
   **Root Cause:** [If known]
   ```

2. **Notify Stakeholders**
   - Risk Manager
   - Trading Operations
   - Project Lead
   - Compliance (if regulatory issue)

3. **Secure Environment**
   - Change API keys if security issue
   - Review access logs
   - Check for unauthorized changes

### Short-term Actions (Within 1 hour)

4. **Root Cause Analysis**
   - Review system logs
   - Check data feeds
   - Analyze recent trades
   - Verify model outputs
   - Check system resources

5. **Fix/Mitigation**
   - Address immediate cause
   - Implement temporary safeguards
   - Update configurations if needed

6. **Testing**
   - Verify fix in test environment
   - Run diagnostic checks
   - Confirm data feeds healthy
   - Validate model outputs

### Before Resuming (Complete Checklist)

```bash
# Pre-resumption checklist
python scripts/pre_resume_checklist.py

# Will verify:
# [ ] Root cause identified and documented
# [ ] Fix implemented and tested
# [ ] System health checks pass
# [ ] All circuit breakers reset
# [ ] Risk limits validated
# [ ] Data feeds operational
# [ ] Models functioning correctly
# [ ] No pending issues
# [ ] Stakeholders notified of resumption plan
# [ ] Post-incident review scheduled
```

---

## Kill Switch Modes Explained

### Mode 1: IMMEDIATE

**Behavior:**
1. Immediately stop all trading logic
2. Close all open positions at market (aggressive)
3. Cancel all pending orders
4. Halt bot process
5. Block restart until manual override

**Use Cases:**
- Security breaches
- Critical model failures
- Exchange emergencies
- Uncontrolled losses

**Recovery Time:** Manual review required (typically 1-4 hours)

### Mode 2: GRACEFUL

**Behavior:**
1. Stop accepting new signals
2. Allow existing positions to reach TP/SL
3. Close positions that don't hit targets within timeout (30 minutes)
4. Halt bot after all positions closed
5. Log final state

**Use Cases:**
- Planned maintenance
- Model deployment
- End of trading session

**Recovery Time:** 30 minutes to 2 hours

### Mode 3: PAUSE

**Behavior:**
1. Stop new entry signals
2. Continue managing existing positions
3. Allow exits at targets or stops
4. Monitoring continues
5. Can resume without restart

**Use Cases:**
- Temporary investigations
- Data quality checks
- High volatility pause
- Exchange maintenance windows

**Recovery Time:** Minutes to hours (no restart needed)

---

## Resumption Procedure

### Pre-Checks

```bash
# 1. System health
python scripts/system_health_check.py --full

# 2. Exchange connectivity
python scripts/test_exchange_connection.py

# 3. Data feed quality
python scripts/validate_data_feeds.py --duration 60

# 4. Model validation
python scripts/validate_models.py --checksum --inference-test

# 5. Risk limits
python scripts/verify_risk_limits.py
```

### Resume Trading

```bash
# Clear kill switch
python scripts/kill_switch.py --clear --auth-token YOUR_TOKEN

# Start bot
docker-compose start bot

# Or manually
python main.py

# Monitor closely
tail -f logs/trading_bot.log
```

### Post-Resumption Monitoring (First 2 Hours)

- Monitor every trade
- Watch for abnormal behavior
- Verify predictions reasonable
- Check execution quality
- Monitor system resources
- Be ready to re-activate kill switch if needed

---

## Authentication & Authorization

### Required Authentication

```python
# In production, require authenticated kill switch
# Option 1: Auth token
python scripts/kill_switch.py --mode immediate --auth-token TOKEN

# Option 2: Two-factor confirmation
python scripts/kill_switch.py --mode immediate --confirm --2fa CODE

# Option 3: Multi-party authorization
python scripts/kill_switch.py --mode immediate --approvers "alice,bob"
```

### Authorized Personnel

| Role | Immediate | Graceful | Pause |
|------|-----------|----------|-------|
| Risk Manager | ✅ | ✅ | ✅ |
| Trading Ops Lead | ✅ | ✅ | ✅ |
| System Admin | ✅ | ✅ | ✅ |
| On-Call Engineer | ✅ | ✅ | ✅ |
| Quant Analyst | ❌ | ✅ | ✅ |
| Junior Staff | ❌ | ❌ | ✅ |

---

## Audit Log Format

Every kill switch activation is logged:

```json
{
  "timestamp": "2024-01-15T14:30:00Z",
  "action": "kill_switch_activated",
  "mode": "immediate",
  "activated_by": "risk_manager",
  "reason": "Daily loss limit exceeded",
  "open_positions": 1,
  "positions_closed": 1,
  "estimated_impact": -150.50,
  "system_state": {
    "equity": 1850.00,
    "daily_pnl": -150.00,
    "positions": []
  },
  "auth_method": "token",
  "ip_address": "10.0.0.5",
  "cleared_at": null,
  "cleared_by": null
}
```

---

## Testing Kill Switch

**IMPORTANT:** Test kill switch regularly in non-production environment

```bash
# Test immediate mode (testnet)
python scripts/kill_switch.py --mode immediate --reason "Testing" --testnet

# Test graceful mode
python scripts/kill_switch.py --mode graceful --reason "Testing" --testnet

# Test pause mode
python scripts/kill_switch.py --mode pause --reason "Testing" --testnet

# Verify audit logging
cat logs/kill_switch_audit.log
```

**Testing Schedule:**
- Monthly in testnet
- Before major deployments
- After significant code changes
- During incident response drills

---

## Common Issues & Solutions

### Issue: Kill switch activated but bot still trading

**Solution:**
```bash
# Force kill process
pkill -9 -f "python main.py"

# Remove stale locks
rm -f /tmp/trading_bot.lock

# Close positions via exchange UI
# (Manual intervention required)
```

### Issue: Positions not closing

**Solution:**
```bash
# Manual position closure
python scripts/emergency_close_positions.py --all --force

# If that fails, use exchange web interface
```

### Issue: Can't clear kill switch

**Solution:**
```bash
# Check for emergency file
rm -f /tmp/EMERGENCY_KILL_SWITCH

# Force clear in database
python scripts/kill_switch.py --force-clear --auth-token TOKEN

# Verify cleared
python scripts/kill_switch.py --status
```

---

## Emergency Contacts

| Role | Contact | Primary | Backup |
|------|---------|---------|--------|
| Risk Manager | | [Contact] | [Contact] |
| Trading Ops | | [Contact] | [Contact] |
| System Admin | | [Contact] | [Contact] |
| On-Call Engineer | | [Contact] | [Contact] |

**Escalation Path:**
1. On-Call Engineer (0-5 minutes)
2. Trading Ops Lead (5-15 minutes)
3. Risk Manager (15-30 minutes)
4. Project Lead (30+ minutes)

---

## Appendix: Kill Switch Script

See: `scripts/kill_switch.py` for implementation

---

**Document Version:** 1.0
**Last Updated:** 2024-01-15
**Next Review:** Monthly
**Owner:** Risk Management & Trading Ops
