"""
Data collection module for real-time market data streaming
"""

from .websocket_streamer import BinanceWebSocketStreamer

__all__ = ['BinanceWebSocketStreamer']
