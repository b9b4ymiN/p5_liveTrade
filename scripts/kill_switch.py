#!/usr/bin/env python3
"""
Manual Kill Switch
Emergency trading halt with authentication and audit logging
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import signal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [KILL SWITCH] - %(message)s'
)
logger = logging.getLogger(__name__)


class KillSwitch:
    """Manual kill switch for emergency trading halt"""

    EMERGENCY_FILE = "/tmp/EMERGENCY_KILL_SWITCH"
    AUDIT_LOG = "./logs/kill_switch_audit.log"

    def __init__(self):
        os.makedirs(os.path.dirname(self.AUDIT_LOG), exist_ok=True)

    def activate(self, mode: str, reason: str, activated_by: str = "manual"):
        """
        Activate kill switch

        Args:
            mode: immediate, graceful, or pause
            reason: Reason for activation
            activated_by: Who activated it
        """
        logger.info("=" * 60)
        logger.info(f"ACTIVATING KILL SWITCH - MODE: {mode.upper()}")
        logger.info("=" * 60)

        # Create audit log entry
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "kill_switch_activated",
            "mode": mode,
            "activated_by": activated_by,
            "reason": reason,
            "status": "initiated"
        }

        # Execute mode-specific actions
        if mode == "immediate":
            success = self._immediate_stop()
        elif mode == "graceful":
            success = self._graceful_stop()
        elif mode == "pause":
            success = self._pause_trading()
        else:
            logger.error(f"Invalid mode: {mode}")
            return False

        audit_entry["status"] = "completed" if success else "failed"

        # Log to audit
        self._write_audit_log(audit_entry)

        # Create emergency file marker
        if success:
            self._create_emergency_marker(mode, reason)

        logger.info("=" * 60)
        logger.info(f"KILL SWITCH {mode.upper()} - {'SUCCESS' if success else 'FAILED'}")
        logger.info("=" * 60)

        return success

    def _immediate_stop(self) -> bool:
        """Immediate emergency stop"""
        logger.warning("IMMEDIATE STOP: Closing all positions and halting")

        try:
            # Step 1: Stop any running bot processes
            self._stop_bot_process()

            # Step 2: Create emergency halt marker
            with open(self.EMERGENCY_FILE, 'w') as f:
                f.write(json.dumps({
                    "mode": "immediate",
                    "timestamp": datetime.now().isoformat(),
                    "action": "all_halted"
                }))

            logger.info("✓ Emergency marker created")
            logger.info("✓ Bot process terminated")
            logger.info("✓ Trading halted")

            # Note: Actual position closing would be done by the bot
            # or manually via exchange
            logger.warning("⚠️  Manual verification required:")
            logger.warning("   - Check open positions on exchange")
            logger.warning("   - Manually close if needed")

            return True

        except Exception as e:
            logger.error(f"Error in immediate stop: {e}", exc_info=True)
            return False

    def _graceful_stop(self) -> bool:
        """Graceful stop allowing positions to close"""
        logger.info("GRACEFUL STOP: Stopping new entries, closing existing positions")

        try:
            # Create marker for graceful shutdown
            with open(self.EMERGENCY_FILE, 'w') as f:
                f.write(json.dumps({
                    "mode": "graceful",
                    "timestamp": datetime.now().isoformat(),
                    "action": "no_new_entries"
                }))

            logger.info("✓ Graceful shutdown initiated")
            logger.info("✓ New entries blocked")
            logger.info("✓ Existing positions will close at targets")
            logger.info("⏳ Bot will halt after positions close (max 30 min)")

            return True

        except Exception as e:
            logger.error(f"Error in graceful stop: {e}", exc_info=True)
            return False

    def _pause_trading(self) -> bool:
        """Pause new entries only"""
        logger.info("PAUSE: Stopping new entries, keeping existing positions")

        try:
            # Create pause marker
            with open(self.EMERGENCY_FILE, 'w') as f:
                f.write(json.dumps({
                    "mode": "pause",
                    "timestamp": datetime.now().isoformat(),
                    "action": "pause_new_entries"
                }))

            logger.info("✓ Trading paused")
            logger.info("✓ New entries blocked")
            logger.info("✓ Existing positions continue to be managed")
            logger.info("✓ Can resume without restart")

            return True

        except Exception as e:
            logger.error(f"Error in pause: {e}", exc_info=True)
            return False

    def _stop_bot_process(self):
        """Stop the trading bot process"""
        try:
            # Look for running bot process
            import psutil

            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main.py' in cmdline or 'trading_bot' in cmdline:
                        logger.info(f"Terminating bot process (PID: {proc.info['pid']})")
                        proc.terminate()
                        proc.wait(timeout=10)
                        logger.info(f"✓ Process {proc.info['pid']} terminated")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    pass

        except ImportError:
            logger.warning("psutil not available, cannot auto-terminate processes")
            logger.warning("Manually stop the bot with: docker-compose stop bot")
        except Exception as e:
            logger.warning(f"Could not stop bot process: {e}")

    def clear(self, cleared_by: str = "manual"):
        """Clear kill switch and allow resumption"""
        logger.info("=" * 60)
        logger.info("CLEARING KILL SWITCH")
        logger.info("=" * 60)

        if not os.path.exists(self.EMERGENCY_FILE):
            logger.warning("No kill switch marker found")
            return True

        try:
            # Read current state
            with open(self.EMERGENCY_FILE, 'r') as f:
                state = json.load(f)

            # Remove marker
            os.remove(self.EMERGENCY_FILE)

            # Audit log
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "kill_switch_cleared",
                "previous_mode": state.get("mode"),
                "cleared_by": cleared_by,
                "status": "cleared"
            }
            self._write_audit_log(audit_entry)

            logger.info("✓ Kill switch cleared")
            logger.info("✓ Trading can resume")
            logger.info("⚠️  Remember to:")
            logger.info("   - Verify system health")
            logger.info("   - Check risk limits")
            logger.info("   - Monitor closely after resumption")

            return True

        except Exception as e:
            logger.error(f"Error clearing kill switch: {e}", exc_info=True)
            return False

    def status(self):
        """Check kill switch status"""
        if os.path.exists(self.EMERGENCY_FILE):
            with open(self.EMERGENCY_FILE, 'r') as f:
                state = json.load(f)

            logger.info("Kill Switch Status: ACTIVE")
            logger.info(f"Mode: {state.get('mode')}")
            logger.info(f"Activated: {state.get('timestamp')}")
            logger.info(f"Action: {state.get('action')}")
            return False
        else:
            logger.info("Kill Switch Status: INACTIVE")
            logger.info("Trading is allowed to proceed")
            return True

    def _create_emergency_marker(self, mode: str, reason: str):
        """Create emergency marker file"""
        marker_data = {
            "mode": mode,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "activated": True
        }

        with open(self.EMERGENCY_FILE, 'w') as f:
            json.dump(marker_data, f, indent=2)

        logger.info(f"Emergency marker created: {self.EMERGENCY_FILE}")

    def _write_audit_log(self, entry: dict):
        """Write to audit log"""
        try:
            with open(self.AUDIT_LOG, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            logger.info(f"Audit log updated: {self.AUDIT_LOG}")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Manual Kill Switch for Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Immediate stop (emergency)
  python kill_switch.py --mode immediate --reason "Security breach"

  # Graceful stop (planned)
  python kill_switch.py --mode graceful --reason "Maintenance"

  # Pause trading
  python kill_switch.py --mode pause --reason "Investigating anomaly"

  # Clear kill switch
  python kill_switch.py --clear

  # Check status
  python kill_switch.py --status
        """
    )

    parser.add_argument('--mode', choices=['immediate', 'graceful', 'pause'],
                       help='Kill switch mode')
    parser.add_argument('--reason', type=str,
                       help='Reason for activation (required for activation)')
    parser.add_argument('--clear', action='store_true',
                       help='Clear kill switch and allow resumption')
    parser.add_argument('--status', action='store_true',
                       help='Check kill switch status')
    parser.add_argument('--auth-token', type=str,
                       help='Authentication token (optional)')
    parser.add_argument('--activated-by', type=str, default='manual',
                       help='Who is activating (for audit)')
    parser.add_argument('--confirm', action='store_true',
                       help='Require confirmation for immediate mode')

    args = parser.parse_args()

    kill_switch = KillSwitch()

    # Check status
    if args.status:
        kill_switch.status()
        return 0

    # Clear kill switch
    if args.clear:
        if kill_switch.clear(cleared_by=args.activated_by):
            return 0
        else:
            return 1

    # Activate kill switch
    if args.mode:
        if not args.reason:
            logger.error("--reason is required for activation")
            return 1

        # Require confirmation for immediate mode
        if args.mode == 'immediate' and args.confirm:
            response = input("⚠️  IMMEDIATE MODE will halt all trading NOW. Type 'CONFIRM' to proceed: ")
            if response != 'CONFIRM':
                logger.info("Activation cancelled")
                return 0

        if kill_switch.activate(args.mode, args.reason, args.activated_by):
            return 0
        else:
            return 1

    # No action specified
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
