"""
Unhedged Market Status Manager
Calculates market status based on time and market patterns
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

class UnhedgedMarketStatus:
    """Calculate Unhedged market status based on time patterns"""

    @staticmethod
    def get_market_status_from_time(current_time: datetime, market_type: str = 'binary') -> Dict:
        """
        Get market status based on current time

        Args:
            current_time: Current datetime
            market_type: 'binary' for hourly YES/NO, 'interval' for 2-hourly LOW/MID/HIGH

        Returns:
            Dict with status info:
            - is_active: bool
            - status: str (ACTIVE, ENDED)
            - time_until_resolved: int (minutes until resolve, None if can't determine)
            - display: str (e.g., "15 min left", "ENDED")
        """
        current_min = current_time.minute
        current_hour = current_time.hour

        if market_type == 'binary':
            # Binary markets: hourly, close at XX:50, resolve at XX:00 (next hour)
            close_min = 50
            resolve_min = 0  # Next hour

            # Check if in CLOSED window (XX:50 - XX:00)
            if current_min >= close_min:
                # Market CLOSED - can't bet, waiting for resolve
                is_active = False
                time_until = 60 - current_min  # Minutes until next hour
                status = "CLOSED"

                if time_until > 0:
                    display = f"CLOSED ({time_until} min until resolve)"
                else:
                    # At XX:00 exactly, market is resolved
                    display = "RESOLVED"

            # Check if just resolved (XX:00 - XX:05, give 5 min buffer)
            elif current_min < 5:
                # Market just resolved, new market opening
                is_active = False
                status = "RESOLVED"
                display = "RESOLVED (new market opening)"
                time_until = 0
            else:
                # Market active (XX:05 - XX:50)
                is_active = True
                time_until = 60 - current_min  # Minutes until resolve
                status = "ACTIVE"

                if time_until <= 20:
                    display = f"{time_until} min left"
                else:
                    display = "ACTIVE"

        elif market_type == 'interval':
            # Interval markets: every 2 hours at odd hours ONLY (11, 13, 15, 17, 19, 21, 23, 1, 3, 5, 7, 9)
            # Close at XX:50 (of second hour), resolve at XX:00 (of third hour)
            # Example: Market starts at 11:00, closes at 12:50, resolves at 13:00

            # Find the most recent interval market start time
            # Interval markets start at odd hours: 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23

            # Determine which interval market is currently active (if any)
            # Current hour could be any hour, we need to find the relevant interval market

            # For any given time, find the most recent odd hour that started an interval market
            # But interval markets only exist for specific odd hours from config

            interval_hours = [11, 13, 15, 17, 19, 21, 23, 1, 3, 5, 7, 9]  # All odd hours

            # Find the most recent interval market start hour
            market_start_hour = None
            for hour in sorted(interval_hours, reverse=True):
                # If we're looking at a past hour (considering day wrap-around)
                test_time = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)

                # If this hour is in the future, it might be from yesterday
                if test_time > current_time:
                    test_time -= timedelta(days=1)

                # Check if a market starting at this hour would still be active (2 hour duration)
                if current_time - test_time < timedelta(hours=2):
                    market_start_hour = hour
                    break

            if market_start_hour is None:
                # No active interval market
                is_active = False
                time_until = 0
                status = "NO_MARKET"
                display = "No active market"
            else:
                # Calculate close and resolve times
                close_hour = (market_start_hour + 1) % 24
                resolve_hour = (market_start_hour + 2) % 24

                # Create datetime objects
                market_start_time = current_time.replace(hour=market_start_hour, minute=0, second=0, microsecond=0)

                # Handle day wrap-around
                if resolve_hour < market_start_hour:
                    # Resolves tomorrow
                    close_time = market_start_time + timedelta(hours=1)
                    resolve_time = market_start_time + timedelta(hours=2)
                else:
                    close_time = current_time.replace(hour=close_hour, minute=50, second=0, microsecond=0)
                    resolve_time = current_time.replace(hour=resolve_hour, minute=0, second=0, microsecond=0)

                    # Adjust if close time is in the past (we're past the close time)
                    if close_time < current_time:
                        close_time += timedelta(days=1)
                    if resolve_time < current_time:
                        resolve_time += timedelta(days=1)

                # Check if market is still active
                if current_time >= close_time:
                    # Market closed or resolved
                    is_active = False
                    time_until = int((resolve_time - current_time).total_seconds() / 60)
                    status = "ENDED"
                    display = "ENDED"
                else:
                    # Market active
                    is_active = True
                    time_until = int((resolve_time - current_time).total_seconds() / 60)
                    status = "ACTIVE"

                    if time_until <= 30:
                        display = f"{time_until} min left"
                    elif time_until <= 120:
                        hours = time_until // 60
                        mins = time_until % 60
                        display = f"{hours}h {mins}m left"
                    else:
                        display = "ACTIVE"

        else:
            # Unknown market type
            is_active = True
            time_until = None
            status = "UNKNOWN"
            display = "UNKNOWN"

        return {
            'is_active': is_active,
            'status': status,
            'time_until_resolved': time_until,
            'display': display,
            'close_time': close_min if market_type == 'binary' else None,
            'resolve_time': resolve_min if market_type == 'binary' else None,
        }

    @staticmethod
    def should_alert_now(symbol: str, market_type: str = 'binary') -> Tuple[bool, str]:
        """
        Check if should send alert for this symbol now

        Args:
            symbol: Trading pair symbol
            market_type: 'binary' or 'interval'

        Returns:
            Tuple of (should_alert: bool, status_message: str)
        """
        now = datetime.now()
        status_info = UnhedgedMarketStatus.get_market_status_from_time(now, market_type)

        if not status_info['is_active']:
            return False, status_info['display']

        # Market is active, can alert
        return True, status_info['display']
