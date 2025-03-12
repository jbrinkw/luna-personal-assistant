from typing import List, Tuple
from db_functions import get_saved_meals, get_meal_ideas, get_inventory, run_query, create_table, clear_table
from langchain_openai import ChatOpenAI
import config

class InStockChecker:
    def __init__(self, new: bool = False):
        self.new = new
        self.table_name = "meal_ideas_in_stock" if new else "saved_meals_in_stock"
        self.llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo", openai_api_key=config.OPENAI_API_KEY)

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

    def parse_ingredients(self, ingredients_str: str) -> List[str]:
        """Convert comma-separated ingredients string to list"""
        if ingredients_str == "N/A":
            return []
        return [ing.lower().strip() for ing in ingredients_str.split(',')]

    def check_ingredient_availability(self, ingredient: str, inventory: dict) -> bool:
        """Use AI to check if an ingredient is available, accounting for similar names"""
        if not inventory:
            return False
            
        inventory_list = "\n".join([f"- {item} (Quantity: {qty})" for item, qty in inventory.items()])
        
        prompt = f"""You are an ingredient matching assistant.
Check if this ingredient can be found in the inventory, accounting for similar names and variations.
Consider common substitutions and different forms of the same ingredient.
Answer ONLY "AVAILABLE" or "NOT_AVAILABLE".

Required Ingredient: {ingredient}

Available Inventory:
{inventory_list}

Answer:"""

        response = self.llm.invoke([{"role": "user", "content": prompt}])
        return response.content.strip() == "AVAILABLE"

    def update_available_meals(self) -> List[int]:
        """
        Check which meals can be made with current inventory and update the corresponding table.
        Returns list of available meal IDs.
        """
        inventory_str = get_inventory()
        # Get meals from appropriate source based on self.new
        meals = get_meal_ideas() if self.new else get_saved_meals()
        inventory = self.parse_inventory(inventory_str)
        
        available_meal_ids = []
        
        for meal_id, name, prep_time, ingredients_str, recipe in meals:
            ingredients = self.parse_ingredients(ingredients_str)
            all_ingredients_available = True
            
            for ingredient in ingredients:
                if not self.check_ingredient_availability(ingredient, inventory):
                    all_ingredients_available = False
                    print(f"Missing ingredient '{ingredient}' for meal '{name}'")
                    break
                    
            if all_ingredients_available:
                available_meal_ids.append(meal_id)
                print(f"Meal available: '{name}'")
        
        # Update the database table
        create_table(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY
            )
        """)
        
        clear_table(self.table_name)
        
        for meal_id in available_meal_ids:
            query = f"INSERT INTO {self.table_name} (id) VALUES (%s)"
            run_query(query, (meal_id,), commit=True)
        
        print(f"Updated {self.table_name} with {len(available_meal_ids)} available meal IDs.")
        return available_meal_ids

if __name__ == "__main__":
    # Check saved meals
    checker = InStockChecker(new=False)
    available_meals = checker.update_available_meals()
    if available_meals:
        print("\nSaved meals that can be made with current inventory:")
        print(f"Meal IDs: {available_meals}")
    else:
        print("\nNo saved meals can be made with the current inventory.")
    
    # Check meal ideas
    checker = InStockChecker(new=True)
    available_ideas = checker.update_available_meals()
    if available_ideas:
        print("\nMeal ideas that can be made with current inventory:")
        print(f"Meal IDs: {available_ideas}")
    else:
        print("\nNo meal ideas can be made with the current inventory.")