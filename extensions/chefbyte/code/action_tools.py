"""High-level action tools that orchestrate complex tasks.

These wrappers delegate to specialized engines such as the
meal planner, suggestion generator and meal ideation engine.
They maintain short-lived database connections and return the
final text result produced by those engines.
"""

from fastmcp import FastMCP

# Create a dedicated MCP server for high-level action tools
mcp = FastMCP("ChefByte Action Tools")

from langchain.schema import HumanMessage
from db.db_functions import with_db
from tools.meal_planner import MealPlanningTool
from tools.meal_suggestion_gen import generate_meal_suggestions as original_generate_suggestions
from tools.new_meal_ideation import MealIdeationEngine
import traceback

@mcp.tool
@with_db
def run_meal_planner(db, tables, user_request: str) -> str:
    """Execute the multi-step meal planning workflow.

    Args:
        user_request: Instructions or questions about planning upcoming meals.

    Returns:
        The final plan text produced by the meal planner.
    """
    try:
        planner = MealPlanningTool(db, tables)
        minimal_history = [HumanMessage(content=user_request)]
        return planner.execute(minimal_history)
    except Exception as e:
        print(f"[ERROR] in run_meal_planner: {e}")
        traceback.print_exc()
        return f"Sorry, an error occurred during meal planning: {e}"


@mcp.tool
def run_meal_suggestion_generator(user_request: str) -> str:
    """Generate meal suggestions from user criteria.

    Args:
        user_request: A prompt describing desired meals or ingredient limits.

    Returns:
        A formatted string of meal suggestion text.
    """
    print(f"[Tool Wrapper] run_meal_suggestion_generator called with: {user_request[:100]}...")
    try:
        minimal_history = [HumanMessage(content=user_request)]
        result = original_generate_suggestions(minimal_history)
        return result
    except Exception as e:
        print(f"[ERROR] in run_meal_suggestion_generator: {e}")
        traceback.print_exc()
        return f"Sorry, an error occurred while generating meal suggestions: {e}"


@mcp.tool
@with_db
def run_new_meal_ideator(db, tables, user_request: str) -> str:
    """Generate creative new meal ideas or recipes.

    Args:
        user_request: Prompt describing desired concept or inspiration.

    Returns:
        The generated recipe or idea text.
    """
    print(f"[Tool Wrapper] run_new_meal_ideator called with: {user_request[:100]}...")
    try:
        engine = MealIdeationEngine(db, tables)
        minimal_history = [HumanMessage(content=user_request)]
        return engine.execute(minimal_history)
    except Exception as e:
        print(f"[ERROR] in run_new_meal_ideator: {e}")
        traceback.print_exc()
        return f"Sorry, an error occurred during meal ideation: {e}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the ChefByte Action Tools MCP server",
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
        default=8030,
        help="Port to run the server on (default: 8030)",
    )
    args = parser.parse_args()

    # Compute URL
    if args.transport == "sse":
        url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
    elif args.transport == "http":
        url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/mcp"
    else:
        url = "stdio"
    print(f"[ChefByte Action Tools] Running via {args.transport.upper()} at {url}")
    mcp.run(transport=args.transport, host=args.host, port=args.port)
