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

    # --- Tool Definitions ---

    @function_tool
    def get_inventory_context() -> str:
        """Fetches the user's current kitchen inventory from the database. 
        Use this tool when the user asks what food they have, about specific items in their inventory, 
        or when context about available ingredients is needed for other tasks like meal planning.
        """
        print("[Tool Called] get_inventory_context")
        db = None
        if PullHelper is None: return "Error: PullHelper failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            pull_helper = PullHelper(db, tables)
            result = pull_helper.get_inventory_context()
            return result
        except Exception as e:
            print(f"[ERROR] Tool 'get_inventory_context' failed: {e}")
            # Ensure the original error message is preserved if PullHelper failed internally
            return f"Error during inventory retrieval: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def update_inventory(user_input: str) -> str:
        """Processes updates to the user's kitchen inventory based on natural language input. 
        Use this tool when the user explicitly states they have added, removed, used, or finished an item, 
        or wants to set/update an expiration date. 
        Example phrases: 'I bought milk', 'Add 2 apples', 'I used 3 eggs', 'Set expiration for chicken to next Tuesday'.
        Args:
            user_input: The user's message describing the inventory changes.
        Returns:
            A string confirming the changes made or reporting any errors.
        """
        print(f"[Tool Called] update_inventory with input: '{user_input}'")
        db = None
        if NaturalLanguageInventoryProcessor is None: return "Error: InventoryProcessor failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            processor = NaturalLanguageInventoryProcessor(tables['inventory'], db)
            result, confirmation = processor.process_inventory_changes(user_input)
            return confirmation
        except Exception as e:
            print(f"[ERROR] Tool 'update_inventory' failed: {e}")
            print(traceback.format_exc())
            return f"An error occurred while processing inventory changes: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def get_taste_profile_context() -> str:
        """Fetches the user's saved taste profile, including likes, dislikes, dietary restrictions, and allergies.
        Use this tool when the user asks about their preferences or restrictions.
        """
        print("[Tool Called] get_taste_profile_context")
        db = None
        if PullHelper is None: return "Error: PullHelper failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            pull_helper = PullHelper(db, tables)
            return pull_helper.get_taste_profile_context()
        except Exception as e:
            print(f"[ERROR] Tool 'get_taste_profile_context' failed: {e}")
            return f"Error retrieving taste profile: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def get_saved_meals_context() -> str:
        """Fetches the list of meals the user has saved previously, including name, ID, prep time, and ingredients.
        Use this tool when the user asks about their saved recipes or meals.
        """
        print("[Tool Called] get_saved_meals_context")
        db = None
        if PullHelper is None: return "Error: PullHelper failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            pull_helper = PullHelper(db, tables)
            return pull_helper.get_saved_meals_context()
        except Exception as e:
            print(f"[ERROR] Tool 'get_saved_meals_context' failed: {e}")
            return f"Error retrieving saved meals: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def get_shopping_list_context() -> str:
        """Fetches the user's current shopping list.
        Use this tool when the user asks what is on their shopping list or what they need to buy.
        """
        print("[Tool Called] get_shopping_list_context")
        db = None
        if PullHelper is None: return "Error: PullHelper failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            pull_helper = PullHelper(db, tables)
            result = pull_helper.get_shopping_list_context()
            return result
        except Exception as e:
            print(f"[ERROR] Tool 'get_shopping_list_context' failed: {e}")
            return f"Error during shopping list retrieval: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def get_daily_notes_context() -> str:
        """Fetches the user's meal plan for the upcoming week (next 7 days).
        Use this tool when the user asks about their meal plan, schedule, or what they are cooking on specific upcoming days.
        """
        print("[Tool Called] get_daily_notes_context")
        db = None
        if PullHelper is None: return "Error: PullHelper failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            pull_helper = PullHelper(db, tables)
            return pull_helper.get_daily_notes_context()
        except Exception as e:
            print(f"[ERROR] Tool 'get_daily_notes_context' failed: {e}")
            print(traceback.format_exc())
            return "Error retrieving daily meal plans."
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def get_new_meal_ideas_context() -> str:
        """Fetches the list of new meal ideas that have been previously generated or suggested.
        Use this tool when the user asks for new ideas or wants to see past suggestions.
        """
        print("[Tool Called] get_new_meal_ideas_context")
        db = None
        if PullHelper is None: return "Error: PullHelper failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            pull_helper = PullHelper(db, tables)
            return pull_helper.get_new_meal_ideas_context()
        except Exception as e:
            print(f"[ERROR] Tool 'get_new_meal_ideas_context' failed: {e}")
            return f"Error retrieving new meal ideas: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def get_instock_meals_context() -> str:
        """Fetches lists of both saved meals and new meal ideas that can be made with the current inventory.
        Use this tool when the user asks what they can make *right now* with the ingredients they have.
        """
        print("[Tool Called] get_instock_meals_context")
        db = None
        if PullHelper is None: return "Error: PullHelper failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            pull_helper = PullHelper(db, tables)
            return pull_helper.get_instock_meals_context()
        except Exception as e:
            print(f"[ERROR] Tool 'get_instock_meals_context' failed: {e}")
            return f"Error retrieving in-stock meals: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def get_ingredients_info_context() -> str:
        """Fetches general information about known ingredients, such as minimum purchase amounts or store links.
        Use this tool when the user asks for general information about an ingredient, not about their current stock.
        """
        print("[Tool Called] get_ingredients_info_context")
        db = None
        if PullHelper is None: return "Error: PullHelper failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            pull_helper = PullHelper(db, tables)
            return pull_helper.get_ingredients_info_context()
        except Exception as e:
            print(f"[ERROR] Tool 'get_ingredients_info_context' failed: {e}")
            return f"Error retrieving ingredients information: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    # --- Update Tool Definitions --- 
    @function_tool
    def update_taste_profile(user_request: str) -> str:
        """Updates the user's taste profile based on their request (e.g., adding likes/dislikes, allergies, dietary restrictions).
        Args:
            user_request: The user's natural language request describing the changes.
        Returns:
            A string confirming the update or stating no changes were made.
        """
        print(f"[Tool Called] update_taste_profile with input: '{user_request}'")
        db = None
        if TasteProfileProcessor is None: return "Error: TasteProfileProcessor failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            processor = TasteProfileProcessor(tables['taste_profile'])
            result, confirmation = processor.update_taste_profile(user_request)
            return confirmation
        except Exception as e:
            print(f"[ERROR] Tool 'update_taste_profile' failed: {e}")
            print(traceback.format_exc())
            return f"An error occurred while updating the taste profile: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def update_saved_meals(user_input: str) -> str:
        """Adds, updates, or deletes saved meals/recipes based on user instructions.
        Use for requests like 'save this recipe', 'update the lasagna recipe', 'delete the pizza meal'.
        Args:
            user_input: The user's natural language request describing the changes.
        Returns:
            A string confirming the changes made or reporting any errors.
        """
        print(f"[Tool Called] update_saved_meals with input: '{user_input}'")
        db = None
        if SavedMealsProcessor is None: return "Error: SavedMealsProcessor failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            processor = SavedMealsProcessor(tables['saved_meals'], db)
            result, confirmation = processor.process_saved_meals_changes(user_input)
            return confirmation
        except Exception as e:
            print(f"[ERROR] Tool 'update_saved_meals' failed: {e}")
            print(traceback.format_exc())
            return f"An error occurred while processing saved meals changes: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def update_shopping_list(user_input: str) -> str:
        """Adds, removes, or clears items from the shopping list.
        Use for requests like 'add milk to my list', 'remove eggs', 'clear my shopping list'.
        Args:
            user_input: The user's natural language request describing the changes.
        Returns:
            A string confirming the changes made or reporting any errors.
        """
        print(f"[Tool Called] update_shopping_list with input: '{user_input}'")
        db = None
        if ShoppingListProcessor is None: return "Error: ShoppingListProcessor failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            processor = ShoppingListProcessor(tables['shopping_list'], tables['ingredients_foods'], db)
            result, confirmation = processor.process_shopping_list_changes(user_input)
            return confirmation
        except Exception as e:
            print(f"[ERROR] Tool 'update_shopping_list' failed: {e}")
            print(traceback.format_exc())
            return f"An error occurred while processing shopping list changes: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)

    @function_tool
    def update_daily_plan(user_input: str) -> str:
        """Adds, updates, or clears the daily meal plan for specified dates.
        Use for requests like 'plan lasagna for Friday', 'add a note to tomorrow', 'clear Wednesday's plan', 'remove pasta from Tuesday'.
        Args:
            user_input: The user's natural language request describing the changes.
        Returns:
            A string confirming the changes made or reporting any errors.
        """
        print(f"[Tool Called] update_daily_plan with input: '{user_input}'")
        db = None
        if DailyNotesProcessor is None: return "Error: DailyNotesProcessor failed to import."
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables: raise ConnectionError("DB init failed.")
            processor = DailyNotesProcessor(tables['daily_planner'], tables['saved_meals'], db)
            result, confirmation = processor.process_daily_notes_changes(user_input)
            return confirmation
        except Exception as e:
            print(f"[ERROR] Tool 'update_daily_plan' failed: {e}")
            print(traceback.format_exc())
            return f"An error occurred while processing daily plan changes: {str(e)}"
        finally:
            if db and db.conn: db.disconnect(verbose=False)