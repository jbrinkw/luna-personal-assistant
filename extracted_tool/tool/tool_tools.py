from agents import function_tool
from langchain.schema import HumanMessage
from db.db_functions import db_session
from tools.meal_planner import MealPlanningTool
from tools.meal_suggestion_gen import generate_meal_suggestions as original_generate_suggestions
from tools.new_meal_ideation import MealIdeationEngine
import traceback

@function_tool
def run_meal_planner(user_request: str) -> str:
    """Execute the MealPlanningTool to generate or select meals.

    **Input:** user_request - planning instructions.
    **Output:** Text summarizing generated intents or selected meals, or an error message.
    """
    try:
        with db_session(verbose=False) as (db, tables):
            planner = MealPlanningTool(db, tables)
            minimal_history = [HumanMessage(content=user_request)]
            return planner.execute(minimal_history)
    except Exception as e:
        print(f"[ERROR] in run_meal_planner: {e}")
        traceback.print_exc()
        return f"Sorry, an error occurred during meal planning: {e}"


@function_tool
def run_meal_suggestion_generator(user_request: str) -> str:
    """Generate meal suggestions based on preferences and inventory.

    **Input:** user_request - description of desired meals or filters.
    **Output:** Formatted list of suggested meals or an error message.
    """
    print(f"[Tool Wrapper] run_meal_suggestion_generator called with: {user_request[:100]}...")
    try:
        minimal_history = [HumanMessage(content=user_request)]
        return original_generate_suggestions(minimal_history)
    except Exception as e:
        print(f"[ERROR] in run_meal_suggestion_generator: {e}")
        traceback.print_exc()
        return f"Sorry, an error occurred while generating meal suggestions: {e}"


@function_tool
def run_new_meal_ideator(user_request: str) -> str:
    """Create new meal ideas or full recipes with MealIdeationEngine.

    **Input:** user_request - details about the desired ideas or recipes.
    **Output:** Generated ideas, recipes, or confirmation text.
    """
    print(f"[Tool Wrapper] run_new_meal_ideator called with: {user_request[:100]}...")
    try:
        with db_session(verbose=False) as (db, tables):
            engine = MealIdeationEngine(db, tables)
            minimal_history = [HumanMessage(content=user_request)]
            return engine.execute(minimal_history)
    except Exception as e:
        print(f"[ERROR] in run_new_meal_ideator: {e}")
        traceback.print_exc()
        return f"Sorry, an error occurred during meal ideation: {e}"


@function_tool
def mealPlanning_layer1(user_request: str) -> str:
    """Generate meal planning intents only (layer 1).

    **Input:** user_request - date range and preferences.
    **Output:** Short meal intents or an error message.
    """
    try:
        with db_session(verbose=False) as (db, tables):
            planner = MealPlanningTool(db, tables)
            history = [HumanMessage(content=user_request)]
            return planner.execute(history)
    except Exception as e:
        print(f"[ERROR] mealPlanning_layer1 failed: {e}")
        traceback.print_exc()
        return "Error generating meal plan."


@function_tool
def mealPlanning_layer2(user_request: str) -> str:
    """Select actual meals for generated intents (layer 2).

    **Input:** user_request - selection instructions.
    **Output:** Meal selection summary or an error message.
    """
    try:
        with db_session(verbose=False) as (db, tables):
            planner = MealPlanningTool(db, tables)
            history = [HumanMessage(content=user_request)]
            return planner.execute(history)
    except Exception as e:
        print(f"[ERROR] mealPlanning_layer2 failed: {e}")
        traceback.print_exc()
        return "Error selecting meals."


@function_tool
def mealIdeation_layer1(user_request: str) -> str:
    """Generate high-level meal ideas (layer 1).

    **Input:** user_request - criteria for ideas.
    **Output:** List of numbered meal ideas or an error message.
    """
    try:
        with db_session(verbose=False) as (db, tables):
            engine = MealIdeationEngine(db, tables)
            history = [HumanMessage(content=user_request)]
            return engine.generate_meal_descriptions(history, limit_to_inventory=False)
    except Exception as e:
        print(f"[ERROR] mealIdeation_layer1 failed: {e}")
        traceback.print_exc()
        return "Error generating meal ideas."


@function_tool
def mealIdeation_layer2(user_request: str, selections: str = "") -> str:
    """Generate full recipes for selected ideas (layer 2).

    **Input:** user_request - original request; selections - idea numbers to expand.
    **Output:** One or more recipes or an error message.
    """
    try:
        with db_session(verbose=False) as (db, tables):
            engine = MealIdeationEngine(db, tables)
            selected_numbers = [int(s) for s in selections.split() if s.isdigit()]
            history = [HumanMessage(content=user_request)]
            return engine.generate_recipes(history, selected_numbers, limit_to_inventory=False)
    except Exception as e:
        print(f"[ERROR] mealIdeation_layer2 failed: {e}")
        traceback.print_exc()
        return "Error generating recipes."


@function_tool
def mealIdeation_layer3(user_request: str, selections: str = "") -> str:
    """Save user-selected recipes to the database (layer 3).

    **Input:** user_request - original request; selections - recipe numbers to save.
    **Output:** Confirmation text or an error message.
    """
    try:
        with db_session(verbose=False) as (db, tables):
            engine = MealIdeationEngine(db, tables)
            nums = [int(s) for s in selections.split() if s.isdigit()]
            _, msg = engine.save_recipes(nums)
            return msg
    except Exception as e:
        print(f"[ERROR] mealIdeation_layer3 failed: {e}")
        traceback.print_exc()
        return "Error saving recipes."
