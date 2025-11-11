# Incident Runbook: Exchange Outage

## Severity: P1 - HIGH

**Response Time:** <1 hour
**Escalation:** Trading Ops & Risk Manager

---

## Detection Indicators

- WebSocket disconnection (persistent)
- API calls returning 5xx errors
- Exchange status page showing issues
- Unable to place orders
- Order book data stale
- Abnormal latency spikes

---

## Immediate Response (0-15 minutes)

### Step 1: Verify Outage

```bash
# Check exchange status
curl -s https://api.binance.com/api/v3/ping
# Should return: {}

# Check futures API
curl -s https://fapi.binance.com/fapi/v1/ping
# Should return: {}

# If both fail, likely exchange issue

# Check official status page
curl -s https://www.binance.com/en/support/announcement

# Check social media
# Twitter: @binance
# Telegram: Binance Official
```

### Step 2: Assess Bot Status

```bash
# Check if bot detected outage
tail -n 50 logs/trading_bot.log | grep -i "connection\|error\|disconnect"

# Check current positions
python scripts/check_positions.py --source exchange

# Verify WebSocket status
python scripts/websocket_status.py
```

### Step 3: Determine Action

**Decision Matrix:**

| Situation | Action |
|-----------|--------|
| Minor outage (<5 min expected) | Pause new entries, monitor |
| Major outage (>5 min) | Close positions if possible, halt |
| Partial outage (API works, WS down) | Continue with REST API fallback |
| Can't access positions | URGENT: Manual intervention |

---

## Response Actions

### Scenario A: Minor Outage (Monitoring Mode)

```bash
# Pause new entries only
python scripts/kill_switch.py --mode pause --reason "Exchange outage monitoring"

# Enable aggressive monitoring
python scripts/monitor_exchange.py --interval 30 --alert

# Set alert for recovery
python scripts/alert_on_recovery.py --notify telegram
```

### Scenario B: Major Outage (Halt Trading)

```bash
# Graceful stop if possible
python scripts/kill_switch.py --mode graceful --reason "Exchange outage - major"

# If graceful stop times out (positions can't close):
# Switch to pause mode
python scripts/kill_switch.py --mode pause
```

### Scenario C: Emergency (Can't Access Positions)

```bash
# Attempt emergency position closure
python scripts/emergency_close_positions.py --all --retry 5

# If API completely unavailable:
# 1. Try exchange mobile app
# 2. Try exchange web UI
# 3. Contact exchange support immediately

# Document all actions
python scripts/log_emergency_action.py \
  --action "manual_position_closure" \
  --reason "exchange_outage" \
  --method "web_ui"
```

---

## Monitoring During Outage

### Continuous Checks

```bash
# Monitor exchange recovery
watch -n 30 'python scripts/check_exchange_health.py'

# Monitor open positions (if accessible)
watch -n 60 'python scripts/check_positions.py'

# Check for status updates
python scripts/monitor_exchange_status.py --follow
```

### Position Risk Assessment

```python
# Calculate liquidation risk
python scripts/calculate_liquidation_risk.py --current-positions

# If liquidation risk high:
# - Attempt to close via any available channel
# - Consider adding margin (if possible)
# - Contact exchange support
```

---

## Recovery Procedures

### Step 1: Verify Exchange Recovery

```bash
# Test API connectivity
python scripts/test_exchange_api.py --full-check

# Verify WebSocket
python scripts/test_websocket.py --duration 60

# Check order placement
python scripts/test_order_placement.py --testnet --small-order

# Verify data quality
python scripts/validate_data_feeds.py --duration 120
```

### Step 2: Reconcile Positions

```bash
# Compare bot state vs exchange
python scripts/reconcile_positions.py --source both

# If discrepancies found:
# - Log all discrepancies
# - Update bot state to match exchange
# - Investigate cause

# Document reconciliation
python scripts/log_reconciliation.py \
  --pre-outage-state pre_outage.json \
  --post-recovery-state post_recovery.json
```

### Step 3: Gradual Resumption

