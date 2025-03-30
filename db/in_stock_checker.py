from typing import List, Dict, Any
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from db.ingredient_matcher import IngredientMatcher

# Load environment variables
load_dotenv()

class InStockChecker:
    def __init__(self):
        """Initialize the ingredient checker with OpenAI client"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.ingredient_matcher = IngredientMatcher()
    
    def check_ingredients(self, ingredients: List[Dict[str, str]], inventory: List[Dict[str, Any]], 
                         add_to_shopping_list: bool = False, db=None) -> List[Dict[str, str]]:
        """
        Check if ingredients are in stock based on inventory
        Args:
            ingredients: List of ingredient dictionaries with 'name' and 'quantity' keys
            inventory: List of inventory items from the database
            add_to_shopping_list: If True, adds missing ingredients to shopping list
            db: Database connection (required if add_to_shopping_list is True)
        
        Returns:
            List of missing ingredients (empty list if all available)
        """
        # Process inventory into a more usable format
        inventory_dict = {}
        for item in inventory:
            inventory_dict[item[1].lower()] = {
                'id': item[0],
                'quantity': item[2],
                'expiration': item[3] if len(item) > 3 else None
            }
        
        missing_ingredients = []
        
        for ingredient in ingredients:
            if not self._is_ingredient_available(ingredient['name'], inventory_dict):
                missing_ingredients.append(ingredient)
                
                # Add to shopping list if specified
                if add_to_shopping_list and db:
                    self.ingredient_matcher.add_to_shopping_list(ingredient, db)
        
        return missing_ingredients
    
    def _is_ingredient_available(self, ingredient_name: str, inventory: Dict[str, Any]) -> bool:
        """
        Use AI to check if an ingredient is available in inventory, accounting for similar names
        Args:
            ingredient_name: Name of the ingredient to check
            inventory: Dictionary of inventory items
        
        Returns:
            Boolean indicating if ingredient is available
        """
        if not inventory:
            return False
        
        # Simple exact match check first
        if ingredient_name.lower() in inventory:
            return True
        
        # Format inventory for AI prompt
        inventory_list = "\n".join([f"- {item}" for item in inventory.keys()])
        
        # Ask AI to determine if the ingredient is available
        prompt = f"""You are an ingredient matching assistant.
Check if this ingredient can be found in the inventory, accounting for similar names and variations.
Consider common substitutions and different forms of the same ingredient.
Answer ONLY "AVAILABLE" or "NOT_AVAILABLE".

Required Ingredient: {ingredient_name}

Available Inventory:
{inventory_list}

Answer:"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        return response.choices[0].message.content.strip() == "AVAILABLE"
    
    # Legacy method, replaced by ingredient_matcher.add_to_shopping_list
    def _add_to_shopping_list(self, ingredient: Dict[str, str], db) -> None:
        """
        Legacy method - use ingredient_matcher.add_to_shopping_list instead
        """
        self.ingredient_matcher.add_to_shopping_list(ingredient, db)
    
    # Legacy method, replaced by ingredient_matcher.find_matching_ingredient
    def _find_matching_ingredient(self, ingredient_name: str, ingredient_names: List[str], all_ingredients: List[tuple]) -> int:
        """
        Legacy method - use ingredient_matcher.find_matching_ingredient instead
        """
        return self.ingredient_matcher.find_matching_ingredient(ingredient_name, ingredient_names, all_ingredients) 