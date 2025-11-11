# Incident Runbook: API Credential Leak

## Severity: P0 - CRITICAL

**Response Time:** <15 minutes
**Escalation:** Immediate to Security Team & Management

---

## Detection Indicators

- Unauthorized API access alerts
- Unusual trading patterns
- Trades from unknown IPs
- Exchange security notifications
- Suspicious withdrawals attempted
- API rate limit reached unexpectedly

---

## Immediate Response (0-5 minutes)

### Step 1: Kill Switch Activation

```bash
# Immediate halt of all trading
python scripts/kill_switch.py --mode immediate --reason "Credential leak suspected"

# Verify halt
python scripts/kill_switch.py --status
```

### Step 2: Disable Compromised API Keys

```bash
# On Binance (via UI or API):
# 1. Login to Binance account
# 2. Go to API Management
# 3. Delete or disable suspect API key IMMEDIATELY
# 4. Check "API History" for unauthorized usage

# Verify all trading activity stopped
# Check exchange UI for:
# - Open orders (cancel all)
# - Open positions (assess if need emergency close)
# - Recent trades (identify unauthorized)
```

### Step 3: Document Initial State

```bash
# Capture current system state
python scripts/capture_system_state.py --output /tmp/incident_state.json

# Review recent logs
tail -n 200 logs/trading_bot.log > /tmp/incident_logs.txt
grep "API" logs/trading_bot.log > /tmp/api_activity.txt

# Check audit log
cat logs/kill_switch_audit.log | tail -n 50
```

---

## Investigation (5-30 minutes)

### Step 4: Assess Damage

```python
# Check unauthorized trades
python scripts/analyze_trades.py --since "2024-01-15 14:00:00" --unauthorized

# Review API access logs
python scripts/analyze_api_access.py --suspicious

# Calculate financial impact
python scripts/calculate_incident_impact.py --type credential_leak
```

**Key Questions:**
- When did the leak occur?
- Which keys were compromised?
- What trades were made by attacker?
- Was any money moved/withdrawn?
- What is the financial damage?
- Are other systems affected?

### Step 5: Identify Breach Vector

**Common Vectors:**

1. **Code Repository Exposure**
   ```bash
   # Check if .env was committed to git
   git log --all --full-history --source -- .env
   git log --all --grep="API_KEY"

   # Check GitHub (if applicable)
   # Search: "BINANCE_API_KEY" site:github.com yourusername
   ```

2. **Phishing/Social Engineering**
   - Review recent emails
   - Check team communication channels
   - Verify no unauthorized access to systems

3. **Malware/Keylogger**
   ```bash
   # Scan system
   sudo clamscan -r /home/user

   # Check for suspicious processes
   ps aux | grep -E "keylog|backdoor"

   # Review cron jobs
   crontab -l
   sudo cat /etc/crontab
   ```

4. **Insecure Storage**
   - Check if .env files were backed up to insecure locations
   - Review cloud storage (Dropbox, Google Drive, etc.)
   - Check Slack/Discord history for shared credentials

5. **Third-party Breach**
   - Check if credentials stored in third-party services
   - Review access to password managers
   - Check monitoring/logging services

---

## Containment (30-60 minutes)

### Step 6: Rotate All Credentials

```bash
# 1. Create new Binance API key
# Via Binance UI:
# - Generate new API key
# - Set IP whitelist (VPS only)
# - Enable Futures Trading ONLY
# - DISABLE withdrawals
# - Save securely

# 2. Update bot configuration
# Edit .env (or Docker secret)
BINANCE_API_KEY=NEW_KEY_HERE
BINANCE_API_SECRET=NEW_SECRET_HERE

# 3. Rotate other credentials
# - Telegram bot token (BotFather)
# - Database passwords
# - SSH keys
# - Any other shared secrets

# 4. Verify new credentials
python scripts/test_api_key.py --testnet
```

### Step 7: Secure Environment

```bash
# Update firewall rules
sudo ufw deny from ANY to any
sudo ufw allow from YOUR_IP_ONLY to any port 22
sudo ufw allow from VPS_IP to any
sudo ufw enable

# Review SSH access
sudo lastlog
sudo last -a

# Check for backdoors
sudo find /home -name "*.sh" -mtime -7
sudo find /tmp -type f -executable
```

### Step 8: Review Code & Configuration

```bash
# Scan for hardcoded secrets
grep -r "sk-" .
grep -r "API_KEY" . --exclude-dir=.git
grep -r "password" . --exclude-dir=.git

# Check .gitignore
cat .gitignore | grep -E "\.env|secret|password"

# Verify .env is NOT in git
git check-ignore .env
# Should output: .env
```

---

## Recovery (1-4 hours)

