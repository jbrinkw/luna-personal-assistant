"""High-level action tools that orchestrate complex tasks.

These wrappers delegate to specialized engines such as the
meal planner, suggestion generator and meal ideation engine.
They maintain short-lived database connections and return the
final text result produced by those engines.
"""

from . import mcp
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
