# Phase 5: Live Trading Deployment System

## Overview

This is **Phase 5** of the AI-Powered OI Trading System - the final phase that brings everything together into a fully autonomous, production-ready trading bot.

**Phase 5** integrates:
- Real-time market data streaming (WebSocket)
- Live feature engineering and ML inference
- Reinforcement Learning decision-making
- Automated order execution with safety controls
- Real-time monitoring and alerting
- Continuous online learning

## Project Structure

```
p5_liveTrade/
├── bot/                      # Main trading bot
│   ├── __init__.py
│   └── trading_bot.py       # AITradingBot class
├── data_collector/          # Real-time data streaming
│   ├── __init__.py
│   └── websocket_streamer.py
├── features/                # Feature engineering
│   ├── __init__.py
│   └── feature_engineer.py
├── models/                  # ML model inference
│   ├── __init__.py
│   └── ensemble.py
├── rl/                      # RL decision engine
│   ├── __init__.py
│   └── rl_agent.py
├── execution/               # Order execution
│   ├── __init__.py
│   └── order_executor.py
├── risk/                    # Risk management
│   ├── __init__.py
│   └── risk_manager.py
├── monitoring/              # Monitoring & alerts
│   ├── __init__.py
│   ├── telegram_bot.py
│   └── dashboard.py        # Streamlit dashboard
├── database/                # Trade logging
│   ├── __init__.py
│   └── trade_logger.py
├── learning/                # Online learning
│   ├── __init__.py
│   └── online_learner.py
├── config/                  # Configuration files
│   └── config.yaml
├── scripts/                 # Startup scripts
│   ├── start_bot.sh
│   └── start_dashboard.sh
├── main.py                  # Main entry point
├── requirements.txt
├── Dockerfile
├── Dockerfile.dashboard
├── docker-compose.yml
├── Claude.md               # Phase 5 specification
├── overall_project.md      # Complete project overview
└── README.md              # This file
```

## Dependencies on Previous Phases

This project builds upon work completed in previous phases:

### Phase 1: Data Collection ([p1_dataCollection](https://github.com/b9b4ymiN/p1_dataCollection))
- **Status:** ✅ Complete (Docker on local machine)
- **Components:**
  - Binance Futures API integration
  - Historical data collection (OHLCV, OI, Funding, Liquidations)
  - PostgreSQL + TimescaleDB database
  - Data quality monitoring
  - WebSocket real-time streaming

### Phase 2-4: ML & RL ([p2_mlFeature](https://github.com/b9b4ymiN/p2_mlFeature))
- **Status:** ✅ Complete
- **Phase 2:** Feature Engineering (100+ features)
- **Phase 3:** ML Model Training (XGBoost, LSTM, Ensemble)
- **Phase 4:** RL Agent Training (PPO for trading decisions)

### Phase 5: Live Deployment (This Repository)
- **Status:** 🚀 Ready for deployment
- Production trading system with all components integrated

## Quick Start

### Prerequisites

1. **Trained Models** from Phase 2-4:
   - Ensemble ML model (`ensemble_model.pkl`)
   - RL agent (`rl_agent.zip`)
   - Place in `./models_saved/` directory

2. **API Credentials:**
   - Binance Futures API key and secret
   - Telegram bot token (optional)

3. **Infrastructure:**
   - Redis (for real-time data caching)
   - PostgreSQL with TimescaleDB (optional, for logging)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/b9b4ymiN/p5_liveTrade.git
   cd p5_liveTrade
   ```

2. **Install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

4. **Configure settings:**
   - Edit `config/config.yaml`
   - Set `paper_trading_mode: true` for testing
   - Configure risk parameters

### Running the Bot

#### Option 1: Local Python

```bash
# Start Redis (required)
redis-server

# Start the trading bot
python main.py

# In another terminal, start the dashboard
streamlit run monitoring/dashboard.py
```

#### Option 2: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

Services:
- **Bot:** Main trading system
- **Dashboard:** http://localhost:8501
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

## Configuration

### config/config.yaml

Key configuration sections:

```yaml
# Trading parameters
symbol: "SOLUSDT"
leverage: 3
initial_balance: 2000

# Risk management
risk:
  risk_per_trade: 0.02        # 2% risk per trade
  max_daily_loss: 0.03        # 3% daily loss limit
  max_consecutive_losses: 5

# Safety
safety:
  paper_trading_mode: true    # Start with paper trading!
  kill_switch_enabled: true
