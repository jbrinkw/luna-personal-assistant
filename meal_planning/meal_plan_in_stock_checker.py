from typing import List
from app.db_functions import get_inventory
from langchain_openai import ChatOpenAI
import app.config as config

class MealPlanInStockChecker:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=config.OPENAI_API_KEY)

    def extract_ingredients(self, meal_description: str) -> List[str]:
        """Extract ingredients with quantities from a meal description using AI"""
        if not meal_description or meal_description.lower() == 'no notes':
            return []
            
        prompt = f"""You are an ingredient extraction assistant.
        Given a meal description, extract and list all required ingredients with their quantities.
        Return ONLY the ingredients with quantities, one per line, in lowercase.
        Format: ingredient: quantity
        Keep original measurements.

        Meal Description:
        {meal_description}

        Ingredients:"""

        response = self.llm.invoke([{"role": "user", "content": prompt}])
        ingredients = [ing.strip().lower() for ing in response.content.strip().split('\n') if ing.strip()]
        return ingredients

    def parse_inventory(self, inventory_str: str) -> dict:
        """Convert inventory string to dictionary of {item: quantity}"""
        inventory = {}
        if inventory_str == "Inventory is empty.":
            return inventory
            
        for line in inventory_str.split('\n'):
            name, rest = line.split(':', 1)
            quantity = int(rest.split('(')[0].strip())
            inventory[name.lower().strip()] = quantity
        return inventory

    def check_ingredient_availability(self, ingredient: str, inventory: dict) -> bool:
        """Use AI to check if an ingredient is available, accounting for similar names"""
        if not inventory:
            return False
            
        inventory_list = "\n".join([f"- {item} (Quantity: {qty})" for item, qty in inventory.items()])
        
        prompt = f"""You are an ingredient matching assistant.
Check if this ingredient can be found in the inventory, accounting for similar names and variations.
IMPORTANT RULES:
1. DO NOT consider processed/derivative forms as matches:
   - If inventory has "cheese" and recipe needs "shredded cheese" = NOT_AVAILABLE
   - If inventory has "pork butt" and recipe needs "pulled pork" = NOT_AVAILABLE
2. Only match exact ingredients or truly equivalent names (like "tomato"/"tomatoes")
Answer ONLY "AVAILABLE" or "NOT_AVAILABLE".

Required Ingredient: {ingredient}

Available Inventory:
{inventory_list}

Answer:"""

        response = self.llm.invoke([{"role": "user", "content": prompt}])
        return response.content.strip() == "AVAILABLE"

    def get_missing_ingredients(self, meal_description: str) -> List[str]:
        """
        Returns a list of ingredients that are missing from the current inventory
        """
        inventory_str = get_inventory()
        inventory = self.parse_inventory(inventory_str)
        ingredients = self.extract_ingredients(meal_description)
        
        if not ingredients:
            return []
            
        missing_ingredients = []
        
        for ingredient in ingredients:
            if not self.check_ingredient_availability(ingredient, inventory):
                missing_ingredients.append(ingredient)
                
        return missing_ingredients

if __name__ == "__main__":
    checker = MealPlanInStockChecker()
    meal_description = """2. Shrimp and Bacon Carbonara
    • Estimated Calories: ~650 kcal
    • Macros (approximate): Protein 35g, Carbs 55g, Fat 28g
    • Ingredients:
     Pre-cooked shrimp: 4 oz
     Bacon: 2 slices
     Egg: 1 large
     Spaghetti (raw weight): 100 g
     Parmesan cheese: 2 tbsp (grated, about 10 g)
     Olive oil: 1 tbsp
     Garlic: 2 cloves (minced)"""
    
    missing = checker.extract_ingredients(meal_description)
    print(missing)
    # if missing:
    #     print("Missing ingredients:")
    #     for ingredient in missing:
    #         print(f"- {ingredient}")
    # else:
    #     print("All ingredients are available!")