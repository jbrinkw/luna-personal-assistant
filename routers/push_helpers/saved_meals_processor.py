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
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = "gpt-4o-mini"  # Using a simpler model for efficiency
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

    def get_current_saved_meals_text(self, db=None):
        """Get the current saved meals as a formatted text string for the prompt"""
        if not db:
            db = Database()
            saved_meals = SavedMeals(db)
            close_after = True
        else:
            saved_meals = SavedMeals(db)
            close_after = False
        
        try:
            current_meals = saved_meals.read()
            if not current_meals:
                return "There are no saved meals currently."
            
            meals_text = ""
            for meal in current_meals:
                # Format: ID, name, prep_time_minutes, ingredients (JSON), recipe
                meal_id = meal[0]
                name = meal[1]
                prep_time = meal[2]
                
                # Parse ingredients JSON
                try:
                    ingredients_json = json.loads(meal[3]) if isinstance(meal[3], str) else meal[3]
                    ingredients_text = ", ".join([f"{ing.get('name', 'Unknown')} ({ing.get('amount', 'Unknown')})" 
                                                for ing in ingredients_json])
                except:
                    ingredients_text = "Error parsing ingredients"
                
                # Truncate recipe text if too long
                recipe = meal[4][:100] + "..." if len(meal[4]) > 100 else meal[4]
                
                meals_text += f"ID: {meal_id}, Name: {name}, Prep Time: {prep_time} minutes\n"
                meals_text += f"Ingredients: {ingredients_text}\n"
                meals_text += f"Recipe: {recipe}\n\n"
            
            return meals_text
        except Exception as e:
            print(f"Error getting saved meals: {e}")
            return "Error retrieving saved meals."
        finally:
            if close_after:
                db.disconnect()

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

    def find_meal_by_name(self, name: str, saved_meals) -> Optional[int]:
        """Find a meal ID by name (case-insensitive partial match)"""
        if not name:
            return None
            
        all_meals = saved_meals.read()
        if not all_meals:
            return None
            
        # First try exact match
        for meal in all_meals:
            if meal[1].lower() == name.lower():
                return meal[0]
                
        # Then try partial match
        for meal in all_meals:
            if name.lower() in meal[1].lower():
                return meal[0]
                
        return None

    def process_saved_meals_changes(self, user_input: str) -> Tuple[bool, str]:
        """
        Process saved meals changes based on natural language input.
        Returns a tuple of (bool, str):
        - bool: True if any changes were made, False otherwise
        - str: Confirmation message with details of all changes made
        """
        # Initialize database connection
        db = Database()
        saved_meals = SavedMeals(db)
        
        # Track all changes made
        changes_made = False
        confirmation_messages = []
        meals_processed = 0
        
        try:
            # Get current saved meals for context
            current_saved_meals = self.get_current_saved_meals_text(db)
            
            # Extract meals from natural language input
            meal_items = self.extract_meals(user_input, current_saved_meals)
            
            # Special case for "delete all" if no items were extracted but user wants to delete all
            if (not meal_items.items and 
                ("delete all" in user_input.lower() or "remove all" in user_input.lower())):
                all_meals = saved_meals.read()
                if all_meals:
                    for meal in all_meals:
                        meal_id = meal[0]
                        saved_meals.delete(meal_id)
                        change_msg = f"Deleted meal: {meal[1]} (ID: {meal_id})"
                        confirmation_messages.append(change_msg)
                        changes_made = True
                        meals_processed += 1
            
            # Process each meal based on the operation determined by the LLM
            for item in meal_items.items:
                if item.operation.lower() == "create":
                    # Verify required fields for creation
                    if not item.name or not item.prep_time_minutes or not item.ingredients or not item.recipe:
                        print(f"[WARNING] Skipping create operation due to missing fields: {item}")
                        continue
                    
                    # Format ingredients for database
                    ingredients_list = []
                    for ing in item.ingredients:
                        ingredients_list.append({"name": ing.name, "amount": ing.amount})
                    
                    # Create new meal in database
                    meal_id = saved_meals.create(
                        item.name,
                        item.prep_time_minutes,
                        ingredients_list,
                        item.recipe
                    )
                    
                    if meal_id:
                        change_msg = f"Created meal: {item.name} (ID: {meal_id}) | Prep time: {item.prep_time_minutes} mins | Ingredients: {len(ingredients_list)}"
                        confirmation_messages.append(change_msg)
                        changes_made = True
                        meals_processed += 1
                
                elif item.operation.lower() == "delete":
                    # Delete by ID if available
                    if item.meal_id is not None:
                        # Get meal details before deletion for confirmation message
                        current = saved_meals.read(item.meal_id)
                        if current and current[0]:
                            meal_name = current[0][1]
                            saved_meals.delete(item.meal_id)
                            change_msg = f"Deleted meal: {meal_name} (ID: {item.meal_id})"
                            confirmation_messages.append(change_msg)
                            changes_made = True
                            meals_processed += 1
                    # Otherwise, try to find by name
                    elif item.name:
                        meal_id = self.find_meal_by_name(item.name, saved_meals)
                        if meal_id:
                            current = saved_meals.read(meal_id)
                            if current and current[0]:
                                meal_name = current[0][1]
                                saved_meals.delete(meal_id)
                                change_msg = f"Deleted meal: {meal_name} (ID: {meal_id})"
                                confirmation_messages.append(change_msg)
                                changes_made = True
                                meals_processed += 1
                        else:
                            print(f"[WARNING] Could not find meal to delete: {item.name}")
                
                elif item.operation.lower() == "update":
                    # Validate meal_id for update
                    if item.meal_id is None and item.name:
                        # Try to find meal by name
                        item.meal_id = self.find_meal_by_name(item.name, saved_meals)
                    
                    if item.meal_id is None:
                        print(f"[WARNING] Skipping update operation due to missing meal_id: {item}")
                        continue
                    
                    # Build update with only the fields that are provided
                    update_fields = {}
                    if item.name is not None:
                        update_fields["name"] = item.name
                    
                    if item.prep_time_minutes is not None:
                        update_fields["prep_time_minutes"] = item.prep_time_minutes
                    
                    if item.recipe is not None:
                        update_fields["recipe"] = item.recipe
                    
                    if item.ingredients is not None:
                        ingredients_list = []
                        for ing in item.ingredients:
                            ingredients_list.append({"name": ing.name, "amount": ing.amount})
                        update_fields["ingredients"] = ingredients_list
                    
                    # If there are fields to update, perform update
                    if update_fields:
                        current = saved_meals.read(item.meal_id)
                        if current and current[0]:
                            updated_fields = []
                            if "name" in update_fields:
                                updated_fields.append(f"name: {current[0][1]} → {update_fields['name']}")
                            if "prep_time_minutes" in update_fields:
                                updated_fields.append(f"prep time: {current[0][2]} → {update_fields['prep_time_minutes']} mins")
                            if "ingredients" in update_fields:
                                updated_fields.append(f"ingredients updated")
                            if "recipe" in update_fields:
                                updated_fields.append(f"recipe updated")
                            
                            saved_meals.update(
                                item.meal_id,
                                update_fields.get("name"),
                                update_fields.get("prep_time_minutes"),
                                update_fields.get("ingredients"),
                                update_fields.get("recipe")
                            )
                            
                            meal_name = update_fields.get("name", current[0][1])
                            change_msg = f"Updated meal: {meal_name} (ID: {item.meal_id}) | Changes: {', '.join(updated_fields)}"
                            confirmation_messages.append(change_msg)
                            changes_made = True
                            meals_processed += 1
            
            print(f"[DEBUG] Processed {meals_processed} saved meal items. Changes: {confirmation_messages}")
            
            # Prepare confirmation message
            if confirmation_messages:
                confirmation = "SAVED MEALS CHANGES:\n"
                confirmation += "\n".join(confirmation_messages)
                
                # Get current saved meals after changes
                current_saved_meals_data = saved_meals.read()
                if current_saved_meals_data:
                    confirmation += "\n\nCURRENT SAVED MEALS:\n"
                    for meal in current_saved_meals_data:
                        confirmation += f"ID: {meal[0]}, Name: {meal[1]}, Prep Time: {meal[2]} minutes\n"
                else:
                    confirmation += "\n\nNo saved meals in database."
                
                return changes_made, confirmation
            else:
                return changes_made, "No changes were made to saved meals."
                
        except Exception as e:
            print(f"[ERROR] Saved meals processor error: {e}")
            return False, f"Error processing saved meals changes: {e}"
        finally:
            # Disconnect from database
            db.disconnect() 