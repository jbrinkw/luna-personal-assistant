"""
This module handles shopping list CRUD operations from natural language inputs.
"""

import os
import json
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from db.db_functions import Database, ShoppingList, IngredientsFood
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define models for extraction
class ShoppingListItem(BaseModel):
    operation: str = Field(..., description="CRUD operation: add, remove, update, clear")
    item_id: Optional[int] = Field(None, description="ID of the item to update or remove")
    item_name: Optional[str] = Field(None, description="Name of the item")
    amount: Optional[float] = Field(None, description="Amount to add/remove/update")
    units: Optional[str] = Field(None, description="Units for the amount (e.g., 'pounds', 'items')")

class ShoppingListItems(BaseModel):
    items: List[ShoppingListItem] = Field(..., description="List of shopping list items to be processed")

class ShoppingListProcessor:
    def __init__(self, shopping_list_table: ShoppingList, ingredients_table: IngredientsFood, db: Database):
        """Initialize processor with shared ShoppingList, IngredientsFood table objects and DB connection."""
        self.shopping_list_table = shopping_list_table # Store passed object
        self.ingredients_table = ingredients_table # Store passed object
        self.db = db # Store passed DB connection (needed for get_item_name etc)
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = "gpt-4o-mini" 
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, api_key=self.api_key)
        self.output_parser = PydanticOutputParser(pydantic_object=ShoppingListItems)
        self.format_instructions = self.output_parser.get_format_instructions()
        self.extraction_prompt_template = """\
Parse the following user input about shopping list changes.
For each shopping list item mentioned, extract the following fields:
- operation: either 'add', 'remove', 'update', or 'clear'
- item_id: for update or remove operations, the ID of the item
- item_name: the name of the item
- amount: numerical quantity
- units: units for the quantity (e.g., 'pounds', 'ounces', 'items')

Your main responsibility is to interpret natural language about shopping list changes and determine the appropriate operations:

1. When the user wants to add items to their shopping list:
   - Use "add" operation
   - Extract the item name and amount

2. When the user wants to update existing items:
   - Use "update" operation 
   - Include item_id if specified or if you can identify the item
   - Extract the new amount

3. When the user wants to remove items:
   - Use "remove" operation
   - Include item_id or use the name to identify the item

4. When the user wants to clear the shopping list:
   - Use "clear" operation
   - No other fields are needed

5. When handling multiple operations in a single request:
   - Split them into separate items with appropriate operations

Current Shopping List:
{current_shopping_list}

Available Food Items:
{available_food_items}

Return the results as a JSON object following this schema:
{format_instructions}

User Input: {user_input}
"""

    def get_shopping_and_food_info(self):
        """Get the current shopping list and available food items using shared objects."""
        # Use self.shopping_list_table and self.ingredients_table
        shopping_list = self.shopping_list_table
        ingredients_food = self.ingredients_table
        try:
            # Get all items from shopping list
            shopping_items = shopping_list.read()
            shopping_text = ""
            
            if not shopping_items:
                shopping_text = "Your shopping list is currently empty."
            else:
                shopping_text = "Items currently in your shopping list:\n"
                food_items = ingredients_food.read()
                food_dict = {item['id']: item['name'] for item in food_items} if food_items else {}
                
                for item in shopping_items:
                    item_id = item['id']
                    amount = item['amount']
                    name = food_dict.get(item_id, f"Unknown item (ID: {item_id})")
                    amount_str = f"{amount:.2f}" if isinstance(amount, float) and amount % 1 != 0 else str(amount)
                    shopping_text += f"- {name} (ID: {item_id}): {amount_str}\n"
            
            # Get all available food items
            food_items = ingredients_food.read()
            food_text = ""
            
            if not food_items:
                food_text = "No food items are currently available in the database."
            else:
                food_text = "Available food items that can be added to your shopping list:\n"
                for item in food_items:
                    food_text += f"ID: {item['id']}, Name: {item['name']}, Min amount: {item['min_amount_to_buy']}\n"
            
            return shopping_text, food_text
        except Exception as e:
            print(f"Error getting shopping list data in processor: {e}")
            return "Error retrieving shopping list.", "Error retrieving food items."
        # No disconnect needed

    def extract_shopping_items(self, user_input: str, shopping_list: str, food_items: str) -> ShoppingListItems:
        """Extract shopping list items from natural language input"""
        prompt = ChatPromptTemplate.from_template(template=self.extraction_prompt_template)
        messages = prompt.format_messages(
            user_input=user_input,
            format_instructions=self.format_instructions,
            current_shopping_list=shopping_list,
            available_food_items=food_items
        )
        response = self.chat.invoke(messages)
        print(f"[DEBUG] Extractor LLM raw output (truncated): '{response.content[:300]}...'")
        
        # Implement a fallback mechanism in case parsing fails
        try:
            extracted_items = self.output_parser.parse(response.content)
            return extracted_items
        except Exception as e:
            print(f"[ERROR] Failed to parse extractor output: {e}")
            # Create a minimal valid output to allow the process to continue
            return ShoppingListItems(items=[])

    def find_item_by_name(self, name: str) -> Optional[int]:
        """Find a food item ID by name using the shared ingredients table object."""
        if not name:
            return None
        
        # Use self.ingredients_table
        ingredients_food = self.ingredients_table
        try:
            all_items = ingredients_food.read()
            if not all_items:
                return None
                
            # Exact match
            for item in all_items:
                if item['name'].lower() == name.lower():
                    return item['id']
                    
            # Partial match
            for item in all_items:
                if name.lower() in item['name'].lower():
                    return item['id']
                    
            return None
        except Exception as e:
             print(f"[ERROR] Failed to find ingredient by name '{name}': {e}")
             return None

    def get_item_name(self, item_id: int) -> str:
        """Get the name of a food item by its ID using the shared ingredients table object."""
        # Use self.ingredients_table
        ingredients_food = self.ingredients_table
        try:
            item_result = ingredients_food.read(item_id)
            if item_result and item_result[0]:
                return item_result[0]['name']
            return f"Unknown item (ID: {item_id})"
        except Exception as e:
             print(f"[ERROR] Failed to get ingredient name for ID {item_id}: {e}")
             return f"Unknown item (ID: {item_id})"

    def process_shopping_list_changes(self, user_input: str) -> Tuple[bool, str]:
        """
        Process shopping list changes using shared table objects.
        """
        # Use self.shopping_list_table and self.ingredients_table
        shopping_list = self.shopping_list_table
        ingredients_food = self.ingredients_table # Needed for potential auto-add
        
        changes_made = False
        confirmation_messages = []
        items_processed = 0
        
        try:
            # Get current shopping list and food items for context
            current_shopping_list_text, available_food_items_text = self.get_shopping_and_food_info()
            
            # Extract shopping items from natural language input
            shopping_items = self.extract_shopping_items(user_input, current_shopping_list_text, available_food_items_text)
            
            # --- Handle Operations --- 
            operation_handled = {} # Track which operations have run (esp. for clear)

            for item in shopping_items.items:
                 op = item.operation.lower()
                 item_name = item.item_name
                 item_id = item.item_id
                 amount = item.amount
                 
                 # Resolve name to ID if ID is missing
                 if item_id is None and item_name:
                     item_id = self.find_item_by_name(item_name)
                 
                 # Handle CLEAR (runs only once)
                 if op == "clear" and "clear" not in operation_handled:
                     all_items = shopping_list.read()
                     if all_items:
                         initial_count = len(all_items)
                         for sl_item in all_items:
                             shopping_list.delete(sl_item['id']) 
                         confirmation_messages.append(f"Shopping list cleared ({initial_count} items removed)")
                         changes_made = True
                         items_processed += initial_count
                     else:
                         confirmation_messages.append("Shopping list was already empty.")
                     operation_handled["clear"] = True # Mark clear as handled
                 
                 # Handle ADD
                 elif op == "add":
                     if item_id is not None:
                         amount_to_add = amount if amount is not None else 1.0
                         shopping_list.create(item_id, amount_to_add) # create handles update if exists
                         resolved_name = self.get_item_name(item_id)
                         change_msg = f"Added/Updated {resolved_name} (Amount: {amount_to_add}) to shopping list"
                         confirmation_messages.append(change_msg)
                         changes_made = True
                         items_processed += 1
                     elif item_name:
                         # Optional: Auto-create ingredient if not found? Current setup warns.
                         print(f"[WARN] Cannot add '{item_name}' to shopping list, item not found in known ingredients.")
                     else:
                          print(f"[WARN] Skipping add operation, missing item name/ID: {item}")
                 
                 # Handle REMOVE
                 elif op == "remove":
                     if item_id is not None:
                         current_list_item = shopping_list.read(item_id)
                         if current_list_item and current_list_item[0]:
                             resolved_name = self.get_item_name(item_id)
                             shopping_list.delete(item_id)
                             change_msg = f"Removed {resolved_name} (ID: {item_id}) from shopping list"
                             confirmation_messages.append(change_msg)
                             changes_made = True
                             items_processed += 1
                         else:
                             resolved_name = self.get_item_name(item_id)
                             print(f"[INFO] Item '{resolved_name}' (ID: {item_id}) not found on shopping list, cannot remove.")
                     else:
                         print(f"[WARN] Could not find item to remove: {item_name or item_id}")
                 
                 # Handle UPDATE
                 elif op == "update":
                     if item_id is not None:
                         if amount is not None:
                             current_list_item = shopping_list.read(item_id)
                             resolved_name = self.get_item_name(item_id)
                             if current_list_item and current_list_item[0]:
                                 original_amount = current_list_item[0]['amount']
                                 shopping_list.update(item_id, amount)
                                 change_msg = f"Updated {resolved_name} amount from {original_amount} to {amount}"
                                 confirmation_messages.append(change_msg)
                                 changes_made = True
                                 items_processed += 1
                             else:
                                 print(f"[INFO] Item '{resolved_name}' not found on shopping list for update. Adding instead.")
                                 shopping_list.create(item_id, amount)
                                 change_msg = f"Added {resolved_name} with amount {amount} to shopping list (was not found for update)"
                                 confirmation_messages.append(change_msg)
                                 changes_made = True
                                 items_processed += 1
                         else:
                             resolved_name = self.get_item_name(item_id) if item_id else item_name
                             print(f"[WARN] Skipping update for {resolved_name}, no amount specified.")
                     else:
                         print(f"[WARN] Could not find item to update: {item_name or item_id}")

            # Check if clear was the *only* operation requested (and maybe successful)
            if "clear" in operation_handled and not any(op != "clear" for op in operation_handled):
                 pass # Already handled by the loop
            # Special case for implicit clear intent without explicit clear operation extracted
            elif not items_processed and ("clear" in user_input.lower() or "empty" in user_input.lower()):
                all_items = shopping_list.read()
                if all_items:
                    initial_count = len(all_items)
                    for item in all_items:
                        shopping_list.delete(item['id'])
                    confirmation_messages.insert(0, f"Shopping list cleared ({initial_count} items removed based on intent).")
                    changes_made = True
                    items_processed += initial_count
                elif not confirmation_messages: # Avoid duplicate message if already cleared
                     confirmation_messages.append("Shopping list is already empty.")
            
            # Construct final confirmation message
            if items_processed > 0:
                final_confirmation = f"SHOPPING LIST UPDATE CONFIRMATION ({items_processed} operation(s))\n-------------------------------------\n" + "\n".join(confirmation_messages)
            else:
                final_confirmation = "No changes were detected or applied to the shopping list."
                
            return changes_made, final_confirmation
        except Exception as e:
            print(f"[ERROR] Shopping list processor error: {e}")
            import traceback
            print(traceback.format_exc())
            return False, f"Failed to process shopping list changes: {e}"
        # No disconnect