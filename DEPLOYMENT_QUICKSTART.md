# Phase 5 Deployment Quick Start Guide

## Prerequisites Checklist

- [ ] Binance Testnet account created
- [ ] API keys generated (Trading + Reading, NO withdrawals)
- [ ] IP allowlist configured on Binance
- [ ] Telegram bot created (via BotFather)
- [ ] Docker and Docker Compose installed
- [ ] VPS/server with minimum specs: 2 CPU, 4GB RAM, 20GB disk

---

## 5-Minute Deployment (Testnet)

### Step 1: Configure Environment (2 minutes)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required values in `.env`:
```bash
# Binance Testnet API
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_secret_here

# Telegram
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=your_chat_id

# Database
DB_PASSWORD=secure_password_here
```

### Step 2: Deploy Services (2 minutes)

```bash
# Start all services (bot, database, cache, dashboard)
docker-compose -f docker-compose.hardened.yml up -d

# Check all services are running
docker-compose ps

# Expected output:
# trading_bot_hardened       running (healthy)
# trading_db_hardened        running (healthy)
# trading_cache_hardened     running (healthy)
# trading_dashboard_hardened running
```

### Step 3: Verify Deployment (1 minute)

```bash
# Check bot logs
docker logs ai_trading_bot_hardened --tail 50

# Look for:
# ✓ "Connected to Binance WebSocket"
# ✓ "Models loaded successfully" OR "Using dummy models (paper trading mode)"
# ✓ "Trading bot started"

# Check health endpoints
curl http://localhost:8000/healthz
# Should return: {"status": "healthy"}

curl http://localhost:8000/metrics
# Should return: JSON with trading metrics

# Access dashboard
# Open browser: http://localhost:8501
```

---

## Monitoring & Operations

### Real-time Monitoring

**Streamlit Dashboard:**
```
http://localhost:8501
```
- Equity curve (auto-refresh every 30s)
- Recent trades
- Current position
- Risk metrics

**Telegram Alerts:**
- Trade entries/exits
- Circuit breaker triggers
- Error notifications
- Daily summaries

**Logs:**
```bash
# Follow bot logs
docker logs -f ai_trading_bot_hardened

# Check recent errors
docker logs ai_trading_bot_hardened 2>&1 | grep ERROR

# View specific service
docker logs trading_db_hardened
docker logs trading_cache_hardened
```

### Emergency Procedures

**Kill Switch - Immediate Halt:**
```bash
docker exec -it ai_trading_bot_hardened \
  python scripts/kill_switch.py \
  --mode immediate \
  --reason "Manual intervention required" \
  --confirm
```

**Kill Switch - Graceful Stop:**
```bash
docker exec -it ai_trading_bot_hardened \
  python scripts/kill_switch.py \
  --mode graceful \
  --reason "End of trading session"
```

**Kill Switch - Pause New Entries:**
```bash
docker exec -it ai_trading_bot_hardened \
  python scripts/kill_switch.py \
  --mode pause \
  --reason "High volatility event"
```

**Check Kill Switch Status:**
```bash
docker exec -it ai_trading_bot_hardened \
  python scripts/kill_switch.py --status
```

**Clear Kill Switch (Resume Trading):**
```bash
docker exec -it ai_trading_bot_hardened \
  python scripts/kill_switch.py --clear
```

### Model Rollback

**Dry-run (see what would happen):**
```bash
docker exec -it ai_trading_bot_hardened \
  python scripts/rollback_model.py
```

**Execute rollback:**
```bash
docker exec -it ai_trading_bot_hardened \
  python scripts/rollback_model.py --execute

# Then restart bot
docker-compose restart bot
```

---

## Paper Trading Validation (2-4 Weeks)

### Week 1-2: System Verification

Daily checklist:
- [ ] Check dashboard for trades
- [ ] Verify Telegram notifications working
- [ ] Review logs for errors
- [ ] Confirm position sizing matches configuration
- [ ] Validate circuit breakers (if triggered)

Expected behavior:
- Bot should trade conservatively (fractional Kelly 50%)
- Stop losses: ~1.5x ATR from entry
- Take profits: ~2:1 risk/reward
- Maximum hold: 4 hours (48 periods on 5m)

### Week 2-3: Risk Control Testing

Test scenarios:
- [ ] Trigger drawdown circuit breaker (if market allows)
- [ ] Test kill switch in all 3 modes
- [ ] Verify consecutive loss handling
- [ ] Monitor volatility spike detection
- [ ] Check latency monitoring

Manual tests:
```bash
# Manually trigger pause mode
docker exec -it ai_trading_bot_hardened \
  python scripts/kill_switch.py --mode pause --reason "Testing"

# Monitor bot behavior (should stop new entries only)
docker logs -f ai_trading_bot_hardened

# Clear and resume
docker exec -it ai_trading_bot_hardened \
  python scripts/kill_switch.py --clear
```

