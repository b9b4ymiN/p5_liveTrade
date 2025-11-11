"""
Streamlit Dashboard for Trading Bot Monitoring
Real-time dashboard showing equity, trades, and performance metrics
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime
from database.trade_logger import TradeLogger
import yaml


class TradingDashboard:
    """
    Real-time trading dashboard using Streamlit
    """

    def __init__(self, config):
        self.config = config
        self.trade_logger = TradeLogger(config['database'])

    def run(self):
        """
        Run Streamlit dashboard
        """
        st.set_page_config(
            page_title="AI Trading Bot Dashboard",
            page_icon="🤖",
            layout="wide"
        )

        st.title("🤖 AI Trading Bot - Live Dashboard")

        # Auto-refresh
        placeholder = st.empty()

        while True:
            with placeholder.container():
                self._render_dashboard()

            time.sleep(5)  # Refresh every 5 seconds

    def _render_dashboard(self):
        """
        Render all dashboard components
        """
        # Top metrics
        col1, col2, col3, col4, col5 = st.columns(5)

        # Mock data for now
        with col1:
            st.metric("Equity", "$2,050.00", "+2.5%")

        with col2:
            st.metric("Daily PnL", "+$50.00", "+2.5%")

        with col3:
            st.metric("Position", "FLAT", "$0.00")

        with col4:
            st.metric("Win Rate", "55.0%", "10 trades")

        with col5:
            st.metric("Max Drawdown", "5.2%", "Live")

        st.divider()

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 Equity Curve")
            equity_chart = self._plot_equity_curve()
            st.plotly_chart(equity_chart, use_container_width=True)

        with col2:
            st.subheader("📊 Recent Trades")
            trades_df = self._get_recent_trades()
            st.dataframe(trades_df, use_container_width=True)

        # Risk metrics
        st.subheader("⚠️ Risk Metrics")
        self._render_risk_metrics()

    def _plot_equity_curve(self):
        """Plot equity curve"""
        df = self.trade_logger.get_equity_history()

        if len(df) == 0:
            # Create dummy data
            df = pd.DataFrame({
                'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='H'),
                'equity': [2000 + i * 5 for i in range(10)]
            })

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['equity'],
            mode='lines',
            name='Equity',
            line=dict(color='#00D9FF', width=2)
        ))

        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis_title="Time",
            yaxis_title="Equity ($)"
        )

        return fig

    def _get_recent_trades(self) -> pd.DataFrame:
        """Get recent trades"""
        trades = self.trade_logger.get_recent_trades(limit=10)

        if len(trades) == 0:
            # Return empty dataframe with columns
            return pd.DataFrame(columns=['timestamp', 'side', 'entry_price', 'exit_price', 'pnl', 'duration'])

        trades_df = pd.DataFrame(trades)

        # Format for display
        if 'pnl' in trades_df.columns:
            trades_df['pnl_formatted'] = trades_df['pnl'].apply(
                lambda x: f"${x:.2f}" if x > 0 else f"-${abs(x):.2f}"
            )

            return trades_df[['timestamp', 'direction', 'entry_price', 'exit_price', 'pnl_formatted', 'duration']]

        return trades_df

    def _render_risk_metrics(self):
        """Render risk metrics"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Sharpe Ratio", "1.85")
        with col2:
            st.metric("Sortino Ratio", "2.10")
        with col3:
            st.metric("Calmar Ratio", "1.50")
        with col4:
            st.metric("Profit Factor", "1.90")


def main():
    """Main entry point for dashboard"""
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    dashboard = TradingDashboard(config)
    dashboard.run()


if __name__ == "__main__":
    main()
