from agents import function_tool
from db.db_functions import processor_session
from helpers.push_helpers.inventory_processor import NaturalLanguageInventoryProcessor
from helpers.push_helpers.taste_profile_processor import TasteProfileProcessor
from helpers.push_helpers.saved_meals_processor import SavedMealsProcessor
from helpers.push_helpers.shopping_list_processor import ShoppingListProcessor
from helpers.push_helpers.daily_notes_processor import DailyNotesProcessor
import traceback

@function_tool
def update_inventory(user_input: str) -> str:
    """Update kitchen inventory using natural language instructions.

    **Input:** user_input - instructions describing inventory changes.
    **Output:** Confirmation string describing the applied updates or an error message.
    """
    print(f"[Tool Called] update_inventory with input: '{user_input}'")
    try:
        with processor_session(NaturalLanguageInventoryProcessor, 'inventory', verbose=False) as proc:
            _, confirmation = proc.process_inventory_changes(user_input)
            return confirmation
    except Exception as e:
        print(f"[ERROR] Tool 'update_inventory' failed: {e}\n{traceback.format_exc()}")
        return f"An error occurred while processing inventory changes: {str(e)}"


@function_tool
def update_taste_profile(user_request: str) -> str:
    """Modify the user's taste profile text.

    **Input:** user_request - new profile details or instructions.
    **Output:** Confirmation text or an error message.
    """
    print(f"[Tool Called] update_taste_profile with input: '{user_request}'")
    try:
        with processor_session(TasteProfileProcessor, 'taste_profile', verbose=False) as proc:
            _, confirmation = proc.update_taste_profile(user_request)
            return confirmation
    except Exception as e:
        print(f"[ERROR] Tool 'update_taste_profile' failed: {e}\n{traceback.format_exc()}")
        return f"An error occurred while updating the taste profile: {str(e)}"


@function_tool
def update_saved_meals(user_input: str) -> str:
    """Add, update, or delete saved meals.

    **Input:** user_input - instructions describing meal changes.
    **Output:** Confirmation string or an error message.
    """
    print(f"[Tool Called] update_saved_meals with input: '{user_input}'")
    try:
        with processor_session(SavedMealsProcessor, 'saved_meals', verbose=False) as proc:
            _, confirmation = proc.process_saved_meals_changes(user_input)
            return confirmation
    except Exception as e:
        print(f"[ERROR] Tool 'update_saved_meals' failed: {e}\n{traceback.format_exc()}")
        return f"An error occurred while processing saved meals changes: {str(e)}"


@function_tool
def update_shopping_list(user_input: str) -> str:
    """Modify the shopping list based on natural language instructions.

    **Input:** user_input - requested list changes.
    **Output:** Confirmation text or an error message.
    """
    print(f"[Tool Called] update_shopping_list with input: '{user_input}'")
    try:
        with processor_session(ShoppingListProcessor, 'shopping_list', verbose=False) as proc:
            _, confirmation = proc.process_shopping_list_changes(user_input)
            return confirmation
    except Exception as e:
        print(f"[ERROR] Tool 'update_shopping_list' failed: {e}\n{traceback.format_exc()}")
        return f"An error occurred while processing shopping list changes: {str(e)}"


@function_tool
def update_daily_plan(user_input: str) -> str:
    """Add, update, or clear items in the daily meal plan.

    **Input:** user_input - instructions describing planner changes.
    **Output:** Confirmation string or an error message.
    """
    print(f"[Tool Called] update_daily_plan with input: '{user_input}'")
    try:
        with processor_session(DailyNotesProcessor, 'daily_planner', verbose=False) as proc:
            _, confirmation = proc.process_daily_notes_changes(user_input)
            return confirmation
    except Exception as e:
        print(f"[ERROR] Tool 'update_daily_plan' failed: {e}\n{traceback.format_exc()}")
        return f"An error occurred while processing daily plan changes: {str(e)}"
