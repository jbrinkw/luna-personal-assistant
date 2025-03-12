#!/usr/bin/env python
import app.config as config
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.db_functions import get_inventory, get_taste_profile, get_saved_meals
from chat_processors.meal_database_manager import MealDBUpdater

class MealPreGenEngine:
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.llm_model = "o3-mini"
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        self.taste_profile = get_taste_profile()
        self.current_inventory = get_inventory()
        self.saved_meals = get_saved_meals()
        
        self.category_generation_prompt = (
            "You are a culinary AI helping generate personalized meal suggestions.\n"
            "Generate {num_meals} NEW meal ideas for category: {meal_category}\n\n"
            "Consider these two sources of user preferences:\n"
            "1. Taste Profile (general food preferences):\n{taste_profile}\n"
            "2. Saved Meals (specific meals the user enjoyed enough to save):\n{saved_meals}\n\n"
            "Using these preferences as inspiration:\n"
            "- Create new meals that match their taste profile\n"
            "- Take inspiration from elements of their saved meals they enjoy\n"
            "- DO NOT duplicate any saved meals\n"
            "- Suggest meals that use available ingredients when possible\n\n"
            "Current Inventory:\n{current_inventory}\n\n"
            "Don't use any special formatting; separate each meal suggestion with a new line.\n"
            "Format each suggestion as:\n"
            "Meal: <meal name>\n"
            "Ingredients: <item1, item2, ...>\n\n"
            "New Meal Ideas:"
        )
        
        # Updated validation prompt to preserve full meal details
        self.validation_prompt = (
            "Review and filter these meal suggestions to ensure they meet the requirements below:\n\n"
            "Category Requirements: {meal_category}\n\n"
            "User Preferences:\n"
            "1. Taste Profile:\n{taste_profile}\n"
            "2. Previously Enjoyed Meals:\n{saved_meals}\n\n"
            "Validation Rules:\n"
            "- Each meal must meet the category requirements\n"
            "- Should align with the taste profile preferences\n"
            "- Must be distinct from saved meals (no duplicates)\n"
            "- The response must include BOTH the meal name and the ingredients in the original format.\n\n"
            "Input Meal Suggestions:\n{meal_ideas}\n\n"
            "Valid New Meals (each meal should be formatted as follows):\n"
            "Meal: <meal name>\n"
            "Ingredients: <item1, item2, ...>\n\n"
            "Valid New Meals:"
        )

    def generate_meals_by_category(self, current_inventory: str, taste_profile: str, 
                                  meal_category: str, num_meals: int) -> str:
        prompt = ChatPromptTemplate.from_template(self.category_generation_prompt)
        formatted_prompt = prompt.format(
            num_meals=num_meals,
            meal_category=meal_category,
            current_inventory=current_inventory,
            taste_profile=taste_profile,
            saved_meals=self.saved_meals
        )
        
        print("\n=== GENERATION PROMPT ===")
        print(formatted_prompt)
        print("\n=== END GENERATION PROMPT ===\n")
        
        try:
            response = self.chat.invoke(formatted_prompt)
            print("\n=== GENERATION RESPONSE ===")
            print(response.content.strip())
            print("\n=== END GENERATION RESPONSE ===\n")
            return response.content.strip()
        except Exception as e:
            raise Exception(f"Error generating meals for {meal_category}: {str(e)}")

    def validate_meals(self, taste_profile: str, meal_category: str, meal_ideas: str) -> str:
        prompt = ChatPromptTemplate.from_template(self.validation_prompt)
        formatted_prompt = prompt.format(
            meal_category=meal_category,
            taste_profile=taste_profile,
            meal_ideas=meal_ideas,
            saved_meals=self.saved_meals
        )
        
        print("\n=== VALIDATION PROMPT ===")
        print(formatted_prompt)
        print("\n=== END VALIDATION PROMPT ===\n")
        
        try:
            response = self.chat.invoke(formatted_prompt)
            print("\n=== VALIDATION RESPONSE ===")
            print(response.content.strip())
            print("\n=== END VALIDATION RESPONSE ===\n")
            return response.content.strip()
        except Exception as e:
            raise Exception(f"Error validating meals: {str(e)}")
            
    def get_meal_suggestions_by_categories(self, categories: list[str], meals_per_category: int) -> dict:
        category_meals = {}
        for category in categories:
            print(f"Generating {meals_per_category} meal ideas for category: {category}")
            meal_ideas = self.generate_meals_by_category(
                current_inventory=self.current_inventory,
                taste_profile=self.taste_profile,
                meal_category=category,
                num_meals=meals_per_category
            )
            
            print(f"Validating meals for category: {category}")
            validated_meals = self.validate_meals(
                taste_profile=self.taste_profile,
                meal_category=category,
                meal_ideas=meal_ideas
            )
            
            category_meals[category] = validated_meals
        return category_meals

# Example usage (for testing):
if __name__ == "__main__":
    engine = MealPreGenEngine()
    try:
        categories = ["fast and easy", "high protein and prep time under 30 minutes"]
        meals_per_category = 5
        meal_suggestions = engine.get_meal_suggestions_by_categories(
            categories=categories,
            meals_per_category=meals_per_category
        )
        
        print("\n=== MEAL SUGGESTIONS ===\n")
        for category, meals in meal_suggestions.items():
            print(f"--- {category.upper()} ---")
            print(meals)
            print("\n")
            
        all_meals_text = ""
        for meals in meal_suggestions.values():
            all_meals_text += meals + "\n"
            
        updater = MealDBUpdater()
        updater.update_meals_in_db(all_meals_text, new=True)
        
    except Exception as e:
        print("Error:", e)
