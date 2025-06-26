import sys
import os
from typing import List, Tuple, Optional, Literal
from agents import function_tool
import traceback # Added for error logging

# --- Database Imports ---
# Ensure correct path to db_functions. If db is in a parent or sibling directory:
project_root = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(project_root) # Go up one level from 'chefbyte' to 'v0.2'
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from db.db_functions import (
        init_tables, Database, Inventory, IngredientsFood, TasteProfile, 
        SavedMeals, ShoppingList, DailyPlanner, NewMealIdeas, 
        SavedMealsInStockIds, NewMealIdeasInStockIds
    )
except ImportError as e:
    print(f"Error importing database modules in agent_tools.py: {e}")
    print(f"Current sys.path: {sys.path}")
    # Define dummy functions or raise error if DB is essential for tools
    # These dummies now just return errors, actual logic moved/will move
    @function_tool
    def get_inventory_context(): return "Error: DB Connection failed or PullHelper unavailable."
    @function_tool
    def update_inventory(user_input: str): return "Error: DB Connection failed or InventoryProcessor unavailable."
    @function_tool
    def get_taste_profile_context(): return "Error: DB Connection failed or PullHelper unavailable."
    @function_tool
    def get_saved_meals_context(): return "Error: DB Connection failed or PullHelper unavailable."
    @function_tool
    def get_shopping_list_context(): return "Error: DB Connection failed or PullHelper unavailable."
    @function_tool
    def get_daily_notes_context(): return "Error: DB Connection failed or PullHelper unavailable."
    @function_tool
    def get_new_meal_ideas_context(): return "Error: DB Connection failed or PullHelper unavailable."
    @function_tool
    def get_instock_meals_context(): return "Error: DB Connection failed or PullHelper unavailable."
    @function_tool
    def get_ingredients_info_context(): return "Error: DB Connection failed or PullHelper unavailable."
    @function_tool
    def update_taste_profile(user_request: str): return "Error: DB Connection failed or TasteProfileProcessor unavailable."
    @function_tool
    def update_saved_meals(user_input: str): return "Error: DB Connection failed or SavedMealsProcessor unavailable."
    @function_tool
    def update_shopping_list(user_input: str): return "Error: DB Connection failed or ShoppingListProcessor unavailable."
    @function_tool
    def update_daily_plan(user_input: str): return "Error: DB Connection failed or DailyNotesProcessor unavailable."
else:
    # --- Import Helpers --- 
    try:
        from helpers.pull_helper import PullHelper
    except ImportError:
        print("[ERROR] agent_tools.py: Failed to import PullHelper. Context tools will fail.")
        PullHelper = None # Set to None if import fails
    
    try:
        from helpers.push_helpers.inventory_processor import NaturalLanguageInventoryProcessor
        from helpers.push_helpers.taste_profile_processor import TasteProfileProcessor
        from helpers.push_helpers.saved_meals_processor import SavedMealsProcessor
        from helpers.push_helpers.shopping_list_processor import ShoppingListProcessor
        from helpers.push_helpers.daily_notes_processor import DailyNotesProcessor
    except ImportError as e:
        print(f"[ERROR] agent_tools.py: Failed to import one or more push helpers: {e}. Update tools will fail.")
        NaturalLanguageInventoryProcessor = None
        TasteProfileProcessor = None
        SavedMealsProcessor = None
        ShoppingListProcessor = None
        DailyNotesProcessor = None


    # --- Tool Definitions (imported from extracted_tool package) ---
    from extracted_tool.pull import (
        get_inventory_context,
        get_taste_profile_context,
        get_saved_meals_context,
        get_shopping_list_context,
        get_daily_notes_context,
        get_new_meal_ideas_context,
        get_instock_meals_context,
        get_ingredients_info_context,
    )
    from extracted_tool.push import (
        update_inventory,
        update_taste_profile,
        update_saved_meals,
        update_shopping_list,
        update_daily_plan,
    )

