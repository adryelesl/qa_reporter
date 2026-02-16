import time
from datetime import datetime, timedelta

def wait_until_time(target_time_str):
    """
    Waits until the specified time (HH:MM) to return.
    If the time has already passed today, waits until tomorrow.
    Returns True when the time is reached.
    """
    try:
        target_hour, target_minute = map(int, target_time_str.split(':'))
    except ValueError:
        print(f"⚠️ Invalid time format '{target_time_str}'. Expected HH:MM. Running immediately.")
        return False

    while True:
        now = datetime.now()
        target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        if now > target_time:
            # If target time passed today, schedule for tomorrow
            target_time += timedelta(days=1)
        
        wait_seconds = (target_time - now).total_seconds()
        
        print(f"⏳ Waiting until {target_time.strftime('%Y-%m-%d %H:%M')} to run... ({int(wait_seconds/60)} min)")
        
        # Sleep until the time (or check periodically)
        # We sleep in chunks to allow interruption if needed, but simple sleep is fine for now
        time.sleep(wait_seconds)
        return True