```

**⚠️ IMPORTANT:** Always start with `paper_trading_mode: true` to test the system without real money!

## System Components

### 1. WebSocket Data Streamer
- Real-time market data from Binance
- Streams klines, mark price, funding rate
- Caches data in Redis for low-latency access

### 2. Feature Engineer
- Computes 50+ features in real-time
- Price action, OI, volume, funding indicators
- Rolling windows and technical indicators

### 3. ML Inference Engine
- Loads trained ensemble models
- Provides entry signals and price targets
- Returns signal (long/short/neutral) + confidence

### 4. RL Decision Engine
- State: position, ML predictions, market conditions, account status
- Actions: HOLD, ENTER_LONG, ENTER_SHORT, EXIT, SCALE_IN, SCALE_OUT
- Uses PPO algorithm for optimal action selection

### 5. Risk Manager
- Position size validation
- Daily loss limits
- Consecutive loss tracking
- Liquidation distance monitoring

### 6. Order Executor
- Binance Futures API integration
- Market and limit order placement
- Retry logic with exponential backoff
- Position tracking

### 7. Trade Logger
- Logs all entries and exits
- Equity tracking
- Performance metrics
- JSON-based file storage (upgradeable to PostgreSQL)

### 8. Telegram Notifier
- Real-time trade alerts
- Error notifications
- Daily performance summaries

### 9. Streamlit Dashboard
- Live equity curve
- Recent trades table
- Risk metrics display
- Auto-refreshing every 5 seconds

### 10. Online Learner
- Daily incremental model updates
- Weekly full retraining
- A/B testing of new models
- Automatic rollback on degradation

## Safety Features

### Built-in Safeguards

1. **Paper Trading Mode**
   - Simulates trades without real execution
   - Perfect for testing strategies

2. **Risk Limits**
   - Max position size: 20% of equity
   - Daily loss limit: 3%
   - Max consecutive losses: 5

3. **Kill Switches**
   - Liquidation distance < 15% → emergency exit
   - ML confidence drops → disable signals
   - Critical errors → stop trading

4. **Validation Layers**
   - Pre-trade risk checks
   - Position size validation
   - API error handling with retries

## Monitoring

### Real-time Dashboard

Access at http://localhost:8501

Features:
- Live equity curve
- Current position status
- Recent trade history
- Risk metrics (Sharpe, drawdown, win rate)

### Telegram Alerts

Configure in `config/config.yaml`:
```yaml
telegram:
  enabled: true
  token: "your_bot_token"
  chat_id: "your_chat_id"
```

Receives:
- Trade entries/exits
- PnL updates
- Error alerts
- Daily summaries

### Log Files

Located in `./logs/`:
- `trading_bot.log` - Main system log
- `trades.jsonl` - Trade journal (JSON lines)

## Development Workflow

### 1. Paper Trading (Week 1-2)

```yaml
# config/config.yaml
safety:
  paper_trading_mode: true
```

- Test system integration
- Validate ML/RL predictions
- Monitor for errors
- Fine-tune parameters

### 2. Live Testing (Week 3)

```yaml
safety:
  paper_trading_mode: false
initial_balance: 500  # Start small!
```

- Begin with minimal capital
- Monitor closely 24/7
- Validate real execution
- Check slippage and fees

### 3. Scaling (Week 4+)

```yaml
initial_balance: 2000
leverage: 5  # Increase if Sharpe > 1.8
```

- Gradually increase capital
- Scale leverage conservatively
- Enable online learning
- Add more symbols

## Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Daily Return | 0.25-0.5% | 🎯 |
| Sharpe Ratio | > 1.8 | 🎯 |
| Max Drawdown | < 20% | 🎯 |
| Win Rate | > 55% | 🎯 |
| System Uptime | > 99.5% | 🎯 |

## Troubleshooting

### Common Issues

**1. Redis Connection Failed**
```bash
# Start Redis
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:7-alpine
```

**2. Binance API Errors**
- Check API key permissions (Futures enabled)
- Verify testnet vs mainnet configuration
- Check IP whitelist if configured

**3. Model Loading Errors**
- Ensure models are in `./models_saved/`
- Check model file paths in `config.yaml`
- Models from Phase 2-4 must be compatible

**4. WebSocket Disconnects**
- System automatically reconnects
- Check internet connection stability
- Review logs for error patterns

## Production Deployment

### Deployment Checklist

- [ ] Models trained and validated (Phase 2-4)
- [ ] Configuration reviewed
- [ ] API credentials secured
- [ ] Paper trading successful (2+ weeks)
- [ ] Risk limits configured
- [ ] Telegram alerts working
- [ ] Dashboard accessible
- [ ] Backup system configured
- [ ] Kill switches tested
- [ ] Logs monitoring setup

### Recommended VPS Setup

- **Provider:** DigitalOcean, AWS, or Vultr
- **Specs:** 2 CPU, 4GB RAM, 50GB SSD
- **OS:** Ubuntu 22.04 LTS
- **Docker:** Latest stable version
- **Monitoring:** Prometheus + Grafana (optional)

### Deployment Steps

```bash
# 1. Clone on VPS
git clone https://github.com/b9b4ymiN/p5_liveTrade.git
cd p5_liveTrade

# 2. Setup environment
cp .env.example .env
nano .env  # Add credentials

# 3. Start with Docker Compose
docker-compose up -d

# 4. Monitor logs
docker-compose logs -f bot

# 5. Access dashboard
# Navigate to http://your-vps-ip:8501
```

## Testing

### Unit Tests (Coming Soon)

```bash
pytest tests/
```

### Integration Tests

```bash
# Test with paper trading
python main.py

# Verify components
python -c "from bot.trading_bot import AITradingBot; print('✓ Bot OK')"
```

## Contributing

This is part of a multi-phase project. Contributions should align with:
- Phase architecture documented in `overall_project.md`
- Risk management philosophy
- Code quality standards

## License

MIT License - See LICENSE file

## Acknowledgments

Built as part of the AI-Powered OI Trading System project:
- Phase 1: [p1_dataCollection](https://github.com/b9b4ymiN/p1_dataCollection)
- Phase 2-4: [p2_mlFeature](https://github.com/b9b4ymiN/p2_mlFeature)
- Phase 5: This repository

## Disclaimer

**⚠️ TRADING DISCLAIMER ⚠️**

This software is for educational purposes only. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results.

- Never invest more than you can afford to lose
- Always start with paper trading
- Understand the risks before deploying real capital
- The authors are not responsible for any trading losses

## Contact & Support

For issues and questions:
- GitHub Issues: [Report here](https://github.com/b9b4ymiN/p5_liveTrade/issues)
- Documentation: See `Claude.md` and `overall_project.md`

---

**Happy Trading! 🚀**

*Built with Python, ML/RL, and lots of backtesting*
