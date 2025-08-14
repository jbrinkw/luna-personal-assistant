import json
from typing import List, Dict, Any
from db.db_functions import Database, Inventory, SavedMeals, NewMealIdeas, SavedMealsInStockIds, NewMealIdeasInStockIds
from db.in_stock_checker import InStockChecker

class MealAvailabilityUpdater:
    def __init__(self, db: Database):
        """Initialize with database connection"""
        self.db = db
        self.inventory = Inventory(db)
        self.saved_meals = SavedMeals(db)
        self.new_meal_ideas = NewMealIdeas(db)
        self.saved_meals_in_stock = SavedMealsInStockIds(db)
        self.new_meal_ideas_in_stock = NewMealIdeasInStockIds(db)
        self.checker = InStockChecker()
    
    def get_inventory_items(self) -> List[dict]:
        """Get all inventory items from database (as list of dicts)"""
        return self.inventory.read()
    
    def check_saved_meal(self, meal_id: int, add_to_shopping_list: bool = False) -> Dict[str, Any]:
        """
        Check if a saved meal can be made with current inventory
        
        Args:
            meal_id: ID of the saved meal to check
            add_to_shopping_list: If True, adds missing ingredients to shopping list
            
        Returns:
            Dict with 'available' boolean and 'missing' list of ingredients [[id, name, quantity_needed], ...]
        """
        # Get meal details
        meal_data = self.saved_meals.read(meal_id)
        if not meal_data:
            return {'available': False, 'missing': [], 'error': 'Meal not found'}
        
        # Get inventory
        inventory_items = self.get_inventory_items()
        
        # Extract ingredients from meal data (should be [[id, name, quantity], ...])
        meal = meal_data[0]
        ingredients_list = []
        try:
            # Access ingredients column by name and parse JSON
            ingredients_str = meal['ingredients'] 
            ingredients_list = json.loads(ingredients_str) if isinstance(ingredients_str, str) else ingredients_str
            # Ensure it's a list of lists
            if not isinstance(ingredients_list, list) or not all(isinstance(i, list) for i in ingredients_list):
                raise TypeError("Ingredients format is not a list of lists")
        except (json.JSONDecodeError, TypeError, KeyError) as e:
             print(f"[ERROR] Could not parse ingredients for saved meal ID {meal_id}: {e}")
             return {'available': False, 'missing': [], 'error': 'Invalid ingredients format'}
        
        # Check ingredients against inventory using the new method
        is_available, missing_ingredients_list = self.checker.check_ingredients_availability(
            ingredients=ingredients_list, # Pass the [[id, name, quantity], ...] list
            inventory_rows=inventory_items, 
            add_to_shopping_list=add_to_shopping_list,
            db=self.db if add_to_shopping_list else None
        )
        
        return {
            'available': is_available,
            'missing': missing_ingredients_list # This is now [[id, name, quantity_needed], ...]
        }
    
    def check_new_meal_idea(self, meal_id: int, add_to_shopping_list: bool = False) -> Dict[str, Any]:
        """
        Check if a new meal idea can be made with current inventory
        
        Args:
            meal_id: ID of the meal idea to check
            add_to_shopping_list: If True, adds missing ingredients to shopping list
            
        Returns:
            Dict with 'available' boolean and 'missing' list of ingredients [[id, name, quantity_needed], ...]
        """
        # Get meal details
        meal_data = self.new_meal_ideas.read(meal_id)
        if not meal_data:
            return {'available': False, 'missing': [], 'error': 'Meal idea not found'}
        
        # Get inventory
        inventory_items = self.get_inventory_items()
        
        # Extract ingredients from meal data (should be [[id, name, quantity], ...])
        meal = meal_data[0]
        ingredients_list = []
        try:
            ingredients_str = meal['ingredients']
            ingredients_list = json.loads(ingredients_str) if isinstance(ingredients_str, str) else ingredients_str
            if not isinstance(ingredients_list, list) or not all(isinstance(i, list) for i in ingredients_list):
                raise TypeError("Ingredients format is not a list of lists")
        except (json.JSONDecodeError, TypeError, KeyError) as e:
             print(f"[ERROR] Could not parse ingredients for new meal idea ID {meal_id}: {e}")
             return {'available': False, 'missing': [], 'error': 'Invalid ingredients format'}

        # Check ingredients against inventory using the new method
        is_available, missing_ingredients_list = self.checker.check_ingredients_availability(
            ingredients=ingredients_list, # Pass the [[id, name, quantity], ...] list
            inventory_rows=inventory_items,
            add_to_shopping_list=add_to_shopping_list,
            db=self.db if add_to_shopping_list else None
        )
        
        return {
            'available': is_available,
            'missing': missing_ingredients_list # This is now [[id, name, quantity_needed], ...]
        }
    
    def update_saved_meals_availability(self, add_to_shopping_list: bool = False) -> List[int]:
        """
        Update the saved_meals_instock_ids table and return list of available meal IDs
        
        Args:
            add_to_shopping_list: If True, adds missing ingredients to shopping list
        
        Returns:
            List of available meal IDs
        """
        # Get all saved meals
        all_meals = self.saved_meals.read()
        
        # Clear current in-stock table
        self.clear_saved_meals_in_stock()
        
        available_meal_ids = []
        
        # Need to handle potential Row object if all_meals is not empty
        if all_meals: 
            for meal_row in all_meals:
                meal_id = meal_row['id'] # Access ID by key
                result = self.check_saved_meal(meal_id, add_to_shopping_list)
            
                if result.get('available', False): # Use .get for safety
                    # Add to available list
                    available_meal_ids.append(meal_id)
                    # Add to database
                    self.saved_meals_in_stock.create(meal_id)
        
        return available_meal_ids
    
    def update_new_meal_ideas_availability(self, add_to_shopping_list: bool = False) -> List[int]:
        """
        Update the new_meal_ideas_instock_ids table and return list of available meal IDs
        
        Args:
            add_to_shopping_list: If True, adds missing ingredients to shopping list
            
        Returns:
            List of available meal IDs
        """
        # Get all new meal ideas
        all_meals = self.new_meal_ideas.read()
        
        # Clear current in-stock table
        self.clear_new_meal_ideas_in_stock()
        
        available_meal_ids = []
        
        if all_meals:
            for meal_row in all_meals:
                meal_id = meal_row['id'] # Access ID by key
                result = self.check_new_meal_idea(meal_id, add_to_shopping_list)
            
                if result.get('available', False): # Use .get for safety
                    # Add to available list
                    available_meal_ids.append(meal_id)
                    # Add to database
                    self.new_meal_ideas_in_stock.create(meal_id)
        
        return available_meal_ids
    
    def clear_saved_meals_in_stock(self):
        """Clear the saved_meals_instock_ids table"""
        self.db.execute_query("DELETE FROM saved_meals_instock_ids")
    
    def clear_new_meal_ideas_in_stock(self):
        """Clear the new_meal_ideas_instock_ids table"""
        self.db.execute_query("DELETE FROM new_meal_ideas_instock_ids")


