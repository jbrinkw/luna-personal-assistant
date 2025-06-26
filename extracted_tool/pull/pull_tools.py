from agents import function_tool
from db.db_functions import pull_helper_session
import traceback

@function_tool
def get_inventory_context() -> str:
    """Return a formatted string describing the user's current inventory.

    **Input:** None
    **Output:** Inventory summary as a string or an error message.
    """
    print("[Tool Called] get_inventory_context")
    try:
        with pull_helper_session(verbose=False) as pull_helper:
            return pull_helper.get_inventory_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_inventory_context' failed: {e}\n{traceback.format_exc()}")
        return f"Error during inventory retrieval: {str(e)}"


@function_tool
def get_taste_profile_context() -> str:
    """Return the user's taste profile information.

    **Input:** None
    **Output:** Taste profile string or error message.
    """
    print("[Tool Called] get_taste_profile_context")
    try:
        with pull_helper_session(verbose=False) as pull_helper:
            return pull_helper.get_taste_profile_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_taste_profile_context' failed: {e}")
        return f"Error retrieving taste profile: {str(e)}"


@function_tool
def get_saved_meals_context() -> str:
    """Return a list of saved meals with IDs and ingredients.

    **Input:** None
    **Output:** Saved meals summary or error message.
    """
    print("[Tool Called] get_saved_meals_context")
    try:
        with pull_helper_session(verbose=False) as pull_helper:
            return pull_helper.get_saved_meals_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_saved_meals_context' failed: {e}")
        return f"Error retrieving saved meals: {str(e)}"


@function_tool
def get_shopping_list_context() -> str:
    """Return the current shopping list items.

    **Input:** None
    **Output:** Formatted shopping list string or error message.
    """
    print("[Tool Called] get_shopping_list_context")
    try:
        with pull_helper_session(verbose=False) as pull_helper:
            return pull_helper.get_shopping_list_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_shopping_list_context' failed: {e}")
        return f"Error during shopping list retrieval: {str(e)}"


@function_tool
def get_daily_notes_context() -> str:
    """Return upcoming daily meal notes and plans.

    **Input:** None
    **Output:** Notes for the next few days or an error message.
    """
    print("[Tool Called] get_daily_notes_context")
    try:
        with pull_helper_session(verbose=False) as pull_helper:
            return pull_helper.get_daily_notes_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_daily_notes_context' failed: {e}\n{traceback.format_exc()}")
        return "Error retrieving daily meal plans."


@function_tool
def get_new_meal_ideas_context() -> str:
    """Return newly generated meal ideas not yet saved.

    **Input:** None
    **Output:** Text describing the meal ideas or error message.
    """
    print("[Tool Called] get_new_meal_ideas_context")
    try:
        with pull_helper_session(verbose=False) as pull_helper:
            return pull_helper.get_new_meal_ideas_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_new_meal_ideas_context' failed: {e}")
        return f"Error retrieving new meal ideas: {str(e)}"


@function_tool
def get_instock_meals_context() -> str:
    """Return meals that can be cooked with current inventory.

    **Input:** None
    **Output:** Text listing in-stock meals or an error message.
    """
    print("[Tool Called] get_instock_meals_context")
    try:
        with pull_helper_session(verbose=False) as pull_helper:
            return pull_helper.get_instock_meals_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_instock_meals_context' failed: {e}")
        return f"Error retrieving in-stock meals: {str(e)}"


@function_tool
def get_ingredients_info_context() -> str:
    """Return general ingredient information like minimum purchase and store links.

    **Input:** None
    **Output:** Ingredient information string or error message.
    """
    print("[Tool Called] get_ingredients_info_context")
    try:
        with pull_helper_session(verbose=False) as pull_helper:
            return pull_helper.get_ingredients_info_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_ingredients_info_context' failed: {e}")
        return f"Error retrieving ingredients information: {str(e)}"
