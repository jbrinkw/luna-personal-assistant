#!/usr/bin/env python3
"""
Temporary timer implementation for testing when database is unavailable
"""
import json
import os
from datetime import datetime, timedelta

# Use absolute path to ensure both UI and agent use the same timer file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TIMER_FILE = os.path.join(SCRIPT_DIR, "temp_timer.json")

def set_timer_temp(duration: int, unit: str = "minutes"):
    """Set a temporary timer using file storage"""
    if unit == "minutes":
        if not (1 <= duration <= 180):
            raise ValueError("Timer duration must be between 1 and 180 minutes")
        end_time = datetime.now() + timedelta(minutes=duration)
        duration_text = f"{duration} minutes"
    elif unit == "seconds":
        if not (1 <= duration <= 10800):  # Max 3 hours in seconds
            raise ValueError("Timer duration must be between 1 and 10800 seconds")
        end_time = datetime.now() + timedelta(seconds=duration)
        minutes = duration // 60
        seconds = duration % 60
        if minutes > 0:
            duration_text = f"{minutes}:{seconds:02d}"
        else:
            duration_text = f"{seconds} seconds"
    else:
        raise ValueError("Unit must be 'minutes' or 'seconds'")
    
    # Save to file
    timer_data = {
        "end_time": end_time.isoformat(),
        "created_at": datetime.now().isoformat()
    }
    
    with open(TIMER_FILE, 'w') as f:
        json.dump(timer_data, f)
    
    return f"Timer set for {duration_text} (until {end_time.strftime('%H:%M:%S')})"

def get_timer_temp():
    """Get current timer status from file"""
    if not os.path.exists(TIMER_FILE):
        return {"status": "no_timer", "message": "No timer currently set"}
    
    try:
        with open(TIMER_FILE, 'r') as f:
            timer_data = json.load(f)
        
        end_time = datetime.fromisoformat(timer_data["end_time"])
        created_at = datetime.fromisoformat(timer_data["created_at"])
        now = datetime.now()
        
        if now >= end_time:
            # Timer has expired
            time_expired = int((now - end_time).total_seconds())
            return {
                "status": "expired",
                "message": f"Timer expired {time_expired} seconds ago",
                "end_time": end_time.isoformat(),
                "created_at": created_at.isoformat()
            }
        else:
            # Timer is still running
            remaining_seconds = int((end_time - now).total_seconds())
            remaining_minutes = remaining_seconds // 60
            remaining_secs = remaining_seconds % 60
            
            return {
                "status": "running",
                "message": f"Timer running - {remaining_minutes}:{remaining_secs:02d} remaining",
                "remaining_seconds": remaining_seconds,
                "end_time": end_time.isoformat(),
                "created_at": created_at.isoformat()
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "set" and len(sys.argv) > 2:
            try:
                duration = int(sys.argv[2])
                # Check if a third argument specifies the unit (seconds)
                if len(sys.argv) > 3 and sys.argv[3] == "seconds":
                    result = set_timer_temp(duration, "seconds")
                else:
                    result = set_timer_temp(duration, "minutes")
                print(result)
            except ValueError as e:
                print(f"Error: {e}")
        elif sys.argv[1] == "get":
            result = get_timer_temp()
            print(json.dumps(result))
    else:
        print("Usage: python timer_temp.py [set <duration> [seconds]|get]") 