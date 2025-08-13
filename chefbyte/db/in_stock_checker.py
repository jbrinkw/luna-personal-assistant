from typing import List, Dict, Any, Tuple, Optional
import json
import os
import re # Import re for quantity parsing
from dotenv import load_dotenv
from openai import OpenAI
# Remove IngredientMatcher import
# from db.ingredient_matcher import IngredientMatcher
# Import ShoppingList table class
from db.db_functions import ShoppingList 
import sys

# Load environment variables
load_dotenv()

# Add project root to sys.path if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class InStockChecker:
    def __init__(self):
        """Initialize the ingredient checker."""
        # Remove OpenAI client and IngredientMatcher init
        # self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # self.ingredient_matcher = IngredientMatcher()
        pass # No initialization needed for now
    
    def _parse_quantity(self, quantity_str: str) -> Tuple[Optional[float], Optional[str]]:
        """Parse quantity string like '2 pounds' -> (2.0, 'pounds'). Handles fractions."""
        if not isinstance(quantity_str, str):
             return None, None
             
        quantity_str = quantity_str.strip()
        # Find numeric part (including fractions like 1/2)
        numeric_match = re.match(r'^([\d\./]+)', quantity_str)
        number = None
        unit = None
        
        if numeric_match:
            amount_str = numeric_match.group(1)
            try:
                if '/' in amount_str:
                    num, denom = amount_str.split('/')
                    number = float(num) / float(denom)
                else:
                    number = float(amount_str)
            except ValueError:
                 number = None # Parsing failed
                 
            # Extract unit part
            unit_part = quantity_str[len(amount_str):].strip()
            # Basic unit extraction, might need refinement
            unit_match = re.match(r'^([a-zA-Z]+)', unit_part)
            if unit_match:
                 unit = unit_match.group(1).lower()
                 # Handle plurals simply
                 if unit.endswith('s'):
                      unit = unit[:-1]
            elif unit_part: # Handle cases like '2 large' -> unit 'large'
                 unit = unit_part.lower()
                 
        # If no numeric part found, maybe it's just a count like 'a dozen'? Treat as 1 for now.
        # Or maybe just a name? For quantity check, we need a number.
        if number is None:
             # Try to handle 'a', 'an'
             if quantity_str.lower().startswith('a ') or quantity_str.lower().startswith('an '):
                 number = 1.0
                 unit_part = quantity_str[quantity_str.find(' ')+1:].strip()
                 # Extract unit if possible
                 unit_match = re.match(r'^([a-zA-Z]+)', unit_part)
                 if unit_match:
                      unit = unit_match.group(1).lower()
                      if unit.endswith('s'):
                           unit = unit[:-1]
                 elif unit_part:
                      unit = unit_part.lower()
             else:
                  # Cannot parse a number, assume 1 unit? Or None?
                  # Let's return None for number if unparseable, requiring downstream handling.
                  number = None 
                  unit = quantity_str # Keep original string as unit if no number
                  
        # Fallback unit if needed
        if number is not None and unit is None:
            unit = 'unit' # Default unit if number exists but no unit found
            
        return number, unit

    # This method is DEPRECATED and will be removed, use check_ingredients_availability
    def check_ingredients(self, ingredients: List[List[Any]], inventory: List[Dict[str, Any]], 
                         add_to_shopping_list: bool = False, db=None) -> List[Dict[str, str]]:
        """
        DEPRECATED - Use check_ingredients_availability.
        Checks if ingredients are in stock based on inventory using name matching.
        Args:
            ingredients: List of ingredient lists [food_id, name, quantity]
            inventory: List of inventory items (row dicts) from the database
            add_to_shopping_list: If True, adds missing ingredients to shopping list
            db: Database connection (required if add_to_shopping_list is True)
        
        Returns:
            List of missing ingredients (formatted as {'name': ..., 'quantity': ...})
        """
        print("[WARN] Calling deprecated check_ingredients method in InStockChecker.")
        # Basic implementation to maintain structure but not recommended
        missing_ingredients = []
        inventory_names = {item['name'].lower() for item in inventory} if inventory else set()
        for food_id, name, quantity in ingredients:
            if name.lower() not in inventory_names:
                missing_ingredients.append({'name': name, 'quantity': quantity})
        return missing_ingredients
    
    # Removed LLM-based _is_ingredient_available method
    # Removed legacy _add_to_shopping_list method
    # Removed legacy _find_matching_ingredient method

    def check_ingredients_availability(self, ingredients: List[List[Any]], inventory_rows: List[Any], 
                                      add_to_shopping_list: bool = False, db=None) -> Tuple[bool, List[List[Any]]]:
        """
        Check if ingredients are in stock based on inventory using food_id matching.
        Args:
            ingredients: List of required ingredient lists [food_id, name, quantity].
            inventory_rows: List of inventory items (row dicts) from the database.
            add_to_shopping_list: If True, adds missing ingredients to the shopping list.
            db: Database connection (required if add_to_shopping_list is True).
        
        Returns:
            Tuple containing:
                - bool: True if all ingredients are available in sufficient quantity, False otherwise.
                - List: List of missing ingredients in the format [food_id, name, quantity_needed].
        """
        # Process inventory: Create a dictionary mapping food_id to a list of inventory items
        # Also sum total quantity for each food_id, attempting basic unit consistency.
        inventory_by_food_id: Dict[int, List[Dict[str, Any]]] = {}
        inventory_totals: Dict[int, Dict[str, float]] = {} # Stores {food_id: {unit: total_quantity}}

        try:
            for item in inventory_rows:
                food_id = item['ingredient_food_id']
                if food_id is None:
                    # print(f"[WARN] Inventory item '{item['name']}' (ID: {item['id']}) has no food_id, skipping for availability check.")
                    continue
                    
                # Store the full item details
                if food_id not in inventory_by_food_id:
                    inventory_by_food_id[food_id] = []
                inventory_by_food_id[food_id].append(dict(item)) # Convert Row to dict
                
                # Attempt to parse and sum quantity
                inv_qty_num, inv_unit = self._parse_quantity(item['quantity'])
                if inv_qty_num is not None and inv_unit is not None:
                     if food_id not in inventory_totals:
                          inventory_totals[food_id] = {}
                     if inv_unit not in inventory_totals[food_id]:
                          inventory_totals[food_id][inv_unit] = 0.0
                     inventory_totals[food_id][inv_unit] += inv_qty_num
                # else:
                     # print(f"[WARN] Could not parse quantity for inventory item '{item['name']}': '{item['quantity']}'")

        except Exception as e:
             print(f"[ERROR] Failed to process inventory: {e}. Inventory item format might be unexpected.")
             print(f"Sample inventory item: {inventory_rows[0] if inventory_rows else 'Empty'}")
             # Return False and an empty list or an error indicator
             return (False, [[None, 'Error processing inventory', '']]) 

        missing_ingredients = []
        # Assume available unless a required food_id is completely missing
        all_available = True 

        print("\n--- Checking Ingredient Availability ---")
        for ingredient_data in ingredients:
            if not isinstance(ingredient_data, list) or len(ingredient_data) != 3:
                 print(f"[WARN] Skipping invalid required ingredient format: {ingredient_data}")
                 continue
                 
            req_food_id, req_name, req_quantity_str = ingredient_data
            print(f"Checking for: {req_name} (FoodID: {req_food_id}, Needed: {req_quantity_str})")

            if req_food_id is None:
                print(f"  [WARN] Required ingredient '{req_name}' has no FoodID. Cannot check availability by ID.")
                # Cannot confirm, add to missing list for info, but don't block availability yet
                missing_ingredients.append([req_food_id, req_name, req_quantity_str + " (Missing FoodID)"])
                # all_available = False # Don't set to false just for missing ID if we relax check
                continue

            # --- MODIFIED CHECK: Focus on presence of FoodID first --- 
            if req_food_id not in inventory_totals:
                print(f"  [Missing] Ingredient Type (FoodID: {req_food_id}) not found in inventory.")
                missing_ingredients.append([req_food_id, req_name, req_quantity_str])
                all_available = False # If the core ingredient type is missing, the meal IS unavailable
            else:
                # Ingredient type exists, attempt quantity check for logging/shopping list, but don't fail the meal based on it
                req_qty_num, req_unit = self._parse_quantity(req_quantity_str)

                if req_qty_num is None:
                    print(f"  [WARN] Could not parse required quantity '{req_quantity_str}' for '{req_name}'. Skipping detailed check.")
                    # Add to missing list for info, but don't block availability
                    missing_ingredients.append([req_food_id, req_name, req_quantity_str + " (Unparsed Quantity)"])
                    continue # Skip further quantity checks for this ingredient

                # Check available quantity for the required unit (or compatible units)
                available_units = inventory_totals[req_food_id]

                # Simple check: Does the inventory have this exact unit?
                if req_unit in available_units:
                    available_amount = available_units[req_unit]
                    if available_amount < req_qty_num:
                        print(f"  [Low Stock] Have {available_amount:.2f} {req_unit}, need {req_qty_num:.2f} {req_unit}.")
                        missing_qty_str = f"{req_qty_num - available_amount:.2f} {req_unit} needed"
                        missing_ingredients.append([req_food_id, req_name, missing_qty_str])
                        # all_available = False # Don't set to false for low stock with relaxed check
                    else:
                        print(f"  [OK] Sufficient quantity ({available_amount:.2f} {req_unit}) confirmed.")
                else:
                    # Unit mismatch - requires conversion logic or assuming unavailable
                    # TODO: Implement unit conversion (e.g., lbs to oz, cups to ml)
                    print(f"  [Unit Mismatch] Need unit '{req_unit}', have units: {list(available_units.keys())}. Cannot confirm quantity.")
                    missing_ingredients.append([req_food_id, req_name, req_quantity_str + f" (Unit '{req_unit}' needed, have {list(available_units.keys())})"])
                    # all_available = False # Don't set to false for unit mismatch with relaxed check

        print("--- Availability Check Finished ---")

        # Add missing ingredients to the shopping list if the flag is set
        if missing_ingredients and add_to_shopping_list and db:
            print("\n  Adding missing/low stock/mismatch ingredients to shopping list...")
            try:
                 # Get ShoppingList table object
                 shopping_list_table = ShoppingList(db)
                 
                 for missing_info in missing_ingredients:
                     food_id, name, qty_needed_str = missing_info
                     
                     if food_id is not None:
                         # Attempt to parse the needed quantity for shopping list amount
                         qty_num, qty_unit = self._parse_quantity(qty_needed_str)
                         # Use a default amount (e.g., 1) if parsing fails or complex unit
                         amount_to_add = qty_num if qty_num is not None and qty_num > 0 else 1.0 
                         
                         # Add/Update the shopping list
                         shopping_list_table.create(food_id, amount_to_add)
                         print(f"    - Added/Updated {name} (FoodID: {food_id}) to shopping list, amount: {amount_to_add}")
                     else:
                         print(f"    - Cannot add {name} to shopping list, missing FoodID.")
            except Exception as e:
                 print(f"[ERROR] Failed to add items to shopping list: {e}")
            
        return all_available, missing_ingredients