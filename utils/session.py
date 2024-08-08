from datetime import datetime, timedelta
import pytz


def get_session_expiry_time():
    now_utc = datetime.now(pytz.timezone('UTC'))
    now_ist = now_utc.astimezone(pytz.timezone('Asia/Kolkata'))
    print(now_ist)
    target_time_ist = now_ist.replace(hour=3, minute=00, second=0, microsecond=0)
    if now_ist > target_time_ist:
        target_time_ist += timedelta(days=1)
    remaining_time = target_time_ist - now_ist
    return remaining_time