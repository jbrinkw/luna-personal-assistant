import re
import config
from db_functions import (
    get_saved_meals,
    get_meal_ideas,
    get_meal_ideas_in_stock,
    get_saved_meals_in_stock,
)
from langchain_openai import ChatOpenAI

class MealPlanner:
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.llm_model = "o3-mini"
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
            
    def analyze_inventory_restriction(self, message: str) -> bool:
        """
        Uses an agent to determine if meals should be restricted to current inventory.
        Returns True if user wants meals from current inventory or False if planning for later.
        
        Args:
            message (str): The user's message to analyze
            
        Returns:
            bool: True if should restrict to current inventory, False if planning for later
        """
        # Create a separate chat instance with gpt-4-mini model
        inventory_chat = ChatOpenAI(
            model="gpt-4-mini",
            openai_api_key=self.api_key
        )
        
        prompt_template = (
            "Analyze this message and determine if the user wants meal suggestions "
            "only from their current inventory or if they're planning meals for later.\n\n"
            "Message: {message}\n\n"
            "Respond with exactly 'current' if they want meals from current inventory, "
            "or 'later' if they're planning ahead or didn't specify."
        )
        
        formatted_prompt = prompt_template.format(message=message.strip())
        
        try:
            response = inventory_chat.invoke(formatted_prompt)
            return response.content.strip().lower() == 'current'
        except Exception as e:
            # Default to showing all meals if there's an error
            return False
    def pick_meals(self, restrict_inventory: bool):
        """
        Retrieve meals from the databases and separate them.
        If restrict_inventory is True, returns only meals with available ingredients.
        Otherwise returns both available and unavailable meals.
        """
        meal_ideas = get_meal_ideas()
        meal_ideas_stock = get_meal_ideas_in_stock()
        saved_meals = get_saved_meals()
        saved_meals_stock = get_saved_meals_in_stock()

        meals_available = []
        meals_unavailable = []

        # Process meal ideas
        for meal in meal_ideas:
            if meal[0] in meal_ideas_stock:
                meals_available.append((meal[1], meal[2], meal[3]))  # name, cook time, ingredients
            else:
                meals_unavailable.append((meal[1], meal[2], meal[3]))
        # Process saved meals
        for meal in saved_meals:
            if meal[0] in saved_meals_stock:
                meals_available.append((meal[1], meal[2], meal[3]))
            else:
                meals_unavailable.append((meal[1], meal[2], meal[3]))

        if restrict_inventory:
            return meals_available, []
        else:
            return meals_available, meals_unavailable

    def generate_meal_plan(self, conversation_history: str) -> str:
        """
        Based on the conversation history:
         1. Determines if meals should be restricted to available components.
         2. Picks meal lists accordingly.
         3. Inspects the user's last message for how many meals to plan (default: 3).
         4. Sends the meal lists and user request to the model.
        Returns a string with the selected meal details.
        """
        # Determine inventory restriction from the user's intent
        restrict_inventory = self.analyze_inventory_restriction(conversation_history)        
        meals_available, meals_unavailable = self.pick_meals(restrict_inventory)


        # Build meal list string for the AI prompt
        if restrict_inventory:
            meal_list_str = "\n".join(
                [f"{meal[0]} ({meal[1]}) - Ingredients: {meal[2]}" for meal in meals_available]
            )
        else:
            available_str = "\n".join(
                [f"{meal[0]} ({meal[1]}) - Ingredients: {meal[2]}" for meal in meals_available]
            )
            unavailable_str = "\n".join(
                [f"{meal[0]} ({meal[1]}) - Ingredients: {meal[2]}" for meal in meals_unavailable]
            )
            meal_list_str = (
                f"Available Meals:\n{available_str}\n\nUnavailable Meals:\n{unavailable_str}"
            )

        # Create prompt for the AI
        prompt_template = (
            "Review this conversation history:\n{conversation_history}\n\n"
            "Given these available meals:\n{meal_list}\n\n"
            "Based on the ENTIRE conversation but focusing on their last request,\n"
            "select appropriate meals that best match their needs. If they didn't specify "
            "a number of meals, suggest 3 meals.\n"
            "Return the meal details in plain text format. Don't use any markdown or special formatting."
        )
        formatted_prompt = prompt_template.format(
            conversation_history=conversation_history,
            meal_list=meal_list_str,
        )
        try:
            response = self.chat.invoke(formatted_prompt)
            return response.content.strip()
        except Exception as e:
            return "Error generating meal plan: " + str(e)

# Example usage:
if __name__ == "__main__":
    conversation_history = (
        "User: Please plan 4 meals. high protein and easy to make"
    )
    planner = MealPlanner()
    meal_plan = planner.generate_meal_plan(conversation_history)
    print("Meal Plan:")
    print(meal_plan)