import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import ChefByteChat
import traceback

def run_tests():
    """Runs a series of predefined tests against the ChefByteChat class."""
    print("Initializing ChefByteChat...")
    try:
        # Initialize with medium intelligence for potentially better routing
        chef_chat = ChefByteChat(intelligence_level='medium') 
        print("ChefByteChat initialized.")
    except Exception as e:
        print(f"Error initializing ChefByteChat: {e}")
        print(traceback.format_exc())
        return

    test_messages = [
        # --- Inventory Tests ---
        "Hi ChefByte! Can you remind me how to update my inventory?", # Initial interaction
        "I just bought 2 lbs of chicken breast.", # Add inventory
        "What's currently in my inventory?", # Read inventory
        "I used 1 lb of the chicken breast.", # Update inventory
        "What's in my inventory now?", # Read inventory again
        "I finished the chicken breast.", # Delete inventory (implicitly)
        "Check inventory one last time.", # Read inventory after deletion

        # --- Taste Profile Tests ---
        "I really dislike cilantro, but I love spicy food.", # Set taste profile
        "What do you know about my taste preferences?", # Read taste profile
        "Actually, add that I'm allergic to shellfish.", # Update taste profile
        "What are my preferences now?", # Read taste profile again

        # --- Shopping List Tests ---
        "Please add 1 gallon of milk to my shopping list.", # Add to shopping list
        "Also add a loaf of bread.", # Add another item
        "What's on my shopping list?", # Read shopping list
        "Change the milk quantity to 2 gallons.", # Update shopping list item
        "Show me the shopping list again.", # Read shopping list again
        "Remove the bread from my list.", # Delete shopping list item
        "What's left on the list?", # Read shopping list after deletion
        "Clear my shopping list completely.", # Clear shopping list
        "Is my shopping list empty now?", # Read empty shopping list

        # --- Saved Meals (Read Only - Saving is complex via prompt) ---
        # Assuming some meals might exist or be created by tools
        "Can you show me my saved recipes?", 

        # --- Daily Planner Tests ---
        "Plan spaghetti for dinner tonight.", # Add to daily plan
        "What meals are planned for today?", # Read daily plan
        "Add a note for today: 'Remember to buy garlic'.", # Update daily plan (add note)
        "What's the plan and notes for today?", # Read daily plan again
        "Clear the plan for today.", # Delete daily plan
        "Is anything planned for today?", # Read empty daily plan
    ]

    print("\n--- Starting Interaction Tests ---")
    for i, msg in enumerate(test_messages):
        print(f"\n--- Test {i+1} ---")
        print(f"User: {msg}")
        try:
            response = chef_chat.process_message(msg)
            print(f"ChefByte: {response}")
        except Exception as e:
            print(f"An error occurred during message processing: {e}")
            print(traceback.format_exc())
            # Optionally continue to the next test or break
            # break 
            
    print("\n--- Interaction Tests Finished ---")

if __name__ == "__main__":
    run_tests() 