### Step 9: Clean System Rebuild (if malware suspected)

```bash
# Backup essential data
tar -czf /tmp/bot_backup.tar.gz \
  logs/ models_saved/ config/ --exclude=.env

# Clean reinstall
# 1. Provision new VPS
# 2. Deploy from clean repository
# 3. Use NEW credentials
# 4. Verify no backdoors

# Or container rebuild
docker-compose down
docker system prune -a --volumes
# Rebuild from Dockerfile
docker-compose up -d --build
```

### Step 10: Enhanced Security Implementation

```bash
# 1. Enable Docker secrets
echo "NEW_API_KEY" | docker secret create binance_api_key -

# 2. Implement Vault (if not using)
# See security_controls.md section D1

# 3. Enable 2FA on all accounts
# - Binance account
# - GitHub
# - VPS provider
# - All team accounts

# 4. Setup intrusion detection
sudo apt install aide
sudo aide --init
```

### Step 11: Verify System Integrity

```bash
# Check all components
python scripts/full_system_check.py

# Verify:
# [ ] New API keys working
# [ ] Old keys deleted from exchange
# [ ] No unauthorized access
# [ ] All services healthy
# [ ] Monitoring active
# [ ] Audit logging enabled
```

---

## Post-Incident (24-48 hours)

### Step 12: Complete Incident Report

```markdown
## Credential Leak Incident Report

**Incident ID:** INC-2024-001
**Date/Time:** 2024-01-15 14:30 UTC
**Severity:** P0 - Critical
**Status:** Resolved

### Timeline
- 14:30 - Suspicious activity detected
- 14:32 - Kill switch activated
- 14:35 - API keys disabled
- 14:45 - Root cause identified: .env file in public repo
- 15:15 - New credentials generated
- 16:00 - System verified secure
- 16:30 - Trading resumed (with monitoring)

### Impact
- Financial: $X lost/at risk
- Downtime: 2 hours
- Positions affected: 1 open position (closed safely)
- Customer impact: None (internal system)

### Root Cause
[Detailed description of how credentials were leaked]

### Corrective Actions Taken
1. Old API keys deleted
2. New keys generated with stricter permissions
3. .env file removed from git history
4. .gitignore updated and verified
5. Docker secrets implemented
6. Team security training scheduled

### Preventive Measures
1. Implement git pre-commit hooks (prevent .env commits)
2. Enable secret scanning on GitHub
3. Move to HashiCorp Vault for secrets
4. Regular security audits (monthly)
5. Automated secret rotation (90 days)

### Lessons Learned
- [Key takeaways]
- [What went well]
- [What could be improved]
```

### Step 13: Team Communication

```markdown
## Security Incident Notification

**To:** All team members, management
**Subject:** Security Incident - Credential Leak - RESOLVED

We experienced a security incident involving compromised API credentials.

**What Happened:**
Brief summary of the incident.

**Impact:**
- Trading was halted for 2 hours
- No customer data affected
- Financial impact: $X

**Actions Taken:**
- Immediate response activated
- All credentials rotated
- Enhanced security implemented

**Going Forward:**
- Additional security measures
- Team training scheduled
- Monitoring enhanced

Questions? Contact: security@example.com
```

### Step 14: Regulatory Reporting (if required)

- Check local regulations for breach reporting requirements
- Document all evidence
- Prepare for potential audits
- Consult legal counsel if needed

---

## Prevention Checklist

### Immediate
- [ ] Remove all .env files from git history
- [ ] Add pre-commit hooks
- [ ] Enable GitHub secret scanning
- [ ] Implement Docker secrets
- [ ] Enable 2FA everywhere

### Short-term (1 week)
- [ ] Deploy Vault for secrets management
- [ ] Setup automated secret rotation
- [ ] Implement AIDE file integrity monitoring
- [ ] Enable API access alerting
- [ ] Conduct team security training

### Long-term (1 month)
- [ ] Regular security audits
- [ ] Quarterly penetration testing
- [ ] Implement SIEM
- [ ] Enhanced monitoring
- [ ] Incident response drills

---

## Tools & Scripts

```bash
# Analyze API usage
scripts/analyze_api_access.py --suspicious

# Check for leaked credentials
scripts/check_leaked_creds.py

# System health verification
scripts/full_system_check.py

# Generate incident report
scripts/create_incident_report.py --type credential_leak
```

---

## Contact Information

| Role | Contact | Emergency |
|------|---------|-----------|
| Security Lead | | |
| Risk Manager | | |
| System Admin | | |
| Exchange Support | | Binance 24/7 Support |

---

**Document Version:** 1.0
**Last Updated:** 2024-01-15
**Next Review:** After any credential leak incident
