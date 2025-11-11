# Security Controls Documentation

## D1. Secrets & Access Management

### Overview

This document defines security controls, access policies, and secrets management for the AI Trading Bot system.

---

## 1. Secrets Management (D1.1)

### Current Implementation

#### Environment Variables (.env)
```bash
# .env file (NEVER commit to git)
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
DB_PASSWORD=your_db_password
```

**⚠️ Current Limitation:** Using .env files. Not production-grade.

### Recommended: Docker Secrets (Production)

#### Setup Docker Secrets

```bash
# Create secrets
echo "your_binance_api_key" | docker secret create binance_api_key -
echo "your_binance_api_secret" | docker secret create binance_api_secret -
echo "your_telegram_token" | docker secret create telegram_token -
echo "your_db_password" | docker secret create db_password -

# List secrets
docker secret ls
```

#### Update docker-compose.yml

```yaml
services:
  bot:
    secrets:
      - binance_api_key
      - binance_api_secret
      - telegram_token
      - db_password

secrets:
  binance_api_key:
    external: true
  binance_api_secret:
    external: true
  telegram_token:
    external: true
  db_password:
    external: true
```

#### Access in Code

```python
# Read from Docker secret
def read_secret(secret_name):
    secret_path = f'/run/secrets/{secret_name}'
    if os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            return f.read().strip()
    return os.getenv(secret_name)  # Fallback to env var
```

### Alternative: HashiCorp Vault (Enterprise)

#### Vault Setup

```bash
# Install Vault
docker run -d --name=vault -p 8200:8200 vault:latest

# Initialize Vault
docker exec -it vault vault operator init

# Unseal Vault (use unseal keys from init)
docker exec -it vault vault operator unseal

# Login
docker exec -it vault vault login
```

#### Store Secrets

```bash
# Store trading secrets
vault kv put secret/trading \
  binance_api_key="xxx" \
  binance_api_secret="xxx" \
  telegram_token="xxx"

# Read secrets
vault kv get secret/trading
```

#### Integration

```python
import hvac

# Connect to Vault
client = hvac.Client(url='http://127.0.0.1:8200')
client.token = os.getenv('VAULT_TOKEN')

# Read secrets
secrets = client.secrets.kv.v2.read_secret_version(path='trading')
api_key = secrets['data']['data']['binance_api_key']
```

---

## 2. Key Rotation Policy (D1.2)

### Rotation Schedule

| Secret | Rotation Frequency | Method |
|--------|-------------------|--------|
| API Keys | 90 days | Manual (Binance UI) |
| Telegram Token | 180 days | Manual (BotFather) |
| Database Password | 90 days | Automated script |
| Docker Secrets | With API keys | Docker secret update |

### API Key Rotation Procedure

#### Step 1: Create New API Key

```bash
# On Binance:
# 1. Go to API Management
# 2. Create new API key
# 3. Set permissions: Enable Futures Trading, Disable Withdrawals
# 4. IP Whitelist: Add your VPS IP
# 5. Save new key securely
```

#### Step 2: Test New Key

```bash
# Test in isolated environment
python scripts/test_api_key.py \
  --api-key NEW_KEY \
  --api-secret NEW_SECRET \
  --testnet

# Verify permissions
python scripts/verify_api_permissions.py --api-key NEW_KEY
```

#### Step 3: Rotate in Production

```bash
# Method 1: Update Docker secret
echo "NEW_KEY" | docker secret create binance_api_key_v2 -
docker service update \
  --secret-rm binance_api_key \
  --secret-add binance_api_key_v2 \
  trading_bot

# Method 2: Update .env and restart
# Edit .env file with new key
docker-compose restart bot

# Method 3: Vault rotation
vault kv put secret/trading binance_api_key="NEW_KEY"
```

#### Step 4: Verify & Cleanup

```bash
# Verify bot is running with new key
docker-compose logs bot | grep "API key"

# Wait 24 hours, then delete old key from Binance
# This allows time to rollback if issues arise
```

---

## 3. IP Allowlist & API Permissions (D1.3)

### Binance API Key Configuration

**Required Settings:**

```
✓ Enable Reading
✓ Enable Futures Trading
✗ Enable Spot & Margin Trading (disabled)
✗ Enable Withdrawals (DISABLED - CRITICAL)
✗ Enable Universal Transfer (disabled)

IP Restrictions:
✓ Restrict access to trusted IPs
✓ Add VPS IP address
✓ Add office IP (for monitoring)
```

### IP Allowlist Management

```bash
# Get current VPS IP
curl -s https://api.ipify.org

# Add to Binance API key restrictions
# Via Binance UI: API Management > Edit > IP Restrictions

# Verify IP restriction
python scripts/test_api_from_unauthorized_ip.py
# Should fail with 403 Forbidden
```

