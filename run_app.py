#!/usr/bin/env python
# run_app.py

"""
Proxy script to run the ChefByte application.
This ensures the application runs with the correct working directory 
and relative imports function as expected.
"""

import sys
import os
import traceback

# Ensure the project root is in the Python path
# This is usually automatic if run from the root, but explicit is safer
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the main application class
try:
    from app import ChefByteChat
except ImportError as e:
    print(f"Error: Could not import ChefByteChat from app.py: {e}")
    print("Please ensure app.py exists in the root directory and all dependencies are installed.")
    sys.exit(1)

# --- Simulated Conversation --- 
simulated_messages = [
    "Show my inventory",
    "Hello ChefByte!",
    "What can you do?",
    "I just bought 2 lbs of 80/20 Ground Beef and a gallon of Great Value Whole Milk.",
    "I also got some fresh spinach.",
    "What meals can I make with ground beef and spinach?",
    "I don't like mushrooms.", # Test taste profile update
    "Let's make the Bacon Cheeseburger from my saved meals.",
    "Actually, I used half the ground beef already.", # Test inventory update (consumption)
    "Okay, what about that Sesame Chicken recipe instead?",
    "Plan the Sesame Chicken for dinner tonight.", # Test daily planner
    "Delete the instant ramen from my inventory.", # Test inventory delete
    "Show my inventory"
]

if __name__ == "__main__":
    chef_chat = None # Initialize to None
    try:
        # --- Reload from Baseline Snapshot --- 
        print("Reloading database from baseline snapshot...")
        try:
            # Need a temporary ResetDB instance to access the reload method
            from debug.reset_db import ResetDB
            reloader = ResetDB()
            if not reloader.reload_from_snapshot("chefbyte_baseline.db"):
                print("[WARN] Failed to reload from baseline snapshot. Proceeding with current DB state.")
            # Ensure the reloader's connection is closed if it was opened
            if reloader.db and reloader.db.conn:
                 reloader.db.disconnect()
        except Exception as reload_err:
            print(f"[ERROR] Failed during snapshot reload: {reload_err}. Proceeding with current DB state.")
            traceback.print_exc() # Print detailed error
        # -------------------------------------
            
        # Create instance of ChefByte chat
        print("Starting ChefByte Simulation via proxy script...")
        chef_chat = ChefByteChat()
        
        print("\n--- ChefByte Simulation Start ---")
        print("--------------------------------------------")
        
        # Iterate through simulated messages
        for i, user_input in enumerate(simulated_messages):
            print(f"\n--- Message {i+1} ---")
            print(f"Simulated User: {user_input}")
            
            if not user_input:
                continue
                
            response = chef_chat.process_message(user_input)
            # Safely print response, replacing characters incompatible with the console encoding
            safe_response = response.encode('utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace')
            print(f"\nChefByte: {safe_response}")
            print("--------------------------------------------")
            
        print("\n--- ChefByte Simulation End ---")
            
    except KeyboardInterrupt:
        print("\nSimulation interrupted!") # Changed message for simulation
    except Exception as e:
        print(f"\nAn error occurred during simulation: {str(e)}")
        print(traceback.format_exc())
    finally:
        # Ensure database connection is closed if chat object exists
        if chef_chat:
            chef_chat.close() 