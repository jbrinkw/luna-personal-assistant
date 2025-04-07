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

from db.db_functions import Database, SavedMeals
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
                
                # Parse ingredients JSON
                ingredients_text = "[Invalid Ingredients Data]" # Default
                try:
                    ingredients_json = json.loads(ingredients_col) if isinstance(ingredients_col, str) else ingredients_col 
                    if isinstance(ingredients_json, list): 
                        ingredients_text = ", ".join([f"{ing.get('name', '?')} ({ing.get('amount', '?')})" 
                                                    for ing in ingredients_json])
                    else:
                         ingredients_text = str(ingredients_json)
                except (json.JSONDecodeError, TypeError) as e:
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
                    
                    ingredients_list = [{"name": ing.name, "amount": ing.amount} for ing in item.ingredients]
                    
                    # Use shared table object
                    meal_id = saved_meals.create(
                        item.name,
                        item.prep_time_minutes,
                        ingredients_list,
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
                    current_meal_data = None
                    item_found_and_updated = False

                    if target_meal_id is None and item.name:
                        target_meal_id = self.find_meal_by_name(item.name)

                    if target_meal_id is not None:
                        current = saved_meals.read(target_meal_id)
                        if current and current[0]:
                           current_meal_data = current[0]

                    if target_meal_id is not None and current_meal_data is not None:
                        update_params = {"meal_id": target_meal_id}
                        original_details = []
                        updated_details = []

                        if item.name is not None and item.name != current_meal_data['name']:
                            update_params['name'] = item.name
                            original_details.append(f"Name: {current_meal_data['name']}")
                            updated_details.append(f"Name: {item.name}")
                            
                        if item.prep_time_minutes is not None and item.prep_time_minutes != current_meal_data['prep_time_minutes']:
                            update_params['prep_time_minutes'] = item.prep_time_minutes
                            original_details.append(f"Prep: {current_meal_data['prep_time_minutes']}m")
                            updated_details.append(f"Prep: {item.prep_time_minutes}m")
                            
                        if item.ingredients is not None:
                            ingredients_list = [{"name": ing.name, "amount": ing.amount} for ing in item.ingredients]
                            update_params['ingredients'] = ingredients_list
                            original_details.append("Ingredients changed")
                            updated_details.append(f"{len(ingredients_list)} ingredients")
                            
                        if item.recipe is not None and item.recipe != current_meal_data['recipe']:
                            update_params['recipe'] = item.recipe
                            original_details.append("Recipe changed")
                            updated_details.append("Recipe updated")

                        if len(update_params) > 1: 
                            # Use shared table object
                            update_result = saved_meals.update(**update_params)
                            
                            meal_name = current_meal_data['name'] if 'name' not in update_params else update_params['name']
                            change_msg = f"Updated: {meal_name} (ID: {target_meal_id})\n Changes: {', '.join(updated_details)}"
                            confirmation_messages.append(change_msg)
                            changes_made = True
                            meals_processed += 1
                            item_found_and_updated = True
                        else:
                            print(f"[INFO] No actual changes detected for update on meal ID {target_meal_id}")
                            
                    if not item_found_and_updated:
                        print(f"[WARN] Could not find meal to update: {item.name or item.meal_id}")
            
            # Construct final confirmation message
            if meals_processed > 0:
                final_confirmation = f"SAVED MEALS UPDATE CONFIRMATION ({meals_processed} operation(s))\n-------------------------------------\n" + "\n".join(confirmation_messages)
            else:
                final_confirmation = "No changes were detected or applied to saved meals."
                
            return changes_made, final_confirmation
        except Exception as e:
            print(f"[ERROR] Saved meals processor error: {e}")
            import traceback
            print(traceback.format_exc())
            return False, f"Failed to process saved meals changes: {e}"
        # No disconnect 