### Firewall Rules (VPS)

```bash
# UFW firewall configuration
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (from specific IP only)
sudo ufw allow from YOUR_OFFICE_IP to any port 22

# Allow Dashboard (from specific IP only)
sudo ufw allow from YOUR_OFFICE_IP to any port 8501

# Allow Health API (from monitoring system)
sudo ufw allow from MONITORING_IP to any port 8000

# Enable firewall
sudo ufw enable
```

---

## 4. Role-Based Access Control (D1.4)

### Access Levels

| Role | Permissions | Justification |
|------|-------------|---------------|
| **System Admin** | Full access, API key rotation, Docker secrets | System maintenance |
| **Risk Manager** | Kill switch, risk parameters, monitoring | Risk oversight |
| **Trading Ops** | Restart bot, view logs, dashboard access | Operations |
| **Quant Analyst** | View-only logs, dashboard, model registry | Analysis |
| **Auditor** | Read-only access to logs and audit trails | Compliance |

### Linux User Permissions

```bash
# Create dedicated trading user (no root)
sudo useradd -m -s /bin/bash trading
sudo usermod -aG docker trading

# Set directory permissions
sudo chown -R trading:trading /home/user/p5_liveTrade
chmod 700 /home/user/p5_liveTrade/config
chmod 600 /home/user/p5_liveTrade/.env

# API keys should be 600 (read/write owner only)
chmod 600 /home/user/p5_liveTrade/.env
```

### SSH Access Control

```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers trading ops_user

# Restart SSH
sudo systemctl restart sshd
```

---

## D2. Network & Container Security

### 1. TLS/HTTPS Everywhere (D2.1)

#### External Communications

- ✅ Binance API: HTTPS (enforced by exchange)
- ✅ Telegram API: HTTPS (enforced by Telegram)
- ⚠️ Dashboard: HTTP (should be behind reverse proxy)