def update_all_meal_availability(add_to_shopping_list: bool = False):
    """
    Utility function to update availability for all saved meals and meal ideas
    
    Args:
        add_to_shopping_list: If True, adds missing ingredients to shopping list
    """
    db = None # Initialize db to None
    try:
        db = Database()
        # Ensure connection is established before proceeding
        if not db.connect(): 
             print("[ERROR] Failed to connect to database in update_all_meal_availability.")
             return {'saved_meals': [], 'new_meal_ideas': []} # Return empty if connection fails
             
        updater = MealAvailabilityUpdater(db)
    
        # Update saved meals
        available_saved_meals = updater.update_saved_meals_availability(add_to_shopping_list)
        print(f"Updated saved meals availability. {len(available_saved_meals)} meals are available.")
    
        # Update new meal ideas
        available_meal_ideas = updater.update_new_meal_ideas_availability(add_to_shopping_list)
        print(f"Updated new meal ideas availability. {len(available_meal_ideas)} meal ideas are available.")
    
        return {
            'saved_meals': available_saved_meals,
            'new_meal_ideas': available_meal_ideas
        }
    except Exception as e:
         print(f"[ERROR] An error occurred in update_all_meal_availability: {e}")
         import traceback
         traceback.print_exc()
         # Return empty lists on error
         return {'saved_meals': [], 'new_meal_ideas': []}
    finally:
         # Ensure database connection is closed
         if db and db.conn:
             db.disconnect()


if __name__ == "__main__":
    update_all_meal_availability() 