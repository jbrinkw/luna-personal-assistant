from typing import List, Dict, Any, Optional, Tuple, Union
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

class IngredientMatcher:
    def __init__(self):
        """Initialize the ingredient matcher with OpenAI client"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def find_or_create_ingredient(self, ingredient_name: str, db) -> Tuple[int, bool]:
        """
        Find an existing ingredient in the ingredients_foods table or create a new one
        
        Args:
            ingredient_name: Name of the ingredient to find or create
            db: Database connection
            
        Returns:
            Tuple of (ingredient_id, was_created)
        """
        from db.db_functions import IngredientsFood
        
        # Get the ingredients_foods table
        ingredients_foods = IngredientsFood(db)
        
        # Get all ingredients from the database
        all_ingredients = ingredients_foods.read()
        
        # Check if we have ingredients to match against
        if all_ingredients:
            # Extract just the names for matching
            ingredient_names = [item[1] for item in all_ingredients]
            
            # Try to find a matching ingredient
            matching_id = self.find_matching_ingredient(ingredient_name, ingredient_names, all_ingredients)
            
            if matching_id:
                # Found a match
                return matching_id, False
        
        # No match found, create a new entry
        # Use default values for min_amount_to_buy and walmart_link
        new_id = ingredients_foods.create(ingredient_name, 1, None)
        return new_id, True
    
    def find_matching_ingredient(self, ingredient_name: str, ingredient_names: List[str], 
                                all_ingredients: List[tuple]) -> Optional[int]:
        """
        Use AI to find a matching ingredient from the ingredients_foods table
        
        Args:
            ingredient_name: Name of the ingredient to match
            ingredient_names: List of all ingredient names in ingredients_foods
            all_ingredients: Complete ingredient data from ingredients_foods
            
        Returns:
            ID of the matching ingredient or None if no match
        """
        if not ingredient_names:
            return None
            
        # Format ingredient names for AI prompt
        ingredients_list = "\n".join([f"- {item}" for item in ingredient_names])
        
        # Ask AI to determine if there's a matching ingredient
        prompt = f"""You are an ingredient matching assistant for a food planning app.
Find the closest match for this ingredient in the following list.
If there is no reasonable match, answer "NO_MATCH".
If there is a match, answer ONLY with the EXACT name of the matching ingredient from the list.
Consider variations in spelling, packaging, and common forms of the ingredient.

Required Ingredient: {ingredient_name}

Available Ingredients:
{ingredients_list}

Answer:"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        match = response.choices[0].message.content.strip()
        
        if match == "NO_MATCH":
            return None
            
        # Find the matching ingredient ID
        for ingredient in all_ingredients:
            if ingredient[1] == match:
                return ingredient[0]
                
        return None
    
    def parse_quantity(self, quantity_str: str) -> float:
        """
        Parse a quantity string into a float
        
        Args:
            quantity_str: String representation of quantity (e.g., "1/2 lb", "2 tsp")
            
        Returns:
            Float representation of the quantity
        """
        try:
            # Extract the first part (numerical part) of the quantity
            amount_str = quantity_str.split()[0]
            
            # Handle fractions
            if '/' in amount_str:
                num, denom = amount_str.split('/')
                return float(num) / float(denom)
            else:
                return float(amount_str)
        except (ValueError, IndexError):
            # Default to 1 if parsing fails
            return 1.0
    
    def add_to_shopping_list(self, ingredient: Dict[str, str], db) -> bool:
        """
        Add an ingredient to the shopping list after checking if it exists
        
        Args:
            ingredient: Dictionary with 'name' and 'quantity' keys
            db: Database connection
            
        Returns:
            Boolean indicating success
        """
        try:
            from db.db_functions import ShoppingList
            
            # Find or create the ingredient
            ingredient_id, was_created = self.find_or_create_ingredient(ingredient['name'], db)
            
            if ingredient_id:
                # Parse the quantity
                amount = self.parse_quantity(ingredient['quantity'])
                
                # Add to shopping list
                shopping_list = ShoppingList(db)
                shopping_list.create(ingredient_id, amount)
                
                action = "Created new ingredient and added" if was_created else "Added existing ingredient"
                print(f"{action} to shopping list: {ingredient['name']} (ID: {ingredient_id})")
                return True
            else:
                print(f"Failed to add {ingredient['name']} to shopping list: Could not get ingredient ID")
                return False
                
        except Exception as e:
            print(f"Error adding to shopping list: {e}")
            return False 