#### Recommended: Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/trading-dashboard
server {
    listen 443 ssl http2;
    server_name dashboard.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Authentication
        auth_basic "Trading Dashboard";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

#### Generate Let's Encrypt Certificate

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d dashboard.yourdomain.com

# Auto-renewal (crontab)
0 0 1 * * certbot renew --quiet
```

### 2. Container Hardening (D2.2)

#### Hardened Dockerfile

See: `Dockerfile.hardened` (created below)

**Key Changes:**
- Non-root user
- Read-only root filesystem
- Security scanning
- Minimal base image
- No unnecessary packages

#### Security Best Practices

```dockerfile
# Use specific version tags (not latest)
FROM python:3.10.12-slim

# Create non-root user
RUN useradd -m -u 1000 trading && \
    mkdir -p /app/logs /app/models_saved && \
    chown -R trading:trading /app

# Switch to non-root user
USER trading

# Read-only root filesystem
# (writable volumes mounted for logs and models)

# Drop capabilities
# (handled in docker-compose.yml)
```

#### docker-compose.yml Security

```yaml
services:
  bot:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - ./logs:/app/logs:rw
      - ./models_saved:/app/models_saved:ro
```

### 3. Image Scanning (D2.3)

#### Scan with Trivy

```bash
# Install Trivy
sudo apt install trivy

# Scan image for vulnerabilities
trivy image ai_trading_bot:latest

# Fail on critical CVEs
trivy image --severity CRITICAL --exit-code 1 ai_trading_bot:latest
```

#### Scan with Snyk

```bash
# Install Snyk
npm install -g snyk

# Authenticate
snyk auth

# Test container
snyk container test ai_trading_bot:latest
```

#### CI/CD Integration

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build image
        run: docker build -t ai_trading_bot:${{ github.sha }} .

      - name: Run Trivy scan
        run: trivy image --severity HIGH,CRITICAL ai_trading_bot:${{ github.sha }}

      - name: SBOM generation
        run: syft ai_trading_bot:${{ github.sha }} -o spdx > sbom.spdx
```

---

## D3. Auditing & Incident Response

### 1. Audit Logging (D3.1)

#### What to Audit

| Event Type | Logged Data | Retention |
|------------|-------------|-----------|
| API key usage | Timestamp, operation, result | 1 year |
| Configuration changes | Before/after, who, when | 1 year |
| Manual overrides | User, action, reason | 1 year |
| Kill switch activations | Mode, reason, outcome | Permanent |
| Access attempts | IP, user, success/failure | 90 days |
| Trade executions | All trade details | 7 years (regulatory) |

#### Audit Log Format

```json
{
  "timestamp": "2024-01-15T14:30:00Z",
  "event_type": "api_key_rotated",
  "actor": "admin_user",
  "ip_address": "10.0.0.5",
  "action": "binance_api_key_update",
  "old_key_id": "xxx...xxx",
  "new_key_id": "yyy...yyy",
  "success": true,
  "reason": "scheduled_rotation"
}
```

#### Implementation

```python
# audit_logger.py
import json
import logging
from datetime import datetime

class AuditLogger:
    def __init__(self, log_file='logs/audit.log'):
        self.log_file = log_file

    def log_event(self, event_type, actor, action, **kwargs):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'actor': actor,
            'action': action,
            **kwargs
        }

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
```

### 2. Incident Response Runbooks (D3.2)

See `/docs/incident_runbooks/` directory for:

1. **credential_leak.md** - API key compromise response
2. **exchange_outage.md** - Exchange downtime procedures
3. **order_mismatch.md** - Position reconciliation
4. **model_failure.md** - Model malfunction response
5. **data_quality.md** - Bad data detection and handling

### 3. Security Incident Response Plan

#### Severity Levels

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| **P0 - Critical** | Active security breach | <15 minutes | Immediate |
| **P1 - High** | Suspected compromise | <1 hour | Senior team |
| **P2 - Medium** | Security anomaly | <4 hours | On-call |
| **P3 - Low** | Policy violation | <24 hours | Next day |

#### Response Procedure

```markdown
## P0 - Critical Security Incident

1. **Immediate Actions (0-5 minutes)**
   - Activate kill switch (immediate mode)
   - Disable API keys on exchange
   - Isolate affected systems

2. **Investigation (5-30 minutes)**
   - Review audit logs
   - Check access logs
   - Identify breach vector
   - Assess damage

3. **Containment (30-60 minutes)**
   - Rotate all credentials
   - Update firewall rules
   - Deploy patches
   - Document findings

4. **Recovery (1-4 hours)**
   - Restore from clean backup
   - Verify system integrity
   - Re-enable with new credentials
   - Monitor closely

5. **Post-Incident (24-48 hours)**
   - Complete incident report
   - Conduct post-mortem
   - Update procedures
   - Communicate to stakeholders
```

---

## Security Checklist

### Pre-Deployment

- [ ] API keys have IP restrictions
- [ ] Withdrawals disabled on API keys
- [ ] Docker secrets configured (or Vault)
- [ ] Firewall rules configured
- [ ] SSH hardened (key-only, no root)
- [ ] TLS/HTTPS for dashboard
- [ ] Non-root container user
- [ ] Image scanned for CVEs
- [ ] Audit logging enabled
- [ ] Incident runbooks prepared

### Production Hardening

- [ ] Read-only root filesystem
- [ ] Dropped container capabilities
- [ ] Resource limits set
- [ ] Log aggregation configured
- [ ] SIEM integration (optional)
- [ ] Intrusion detection (optional)
- [ ] Backup & DR procedures tested
- [ ] Security monitoring alerts configured

### Ongoing Operations

- [ ] Monthly security reviews
- [ ] Quarterly key rotations
- [ ] Weekly vulnerability scans
- [ ] Daily audit log reviews
- [ ] Incident response drills (quarterly)
- [ ] Access control audits
- [ ] Dependency updates
- [ ] Security patch management

---

## Compliance & Regulatory

### Data Retention

| Data Type | Retention Period | Justification |
|-----------|-----------------|---------------|
| Trade records | 7 years | Regulatory requirement |
| Audit logs | 1 year minimum | Security best practice |
| System logs | 90 days | Operational needs |
| Model artifacts | 3 years | Reproducibility |
| Configuration history | 1 year | Change tracking |

### Geographic Considerations

- GDPR compliance (if EU users/data)
- Data residency requirements
- Cross-border data transfer restrictions
- Financial regulations (varies by jurisdiction)

---

## Tools & Resources

### Security Tools

| Tool | Purpose | Installation |
|------|---------|-------------|
| **Trivy** | Container scanning | `sudo apt install trivy` |
| **Snyk** | Dependency scanning | `npm install -g snyk` |
| **Vault** | Secrets management | Docker image available |
| **AIDE** | File integrity | `sudo apt install aide` |
| **fail2ban** | Intrusion prevention | `sudo apt install fail2ban` |

### Monitoring & Alerting

- **Prometheus** - Metrics collection
- **Grafana** - Visualization
- **AlertManager** - Alert routing
- **ELK Stack** - Log aggregation (optional)
- **Wazuh** - SIEM (optional)

---

## Document Metadata

- **Version:** 1.0.0
- **Last Updated:** 2024-01-15
- **Owner:** Security & Risk Team
- **Review Frequency:** Quarterly
- **Next Review:** 2024-04-15
- **Approved By:** [Pending]
