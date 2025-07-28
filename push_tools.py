"""Tools for updating database records.

These functions process natural language requests to modify
ChefByte's data tables. Each tool initializes a database
connection, delegates parsing and update logic to helper
classes, and returns a confirmation string describing the
changes made.
"""

from fastmcp import FastMCP
from db.db_functions import with_db
from helpers.push_helpers.inventory_processor import NaturalLanguageInventoryProcessor
from helpers.push_helpers.taste_profile_processor import TasteProfileProcessor
from helpers.push_helpers.saved_meals_processor import SavedMealsProcessor
from helpers.push_helpers.shopping_list_processor import ShoppingListProcessor
from helpers.push_helpers.daily_notes_processor import DailyNotesProcessor
import traceback

# Create a dedicated MCP server for push/update tools
mcp = FastMCP("ChefByte Push Tools")


@mcp.tool
@with_db
def update_inventory(db, tables, user_input: str) -> str:
    """Update the kitchen inventory.

    Args:
        user_input: Natural language description of inventory changes such as
            items added, removed or used.

    Returns:
        Confirmation text summarizing the updates that were applied.
    """
    print(f"[Tool Called] update_inventory with input: '{user_input}'")
    try:
        processor = NaturalLanguageInventoryProcessor(tables['inventory'], db)
        _, confirmation = processor.process_inventory_changes(user_input)
        return confirmation
    except Exception as e:
        print(f"[ERROR] Tool 'update_inventory' failed: {e}")
        print(traceback.format_exc())
        return f"An error occurred while processing inventory changes: {str(e)}"


@mcp.tool
@with_db
def update_taste_profile(db, tables, user_request: str) -> str:
    """Adjust the saved taste profile.

    Args:
        user_request: Natural language instructions describing likes,
            dislikes or dietary changes.

    Returns:
        A confirmation message summarizing the profile updates.
    """
    print(f"[Tool Called] update_taste_profile with input: '{user_request}'")
    try:
        processor = TasteProfileProcessor(tables['taste_profile'])
        _, confirmation = processor.update_taste_profile(user_request)
        return confirmation
    except Exception as e:
        print(f"[ERROR] Tool 'update_taste_profile' failed: {e}")
        print(traceback.format_exc())
        return f"An error occurred while updating the taste profile: {str(e)}"


@mcp.tool
@with_db
def update_saved_meals(db, tables, user_input: str) -> str:
    """Manage saved meals.

    Args:
        user_input: Natural language request describing which recipes to add,
            update or remove.

    Returns:
        Confirmation text detailing the changes made to the saved meals list.
    """
    print(f"[Tool Called] update_saved_meals with input: '{user_input}'")
    try:
        processor = SavedMealsProcessor(tables['saved_meals'], db)
        _, confirmation = processor.process_saved_meals_changes(user_input)
        return confirmation
    except Exception as e:
        print(f"[ERROR] Tool 'update_saved_meals' failed: {e}")
        print(traceback.format_exc())
        return f"An error occurred while processing saved meals changes: {str(e)}"


@mcp.tool
@with_db
def update_shopping_list(db, tables, user_input: str) -> str:
    """Modify the shopping list.

    Args:
        user_input: Text describing items to add, remove or clear from the list.

    Returns:
        Confirmation describing the final state of the shopping list.
    """
    print(f"[Tool Called] update_shopping_list with input: '{user_input}'")
    try:
        processor = ShoppingListProcessor(tables['shopping_list'], tables['ingredients_foods'], db)
        _, confirmation = processor.process_shopping_list_changes(user_input)
        return confirmation
    except Exception as e:
        print(f"[ERROR] Tool 'update_shopping_list' failed: {e}")
        print(traceback.format_exc())
        return f"An error occurred while processing shopping list changes: {str(e)}"


@mcp.tool
@with_db
def update_daily_plan(db, tables, user_input: str) -> str:
    """Modify entries in the daily meal plan.

    Args:
        user_input: Natural language request mentioning meals or notes to add,
            change or remove for particular days.

    Returns:
        Confirmation describing what updates were made to the plan.
    """
    print(f"[Tool Called] update_daily_plan with input: '{user_input}'")
    try:
        processor = DailyNotesProcessor(tables['daily_planner'], tables['saved_meals'], db)
        _, confirmation = processor.process_daily_notes_changes(user_input)
        return confirmation
    except Exception as e:
        print(f"[ERROR] Tool 'update_daily_plan' failed: {e}")
        print(traceback.format_exc())
        return f"An error occurred while processing daily plan changes: {str(e)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the ChefByte Push Tools MCP server",
    )
    parser.add_argument(
        "--transport",
        default="sse",
        choices=["http", "stdio", "sse"],
        help="Transport protocol to use (default: sse)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8010,
        help="Port to run the server on (default: 8010)",
    )
    args = parser.parse_args()

    # Compute and log the access URL for convenience
    if args.transport == "sse":
        url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
    elif args.transport == "http":
        url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/mcp"
    else:
        url = "stdio (process stdio)"
    print(f"[ChefByte Push Tools] Running via {args.transport.upper()} at {url}")

    mcp.run(transport=args.transport, host=args.host, port=args.port)
