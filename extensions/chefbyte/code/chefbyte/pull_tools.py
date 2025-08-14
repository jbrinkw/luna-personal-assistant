"""Tools for retrieving context information from the database.

Each function opens a temporary connection, collects the
requested data using the ``PullHelper`` utility class and
returns a plain string summary for the agent to use.
"""

from fastmcp import FastMCP
from db.db_functions import with_db
from helpers.pull_helper import PullHelper
import traceback

# Create a dedicated MCP server for pull/query tools
mcp = FastMCP("ChefByte Pull Tools")


@mcp.tool
@with_db
def get_inventory_context(db, tables) -> str:
    """Retrieve a summary of the current kitchen inventory.

    Returns:
        A plain text listing of items and amounts on hand.
    """
    print("[Tool Called] get_inventory_context")
    try:
        pull_helper = PullHelper(db, tables)
        return pull_helper.get_inventory_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_inventory_context' failed: {e}")
        return f"Error during inventory retrieval: {str(e)}"


@mcp.tool
@with_db
def get_taste_profile_context(db, tables) -> str:
    """Get the saved taste profile.

    Returns:
        A description of likes, dislikes and dietary restrictions.
    """
    print("[Tool Called] get_taste_profile_context")
    try:
        pull_helper = PullHelper(db, tables)
        return pull_helper.get_taste_profile_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_taste_profile_context' failed: {e}")
        return f"Error retrieving taste profile: {str(e)}"


@mcp.tool
@with_db
def get_saved_meals_context(db, tables) -> str:
    """List stored meals and recipes.

    Returns:
        Text summary of all meals saved by the user.
    """
    print("[Tool Called] get_saved_meals_context")
    try:
        pull_helper = PullHelper(db, tables)
        return pull_helper.get_saved_meals_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_saved_meals_context' failed: {e}")
        return f"Error retrieving saved meals: {str(e)}"


@mcp.tool
@with_db
def get_shopping_list_context(db, tables) -> str:
    """Retrieve the current shopping list.

    Returns:
        Plain text list of ingredients and quantities to purchase.
    """
    print("[Tool Called] get_shopping_list_context")
    try:
        pull_helper = PullHelper(db, tables)
        return pull_helper.get_shopping_list_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_shopping_list_context' failed: {e}")
        return f"Error during shopping list retrieval: {str(e)}"


@mcp.tool
@with_db
def get_daily_notes_context(db, tables) -> str:
    """Get the meal plan for the upcoming week.

    Returns:
        A text summary of planned meals and notes for the next seven days.
    """
    print("[Tool Called] get_daily_notes_context")
    try:
        pull_helper = PullHelper(db, tables)
        return pull_helper.get_daily_notes_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_daily_notes_context' failed: {e}")
        print(traceback.format_exc())
        return "Error retrieving daily meal plans."


@mcp.tool
@with_db
def get_new_meal_ideas_context(db, tables) -> str:
    """List previously generated meal ideas.

    Returns:
        A newline-separated list of stored suggestions.
    """
    print("[Tool Called] get_new_meal_ideas_context")
    try:
        pull_helper = PullHelper(db, tables)
        return pull_helper.get_new_meal_ideas_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_new_meal_ideas_context' failed: {e}")
        return f"Error retrieving new meal ideas: {str(e)}"


@mcp.tool
@with_db
def get_instock_meals_context(db, tables) -> str:
    """Find meals that can be prepared with current inventory.

    Returns:
        Text listing of saved and new meals possible with ingredients on hand.
    """
    print("[Tool Called] get_instock_meals_context")
    try:
        pull_helper = PullHelper(db, tables)
        return pull_helper.get_instock_meals_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_instock_meals_context' failed: {e}")
        return f"Error retrieving in-stock meals: {str(e)}"


@mcp.tool
@with_db
def get_ingredients_info_context(db, tables) -> str:
    """Provide general information about ingredients.

    Returns:
        Tips such as purchase amounts or reference links for ingredients.
    """
    print("[Tool Called] get_ingredients_info_context")
    try:
        pull_helper = PullHelper(db, tables)
        return pull_helper.get_ingredients_info_context()
    except Exception as e:
        print(f"[ERROR] Tool 'get_ingredients_info_context' failed: {e}")
        return f"Error retrieving ingredients information: {str(e)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the ChefByte Pull Tools MCP server",
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
        default=8020,
        help="Port to run the server on (default: 8020)",
    )
    args = parser.parse_args()

    # Compute and log the access URL
    if args.transport == "sse":
        url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
    elif args.transport == "http":
        url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/mcp"
    else:
        url = "stdio"
    print(f"[ChefByte Pull Tools] Running via {args.transport.upper()} at {url}")
    mcp.run(transport=args.transport, host=args.host, port=args.port)