```bash
# Clear kill switch
python scripts/kill_switch.py --clear

# Resume with reduced size
# Edit config temporarily:
# position_sizing.max_position_pct: 0.10 (50% of normal)

# Restart bot
docker-compose restart bot

# Monitor closely for 1 hour
tail -f logs/trading_bot.log

# If stable, restore normal size after 1 hour
```

---

## Post-Outage Analysis

### Step 1: Impact Assessment

```python
# Calculate downtime
python scripts/calculate_outage_impact.py \
  --start "2024-01-15 14:00:00" \
  --end "2024-01-15 15:30:00"

# Output:
# - Total downtime: 90 minutes
# - Missed opportunities: X trades
# - Position impact: $Y unrealized change
# - System availability: 99.X%
```

### Step 2: Bot Behavior Analysis

```bash
# Review bot logs during outage
grep -A 5 -B 5 "connection" logs/trading_bot.log > outage_logs.txt

# Check if circuit breakers triggered correctly
python scripts/analyze_circuit_breakers.py --during-outage

# Verify fallback mechanisms worked
python scripts/verify_fallback_behavior.py --outage-period
```

### Step 3: Update Procedures

```markdown
## Outage Incident Report

**Date:** 2024-01-15
**Duration:** 90 minutes
**Type:** Exchange API outage

### What Happened
Binance experienced API issues affecting futures trading.

### Bot Response
- ✓ WebSocket disconnection detected
- ✓ Circuit breaker triggered (pause mode)
- ✓ No new positions opened
- ✓ Existing position managed manually
- ⚠️  Initial reconnection attempts slow

### Improvements Needed
1. Faster detection of outage vs network issue
2. Better fallback to REST API
3. Automated position monitoring during outage
4. Enhanced alerting

### Action Items
- [ ] Implement REST API fallback
- [ ] Add exchange status API monitoring
- [ ] Improve reconnection logic
- [ ] Test outage response procedures
```

---

## Exchange-Specific Procedures

### Binance Outage Response

#### Detection
- Monitor: https://api.binance.com/api/v3/systemStatus
- Status page: https://www.binancestatus.com
- Twitter: @binance
- Telegram: Binance English

#### Support Contact
- 24/7 Support: Via Binance website
- VIP Support: (if applicable)
- Emergency: cs@binance.com

#### Known Issues
- Scheduled maintenance (usually announced 24h ahead)
- Overload during high volatility
- DDoS attacks (rare)
- System upgrades

---

## Testing Outage Response

### Regular Testing (Monthly)

```bash
# Simulate outage in testnet
python scripts/simulate_exchange_outage.py --duration 300

# Verify bot behavior:
# [ ] Circuit breaker triggered
# [ ] Positions handled correctly
# [ ] Reconnection successful
# [ ] Monitoring alerts sent
```

---

## Contingency Plans

### Alternative Exchanges (Future)

If considering multi-exchange:
1. Maintain accounts on backup exchanges
2. Test order execution on alternates
3. Implement exchange abstraction layer
4. Document switching procedures

### Manual Trading Backup

```markdown
## Manual Trading Procedures

If bot must be disabled long-term:

1. Close all positions via exchange UI
2. Document final state
3. Disable API keys
4. Manual monitoring of markets
5. Plan for bot resumption
```

---

## Monitoring & Alerting

### Real-time Checks

```python
# Health check endpoints
GET /healthz
# Should include:
# - exchange_connection: true/false
# - websocket_status: connected/disconnected
# - last_data_received: timestamp
# - api_latency: milliseconds
```

### Alert Configuration

```yaml
# Prometheus alerts
- alert: ExchangeConnectionLost
  expr: exchange_connection_status == 0
  for: 1m
  annotations:
    summary: "Exchange connection lost"
    severity: "critical"

- alert: HighAPILatency
  expr: api_latency_p95 > 2000
  for: 5m
  annotations:
    summary: "High API latency detected"
    severity: "warning"
```

---

## Document Metadata

- **Version:** 1.0
- **Last Updated:** 2024-01-15
- **Tested:** Not yet tested in production
- **Next Review:** After any exchange outage incident
