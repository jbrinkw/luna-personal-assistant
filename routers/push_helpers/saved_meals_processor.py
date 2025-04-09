"""
This module handles saved meals CRUD operations from natural language inputs.
"""

import os
import json
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from db.db_functions import Database, SavedMeals, IngredientsFood
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define models for extraction
class MealIngredient(BaseModel):
    name: str = Field(..., description="Ingredient name")
    amount: str = Field(..., description="Amount with units")

class SavedMealItem(BaseModel):
    operation: str = Field(..., description="CRUD operation: create, delete, update")
    meal_id: Optional[int] = Field(None, description="ID of the meal to update or delete")
    name: Optional[str] = Field(None, description="Name of the meal")
    prep_time_minutes: Optional[int] = Field(None, description="Preparation time in minutes")
    ingredients: Optional[List[MealIngredient]] = Field(None, description="List of ingredients")
    recipe: Optional[str] = Field(None, description="Recipe instructions")

class SavedMealItems(BaseModel):
    items: List[SavedMealItem] = Field(..., description="List of saved meal items to be processed")

class SavedMealsProcessor:
    def __init__(self, saved_meals_table: SavedMeals, db: Database):
        """Initialize processor with shared SavedMeals table object and DB connection."""
        self.saved_meals_table = saved_meals_table # Store passed object
        self.db = db # Store passed DB connection (needed for find_meal_by_name)
        # Add ingredients_foods table for lookups
        self.ingredients_foods_table = IngredientsFood(self.db)
        self._food_id_lookup = self._build_food_id_lookup() # Build lookup on init
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = "gpt-4o-mini" 
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, api_key=self.api_key)
        self.output_parser = PydanticOutputParser(pydantic_object=SavedMealItems)
        self.format_instructions = self.output_parser.get_format_instructions()
        self.extraction_prompt_template = """\
Parse the following user input about saved meals changes.
For each meal mentioned, extract the following fields:
- operation: either 'create', 'delete', or 'update'
- meal_id: for update or delete operations, the ID of the meal to modify
- name: the name of the meal
- prep_time_minutes: the preparation time in minutes
- ingredients: a list of ingredients with name and amount
- recipe: the recipe instructions

IMPORTANT: All ingredient entries MUST have both a name and an amount. If the amount is not specified, use a reasonable default like "to taste", "as needed", or "1 unit".

Your main responsibility is to interpret natural language about saved meals and determine the appropriate operations:

1. When the user wants to create a new meal:
   - Use "create" operation
   - Extract all relevant meal details provided

2. When the user wants to update an existing meal:
   - Use "update" operation 
   - Include meal_id if specified or if you can identify the meal
   - Only extract the fields that are being updated

3. When the user wants to delete a meal:
   - Use "delete" operation
   - Include meal_id or use the name to identify the meal

4. When handling multiple operations in a single request:
   - Split them into separate items with appropriate operations
   - Ensure each item has all necessary fields

Current Saved Meals:
{current_saved_meals}

Return the results as a JSON object following this schema:
{format_instructions}

Remember that ALL ingredient entries MUST have both a name and an amount field specified as strings.

User Input: {user_input}
"""

    def _build_food_id_lookup(self) -> Dict[str, int]:
        """Builds a dictionary mapping lowercase ingredient names to food IDs."""
        lookup = {}
        try:
            all_foods = self.ingredients_foods_table.read()
            if all_foods:
                for food in all_foods:
                    # Use dictionary access for Row objects
                    lookup[food['name'].lower()] = food['id']
        except Exception as e:
             print(f"[ERROR] Failed to build food ID lookup in SavedMealsProcessor: {e}")
        return lookup

    def _get_food_id_by_name(self, name: str) -> Optional[int]:
        """Helper to find the food ID based on name using the pre-built lookup."""
        # Simple case-insensitive lookup
        return self._food_id_lookup.get(name.lower())

    def get_current_saved_meals_text(self):
        """Get the current saved meals using the shared table object."""
        # Use self.saved_meals_table directly
        saved_meals = self.saved_meals_table
        try:
            current_meals = saved_meals.read()
            if not current_meals:
                return "There are no saved meals currently."
            
            meals_text = ""
            for meal in current_meals:
                # Access data using dictionary keys
                meal_id = meal['id']
                name = meal['name']
                prep_time = meal['prep_time_minutes']
                ingredients_col = meal['ingredients']
                recipe_col = meal['recipe']
                
                # Parse ingredients JSON (new format: [[id, name, quantity], ...])
                ingredients_text = "[Invalid Ingredients Data]" # Default
                try:
                    ingredients_json = json.loads(ingredients_col) if isinstance(ingredients_col, str) else ingredients_col 
                    if isinstance(ingredients_json, list): 
                        # Format based on new list structure
                        ingredients_text = ", ".join([f"{ing_data[1]} ({ing_data[2]})" 
                                                    for ing_data in ingredients_json if isinstance(ing_data, list) and len(ing_data) >= 3])
                    else:
                         ingredients_text = str(ingredients_json)
                except (json.JSONDecodeError, TypeError, IndexError) as e:
                    print(f"[WARN] Error parsing ingredients JSON for saved meal ID {meal_id}: {e}")
                
                # Truncate recipe text
                recipe = recipe_col[:100] + "..." if len(recipe_col) > 100 else recipe_col
                
                meals_text += f"ID: {meal_id}, Name: {name}, Prep Time: {prep_time} mins\n"
                meals_text += f"  Ingredients: {ingredients_text}\n"
                # meals_text += f"Recipe: {recipe}\n\n" # Maybe omit recipe for brevity
            
            return meals_text.strip()
        except Exception as e:
            print(f"Error getting saved meals text in processor: {e}")
            return "Error retrieving saved meals."
        # No disconnect

    def extract_meals(self, user_input: str, current_saved_meals: str) -> SavedMealItems:
        prompt = ChatPromptTemplate.from_template(template=self.extraction_prompt_template)
        messages = prompt.format_messages(
            user_input=user_input,
            format_instructions=self.format_instructions,
            current_saved_meals=current_saved_meals
        )
        response = self.chat.invoke(messages)
        print(f"[DEBUG] Extractor LLM raw output (truncated): '{response.content[:300]}...'")
        
        # Implement a fallback mechanism in case parsing fails
        try:
            extracted_meals = self.output_parser.parse(response.content)
            return extracted_meals
        except Exception as e:
            print(f"[ERROR] Failed to parse extractor output: {e}")
            # Create a minimal valid output to allow the process to continue
            return SavedMealItems(items=[])

    def find_meal_by_name(self, name: str) -> Optional[int]:
        """Find a meal ID by name using the shared table object."""
        if not name:
            return None
        
        # Use self.saved_meals_table
        saved_meals = self.saved_meals_table
        try:
            all_meals = saved_meals.read()
            if not all_meals:
                return None
                
            # First try exact match
            for meal in all_meals:
                if meal['name'].lower() == name.lower():
                    return meal['id']
                    
            # Then try partial match
            for meal in all_meals:
                if name.lower() in meal['name'].lower():
                    return meal['id']
                    
            return None
        except Exception as e:
             print(f"[ERROR] Failed to find meal by name '{name}': {e}")
             return None

    def process_saved_meals_changes(self, user_input: str) -> Tuple[bool, str]:
        """
        Process saved meals changes using the shared table object.
        Handles the new ingredient format [[food_id, name, quantity], ...]
        """
        # Use self.saved_meals_table directly
        saved_meals = self.saved_meals_table
        
        changes_made = False
        confirmation_messages = []
        meals_processed = 0
        
        try:
            # Get current saved meals for context
            current_saved_meals_text = self.get_current_saved_meals_text()
            
            # Extract meals from natural language input
            meal_items = self.extract_meals(user_input, current_saved_meals_text)
            
            # Special case for "delete all"
            if (not meal_items.items and 
                ("delete all" in user_input.lower() or "remove all" in user_input.lower())):
                all_meals = saved_meals.read()
                if all_meals:
                    initial_count = len(all_meals)
                    for meal in all_meals:
                        meal_id = meal['id']
                        saved_meals.delete(meal_id)
                        meals_processed += 1
                    if initial_count > 0:
                         confirmation_messages.append(f"Deleted all {initial_count} saved meals.")
                         changes_made = True
                    else:
                         confirmation_messages.append("No saved meals found to delete.")
            
            # Process each meal item
            for item in meal_items.items:
                if item.operation.lower() == "create":
                    if not item.name or not item.prep_time_minutes or not item.ingredients or not item.recipe:
                        print(f"[WARN] Skipping create operation due to missing fields: {item}")
                        continue
                    
                    # Convert ingredients from LLM format [{name, amount}, ...] to DB format [[id, name, amount], ...]
                    ingredients_for_db = []
                    for ing in item.ingredients:
                        food_id = self._get_food_id_by_name(ing.name)
                        # If food_id is None, we might skip, log, or add without ID
                        if food_id is None:
                             print(f"[WARN] Could not find food ID for ingredient '{ing.name}'. Skipping in meal '{item.name}'.")
                             # Alternatively, could add with food_id=None: ingredients_for_db.append([None, ing.name, ing.amount])
                             continue # Skip this ingredient if ID not found
                        ingredients_for_db.append([food_id, ing.name, ing.amount])
                    
                    # Use shared table object
                    meal_id = saved_meals.create(
                        item.name,
                        item.prep_time_minutes,
                        ingredients_for_db, # Save in the new format
                        item.recipe
                    )
                    
                    if meal_id:
                        change_msg = f"Created meal: {item.name} (ID: {meal_id}) | Prep: {item.prep_time_minutes}m"
                        confirmation_messages.append(change_msg)
                        changes_made = True
                        meals_processed += 1
                
                elif item.operation.lower() == "delete":
                    target_meal_id = item.meal_id
                    meal_name_for_msg = "Unknown"
                    item_found_and_deleted = False

                    if target_meal_id is None and item.name:
                        target_meal_id = self.find_meal_by_name(item.name)

                    if target_meal_id is not None:
                        current = saved_meals.read(target_meal_id)
                        if current and current[0]:
                            meal_name_for_msg = current[0]['name']
                            saved_meals.delete(target_meal_id)
                            change_msg = f"Deleted meal: {meal_name_for_msg} (ID: {target_meal_id})"
                            confirmation_messages.append(change_msg)
                            changes_made = True
                            meals_processed += 1
                            item_found_and_deleted = True
                            
                    if not item_found_and_deleted:
                        print(f"[WARN] Could not find meal to delete: {item.name or item.meal_id}")
                
                elif item.operation.lower() == "update":
                    target_meal_id = item.meal_id
                    if target_meal_id is None and item.name:
                        target_meal_id = self.find_meal_by_name(item.name)
                    
                    if target_meal_id is None:
                        print(f"[WARN] Could not find meal to update: {item.name or 'ID not provided'}")
                        continue

                    update_fields = {}
                    if item.name is not None: update_fields['name'] = item.name
                    if item.prep_time_minutes is not None: update_fields['prep_time_minutes'] = item.prep_time_minutes
                    if item.recipe is not None: update_fields['recipe'] = item.recipe
                    
                    # Handle ingredient update separately - convert to new format
                    if item.ingredients is not None:
                        ingredients_for_db = []
                        for ing in item.ingredients:
                            food_id = self._get_food_id_by_name(ing.name)
                            if food_id is None:
                                print(f"[WARN] Could not find food ID for ingredient '{ing.name}' during update for meal ID {target_meal_id}. Skipping ingredient.")
                                continue
                            ingredients_for_db.append([food_id, ing.name, ing.amount])
                        # Convert the list to JSON string before saving
                        update_fields['ingredients'] = json.dumps(ingredients_for_db) 

                    if not update_fields:
                        print(f"[WARN] No fields to update for meal ID: {target_meal_id}")
                        continue
                        
                    # Use shared table object
                    saved_meals.update(target_meal_id, **update_fields)
                    
                    # Fetch updated name for confirmation message
                    updated_meal_data = saved_meals.read(target_meal_id)
                    updated_name = updated_meal_data[0]['name'] if updated_meal_data else item.name
                    change_msg = f"Updated meal: {updated_name} (ID: {target_meal_id}) | Fields: {list(update_fields.keys())}"
                    confirmation_messages.append(change_msg)
                    changes_made = True
                    meals_processed += 1
            
            # Construct final confirmation message
            if meals_processed > 0:
                final_confirmation = f"SAVED MEALS UPDATE CONFIRMATION ({meals_processed} meal(s))\n-------------------------------------\n" + "\n".join(confirmation_messages)
            else:
                final_confirmation = "No saved meals changes were detected or applied."
            
            return changes_made, final_confirmation
                  
        except Exception as e:
            print(f"[ERROR] Error processing saved meals changes: {e}")
            import traceback
            print(traceback.format_exc()) # Print detailed traceback
            return False, "An error occurred while processing saved meals changes."
        # No disconnect needed here 