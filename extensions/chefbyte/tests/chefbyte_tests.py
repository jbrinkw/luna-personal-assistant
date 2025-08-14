from test_proxy import TestRunner
import subprocess

def main():
    """Run ChefByte tests for MCP tool coverage"""

    # Reset database with sample data
    subprocess.run(["python", "chefbyte/debug/reset_db.py"], check=True)

    prompt_sets = [
        {
            "name": "Get Inventory Context Test",
            "description": "Test retrieving kitchen inventory using get_inventory_context tool",
            "prompts": [
                "Show my kitchen inventory."
            ]
        },
        {
            "name": "Get Taste Profile Context Test",
            "description": "Test retrieving saved taste preferences using get_taste_profile_context tool",
            "prompts": [
                "What is my taste profile?"
            ]
        },
        {
            "name": "Get Saved Meals Context Test",
            "description": "Test retrieving stored meals using get_saved_meals_context tool",
            "prompts": [
                "List my saved meals."
            ]
        },
        {
            "name": "Get Shopping List Context Test",
            "description": "Test retrieving shopping list using get_shopping_list_context tool",
            "prompts": [
                "What is on my shopping list?"
            ]
        },
        {
            "name": "Get Daily Notes Context Test",
            "description": "Test retrieving weekly meal plan using get_daily_notes_context tool. There will only be a few meals.",
            "prompts": [
                "Show my meal plan for the week."
            ]
        },
        {
            "name": "Get Instock Meals Context Test",
            "description": "Test retrieving meals possible with current inventory using get_instock_meals_context tool",
            "prompts": [
                "What meals can I make with what I have?"
            ]
        },
        {
            "name": "Get Ingredients Info Context Test",
            "description": "Test retrieving ingredient tips using get_ingredients_info_context tool",
            "prompts": [
                "Provide ingredient tips."
            ]
        },
        {
            "name": "Update Inventory Test",
            "description": "Test updating inventory using update_inventory tool",
            "prompts": [
                "Add two apples to my inventory."
            ]
        },
        {
            "name": "Update Taste Profile Test",
            "description": "Test updating taste profile using update_taste_profile tool",
            "prompts": [
                "I now prefer spicy food."
            ]
        },
        {
            "name": "Update Saved Meals Test",
            "description": "Test saving a meal using update_saved_meals tool",
            "prompts": [
                "Save grilled cheese sandwich. It takes 10 minutes to make. Ingredients: 2 slices bread, 2 slices cheese, 1 tbsp butter. Recipe: Butter the bread, add cheese, cook in pan until golden brown."
            ]
        },
        {
            "name": "Update Shopping List Test",
            "description": "Test modifying shopping list using update_shopping_list tool",
            "prompts": [
                "Add milk to my shopping list."
            ]
        },
        {
            "name": "Update Daily Plan Test",
            "description": "Test updating daily meal plan using update_daily_plan tool",
            "prompts": [
                "Schedule pasta for tomorrow."
            ]
        },
        {
            "name": "Run Meal Planner Test",
            "description": "Test executing meal planning workflow using run_meal_planner tool",
            "prompts": [
                "i want to plan some meals for today. something quick and easy",
                "yes"
            ]
        },
        {
            "name": "Run Meal Suggestion Generator Test",
            "description": "Test generating meal suggestions using run_meal_suggestion_generator tool",
            "prompts": [
                "Suggest a dinner using chicken."
            ]
        },
        {
            "name": "Run New Meal Ideator Test",
            "description": "Test generating creative new recipes using run_new_meal_ideator tool",
            "prompts": [
                "Invent a new quick and easy meal that is high protien.",
                "I like the first one",
                "yes save it"

            ]
        }
    ]

    runner = TestRunner()
    results = runner.run_tests(prompt_sets)
    return results

if __name__ == "__main__":
    main() 