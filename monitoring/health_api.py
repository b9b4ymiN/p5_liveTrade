"""
Health Check and Metrics API
FastAPI endpoints for monitoring system health
"""

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
import psutil
import time
from datetime import datetime
from typing import Dict
import logging

app = FastAPI(title="Trading Bot Health API")
logger = logging.getLogger(__name__)

# Global state tracking
system_start_time = time.time()
last_heartbeat = time.time()
trade_count = 0
error_count = 0
last_error = None


@app.get("/healthz")
async def health_check():
    """
    Kubernetes-style health check endpoint
    Returns 200 if system is healthy, 503 if unhealthy
    """
    try:
        # Check if bot is responsive (heartbeat within last 60 seconds)
        time_since_heartbeat = time.time() - last_heartbeat

        if time_since_heartbeat > 60:
            return Response(
                content="Bot heartbeat timeout",
                status_code=503
            )

        # Check system resources
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent

        if cpu_percent > 90 or memory_percent > 90:
            return Response(
                content="Resource exhaustion",
                status_code=503
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": int(time.time() - system_start_time)
            }
        )

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return Response(
            content=f"Health check failed: {str(e)}",
            status_code=503
        )


@app.get("/metrics")
async def metrics():
    """
    Prometheus-compatible metrics endpoint
    Returns system and trading metrics
    """
    uptime = time.time() - system_start_time

    metrics_data = {
        # System metrics
        "system": {
            "uptime_seconds": int(uptime),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
        },

        # Trading metrics
        "trading": {
            "total_trades": trade_count,
            "total_errors": error_count,
            "last_error": last_error,
            "trades_per_hour": (trade_count / uptime * 3600) if uptime > 0 else 0,
        },

        # Timestamp
        "timestamp": datetime.now().isoformat()
    }

    return JSONResponse(content=metrics_data)


@app.get("/readiness")
async def readiness_check():
    """
    Kubernetes readiness probe
    Returns 200 if ready to accept traffic
    """
    # Check if models are loaded
    # Check if connections are established
    # Add actual checks here

    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "timestamp": datetime.now().isoformat()
        }
    )


def update_heartbeat():
    """Update last heartbeat timestamp"""
    global last_heartbeat
    last_heartbeat = time.time()


def increment_trade_count():
    """Increment trade counter"""
    global trade_count
    trade_count += 1


def record_error(error_msg: str):
    """Record error for metrics"""
    global error_count, last_error
    error_count += 1
    last_error = {
        "message": error_msg,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
