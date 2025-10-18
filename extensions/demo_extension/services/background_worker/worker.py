#!/usr/bin/env python3
"""
Demo Background Worker Service
A simple background task that runs without requiring a network port.
"""

import sys
import time
from datetime import datetime


def log(message):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)


def main():
    log("Background Worker started")
    log("This service runs without requiring a network port")
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            log(f"Background Worker tick #{iteration} - Processing tasks...")
            
            # Simulate some background work
            time.sleep(10)
            
            # Every 6 iterations (1 minute), log a summary
            if iteration % 6 == 0:
                log(f"Background Worker summary: Completed {iteration} iterations")
                
    except KeyboardInterrupt:
        log("Background Worker received shutdown signal")
        log(f"Total iterations completed: {iteration}")
        sys.exit(0)


if __name__ == "__main__":
    main()