### Week 3-4: Performance Analysis

Metrics to track:
- Total trades
- Win rate
- Average R:R (should be close to 2:1)
- Maximum drawdown (should be < 3%)
- Sharpe ratio (target: > 1.5)
- Maximum consecutive losses (should be < 5)

Analysis:
```bash
# Review trade logs
docker exec -it ai_trading_bot_hardened \
  cat logs/trades.jsonl | tail -50

# Check database records
docker exec -it trading_db_hardened \
  psql -U trader -d trading -c "SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10;"
```

---

## Transition to Live Trading

⚠️ **ONLY after successful paper trading (minimum 2 weeks)**

### Pre-Live Checklist

- [ ] Paper trading completed (2-4 weeks)
- [ ] All circuit breakers tested and working
- [ ] Kill switch tested in all modes
- [ ] Performance meets expectations (Sharpe > 1.5, MDD < 3%)
- [ ] No critical errors in logs
- [ ] Stakeholder approval obtained
- [ ] 24/7 monitoring plan in place
- [ ] Incident response team identified

### Live Deployment Steps

1. **Create Mainnet API Keys:**
   - Binance → API Management → Create API Key
   - Enable: Futures Trading + Reading
   - **DISABLE: Withdrawals** (CRITICAL)
   - Set IP allowlist (VPS IP only)

2. **Update Environment:**
   ```bash
   # Edit .env
   nano .env
   
   # Change API keys to mainnet
   BINANCE_API_KEY=live_api_key
   BINANCE_API_SECRET=live_secret
   
   # Verify PAPER_TRADING=false (or remove line)
   ```

3. **Update Risk Configuration (Conservative Start):**
   ```bash
   # Edit config/risk_policy.yaml
   nano config/risk_policy.yaml
   
   # Reduce initial risk:
   position_sizing:
     risk_per_trade: 0.01  # 1% instead of 2%
     max_position_pct: 0.10  # 10% instead of 20%
   ```

4. **Redeploy:**
   ```bash
   docker-compose -f docker-compose.hardened.yml down
   docker-compose -f docker-compose.hardened.yml up -d
   ```

5. **Monitor Intensively:**
   - First 24 hours: Check every 2 hours
   - First week: Check every 6 hours
   - First month: Daily checks
   - Gradually reduce monitoring as confidence builds

---

## Troubleshooting

### Bot Not Starting

```bash
# Check logs
docker logs ai_trading_bot_hardened

# Common issues:
# 1. Invalid API keys → Check .env
# 2. IP not allowlisted → Add VPS IP to Binance
# 3. Missing dependencies → Rebuild container
docker-compose -f docker-compose.hardened.yml build --no-cache
```

### WebSocket Connection Issues

```bash
# Check network connectivity
docker exec -it ai_trading_bot_hardened ping api.binance.com

# Check firewall
sudo ufw status

# Allow outbound HTTPS
sudo ufw allow out 443/tcp
```

### Dashboard Not Loading

```bash
# Check Streamlit service
docker logs trading_dashboard_hardened

# Restart dashboard
docker-compose restart dashboard

# Access via localhost only
# URL: http://localhost:8501 (NOT external IP)
```

### Database Connection Errors

```bash
# Check PostgreSQL
docker exec -it trading_db_hardened pg_isready -U trader

# Reset database (CAUTION: deletes all data)
docker-compose down -v
docker-compose -f docker-compose.hardened.yml up -d
```

---

## Key Contacts & Resources

### Documentation
- Implementation: `docs/phase5_signoff.md`
- Kill Switch: `docs/kill_switch_runbook.md`
- Rollback: `docs/rollback_playbook.md`
- Security: `docs/security_controls.md`
- Incidents: `docs/incident_runbooks/`

### Emergency Procedures
- Credential leak: `docs/incident_runbooks/credential_leak.md`
- Exchange outage: `docs/incident_runbooks/exchange_outage.md`

### Support
- Binance Support: https://www.binance.com/en/support
- Binance Status: https://www.binancestatus.com

---

## Success Criteria

✅ **System is working correctly if:**
- Bot connects to Binance WebSocket without errors
- Trades are executed and logged
- Dashboard shows live updates
- Telegram notifications received
- Circuit breakers trigger at correct thresholds
- Kill switch works in all modes
- No critical errors in logs for 24+ hours

🚨 **Stop trading immediately if:**
- Repeated order execution failures
- Circuit breakers not triggering when they should
- Unexpected position sizes
- Kill switch not working
- Critical errors in logs
- Suspicious account activity

---

**Last Updated:** 2025-11-11
**Version:** 1.0
**Status:** Production Ready (Pending Paper Trading)
