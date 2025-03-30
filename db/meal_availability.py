import json
from typing import List, Dict, Any
from db.db_functions import Database, Inventory, SavedMeals, NewMealIdeas, SavedMealsInStockIds, NewMealIdeasInStockIds
from db.in_stock_checker import InStockChecker
from db.ingredient_matcher import IngredientMatcher

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
        self.ingredient_matcher = IngredientMatcher()
    
    def get_inventory_items(self) -> List[tuple]:
        """Get all inventory items from database"""
        return self.inventory.read()
    
    def check_saved_meal(self, meal_id: int, add_to_shopping_list: bool = False) -> Dict[str, Any]:
        """
        Check if a saved meal can be made with current inventory
        
        Args:
            meal_id: ID of the saved meal to check
            add_to_shopping_list: If True, adds missing ingredients to shopping list
            
        Returns:
            Dict with 'available' boolean and 'missing' list of ingredients
        """
        # Get meal details
        meal_data = self.saved_meals.read(meal_id)
        if not meal_data:
            return {'available': False, 'missing': [], 'error': 'Meal not found'}
        
        # Get inventory
        inventory = self.get_inventory_items()
        
        # Extract ingredients from meal data
        meal = meal_data[0]
        ingredients = json.loads(meal[3]) if isinstance(meal[3], str) else meal[3]
        
        # Check ingredients against inventory
        missing_ingredients = self.checker.check_ingredients(
            ingredients, 
            inventory, 
            add_to_shopping_list=add_to_shopping_list,
            db=self.db if add_to_shopping_list else None
        )
        
        return {
            'available': len(missing_ingredients) == 0,
            'missing': missing_ingredients
        }
    
    def check_new_meal_idea(self, meal_id: int, add_to_shopping_list: bool = False) -> Dict[str, Any]:
        """
        Check if a new meal idea can be made with current inventory
        
        Args:
            meal_id: ID of the meal idea to check
            add_to_shopping_list: If True, adds missing ingredients to shopping list
            
        Returns:
            Dict with 'available' boolean and 'missing' list of ingredients
        """
        # Get meal details
        meal_data = self.new_meal_ideas.read(meal_id)
        if not meal_data:
            return {'available': False, 'missing': [], 'error': 'Meal idea not found'}
        
        # Get inventory
        inventory = self.get_inventory_items()
        
        # Extract ingredients from meal data
        meal = meal_data[0]
        ingredients = json.loads(meal[3]) if isinstance(meal[3], str) else meal[3]
        
        # Check ingredients against inventory
        missing_ingredients = self.checker.check_ingredients(
            ingredients, 
            inventory,
            add_to_shopping_list=add_to_shopping_list,
            db=self.db if add_to_shopping_list else None
        )
        
        return {
            'available': len(missing_ingredients) == 0,
            'missing': missing_ingredients
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
        
        for meal in all_meals:
            meal_id = meal[0]
            result = self.check_saved_meal(meal_id, add_to_shopping_list)
            
            if result['available']:
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
        
        for meal in all_meals:
            meal_id = meal[0]
            result = self.check_new_meal_idea(meal_id, add_to_shopping_list)
            
            if result['available']:
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
    db = Database()
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


if __name__ == "__main__":
    update_all_meal_availability() 