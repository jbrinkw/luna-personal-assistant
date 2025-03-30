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
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = "gpt-4o-mini"  # Using a simpler model for efficiency
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

    def get_shopping_and_food_info(self, db=None):
        """Get the current shopping list and available food items as formatted text strings for the prompt"""
        if not db:
            db = Database()
            close_after = True
        else:
            close_after = False
        
        try:
            # Initialize tables
            shopping_list = ShoppingList(db)
            ingredients_food = IngredientsFood(db)
            
            # Get all items from shopping list
            shopping_items = shopping_list.read()
            shopping_text = ""
            
            if not shopping_items:
                shopping_text = "Your shopping list is currently empty."
            else:
                shopping_text = "Items currently in your shopping list:\n"
                food_items = ingredients_food.read()
                food_dict = {item[0]: item[1] for item in food_items} if food_items else {}
                
                for item in shopping_items:
                    item_id = item[0]
                    amount = item[1]
                    name = food_dict.get(item_id, f"Unknown item (ID: {item_id})")
                    shopping_text += f"- {name}: {amount}\n"
            
            # Get all available food items
            food_items = ingredients_food.read()
            food_text = ""
            
            if not food_items:
                food_text = "No food items are currently available in the database."
            else:
                food_text = "Available food items that can be added to your shopping list:\n"
                for item in food_items:
                    food_text += f"ID: {item[0]}, Name: {item[1]}, Min amount to buy: {item[2]}\n"
            
            return shopping_text, food_text
        except Exception as e:
            print(f"Error getting shopping list data: {e}")
            return "Error retrieving shopping list.", "Error retrieving food items."
        finally:
            if close_after:
                db.disconnect()

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

    def find_item_by_name(self, name: str, db) -> Optional[int]:
        """Find a food item ID by name (case-insensitive)"""
        if not name:
            return None
            
        ingredients_food = IngredientsFood(db)
        all_items = ingredients_food.read()
        if not all_items:
            return None
            
        # First try exact match
        for item in all_items:
            if item[1].lower() == name.lower():
                return item[0]
                
        # Then try partial match
        for item in all_items:
            if name.lower() in item[1].lower():
                return item[0]
                
        return None

    def get_item_name(self, item_id: int, db) -> str:
        """Get the name of a food item by its ID"""
        ingredients_food = IngredientsFood(db)
        item = ingredients_food.read(item_id)
        if item and item[0]:
            return item[0][1]
        return f"Unknown item (ID: {item_id})"

    def process_shopping_list_changes(self, user_input: str) -> Tuple[bool, str]:
        """
        Process shopping list changes based on natural language input.
        Returns a tuple of (bool, str):
        - bool: True if any changes were made, False otherwise
        - str: Confirmation message with details of all changes made
        """
        # Initialize database connection
        db = Database()
        shopping_list = ShoppingList(db)
        
        # Track all changes made
        changes_made = False
        confirmation_messages = []
        items_processed = 0
        
        try:
            # Get current shopping list and food items for context
            current_shopping_list, available_food_items = self.get_shopping_and_food_info(db)
            
            # Extract shopping items from natural language input
            shopping_items = self.extract_shopping_items(user_input, current_shopping_list, available_food_items)
            
            # Special case for "clear" if no items were extracted but user wants to clear the list
            if (not shopping_items.items and 
                ("clear" in user_input.lower() or "empty" in user_input.lower() or "remove all" in user_input.lower())):
                all_items = shopping_list.read()
                if all_items:
                    for item in all_items:
                        item_id = item[0]
                        item_name = self.get_item_name(item_id, db)
                        shopping_list.delete(item_id)
                        change_msg = f"Removed {item_name} (ID: {item_id}) from shopping list"
                        confirmation_messages.append(change_msg)
                        changes_made = True
                        items_processed += 1
                    
                    if items_processed > 0:
                        confirmation_messages.insert(0, "Shopping list cleared")
            
            # Process each item based on the operation determined by the LLM
            for item in shopping_items.items:
                if item.operation.lower() == "clear":
                    # Clear the entire shopping list
                    all_items = shopping_list.read()
                    if all_items:
                        for sl_item in all_items:
                            item_id = sl_item[0]
                            item_name = self.get_item_name(item_id, db)
                            shopping_list.delete(item_id)
                        
                        confirmation_messages.append("Shopping list cleared")
                        changes_made = True
                        items_processed += len(all_items)
                
                elif item.operation.lower() == "add":
                    # Verify required fields for adding
                    if not item.item_name:
                        print(f"[WARNING] Skipping add operation due to missing item name: {item}")
                        continue
                    
                    # Find item id from name if not provided
                    if item.item_id is None:
                        item.item_id = self.find_item_by_name(item.item_name, db)
                    
                    # If item id is still None, we need to create a new food item
                    if item.item_id is None:
                        print(f"[WARNING] Could not find food item: {item.item_name}")
                        # For testing purposes only, auto-create a minimal food item
                        ingredients_food = IngredientsFood(db)
                        min_amount = 1
                        item.item_id = ingredients_food.create(item.item_name, min_amount)
                        print(f"[INFO] Created new food item: {item.item_name} (ID: {item.item_id})")
                    
                    # Use a default amount if not specified
                    amount = item.amount if item.amount is not None else 1.0
                    
                    # Update the shopping list (create uses ON CONFLICT to handle updates)
                    shopping_list.create(item.item_id, amount)
                    
                    item_name = self.get_item_name(item.item_id, db)
                    unit_text = f" {item.units}" if item.units else ""
                    change_msg = f"Added {amount}{unit_text} {item_name} to shopping list"
                    confirmation_messages.append(change_msg)
                    changes_made = True
                    items_processed += 1
                
                elif item.operation.lower() == "remove":
                    # Find item id from name if not provided
                    if item.item_id is None and item.item_name:
                        item.item_id = self.find_item_by_name(item.item_name, db)
                    
                    if item.item_id is None:
                        print(f"[WARNING] Could not find item to remove: {item.item_name}")
                        continue
                    
                    # Check if the item exists in the shopping list
                    existing = shopping_list.read(item.item_id)
                    if existing and existing[0]:
                        item_name = self.get_item_name(item.item_id, db)
                        shopping_list.delete(item.item_id)
                        change_msg = f"Removed {item_name} from shopping list"
                        confirmation_messages.append(change_msg)
                        changes_made = True
                        items_processed += 1
                    else:
                        print(f"[WARNING] Item not in shopping list: {item.item_name}")
                
                elif item.operation.lower() == "update":
                    # Find item id from name if not provided
                    if item.item_id is None and item.item_name:
                        item.item_id = self.find_item_by_name(item.item_name, db)
                    
                    if item.item_id is None:
                        print(f"[WARNING] Could not find item to update: {item.item_name}")
                        continue
                    
                    # Verify required fields for updating
                    if item.amount is None:
                        print(f"[WARNING] Skipping update operation due to missing amount: {item}")
                        continue
                    
                    # Check if the item exists in the shopping list
                    existing = shopping_list.read(item.item_id)
                    if existing and existing[0]:
                        old_amount = existing[0][1]
                        item_name = self.get_item_name(item.item_id, db)
                        shopping_list.update(item.item_id, item.amount)
                        unit_text = f" {item.units}" if item.units else ""
                        change_msg = f"Updated {item_name} in shopping list: {old_amount} → {item.amount}{unit_text}"
                        confirmation_messages.append(change_msg)
                        changes_made = True
                        items_processed += 1
                    else:
                        # If item doesn't exist in the shopping list, add it
                        shopping_list.create(item.item_id, item.amount)
                        item_name = self.get_item_name(item.item_id, db)
                        unit_text = f" {item.units}" if item.units else ""
                        change_msg = f"Added {item.amount}{unit_text} {item_name} to shopping list"
                        confirmation_messages.append(change_msg)
                        changes_made = True
                        items_processed += 1
            
            print(f"[DEBUG] Processed {items_processed} shopping list items. Changes: {confirmation_messages}")
            
            # Prepare confirmation message
            if confirmation_messages:
                confirmation = "SHOPPING LIST CHANGES:\n"
                confirmation += "\n".join(confirmation_messages)
                
                # Get current shopping list after changes
                confirmation += "\n\nCURRENT SHOPPING LIST:\n"
                updated_shopping_list, _ = self.get_shopping_and_food_info(db)
                confirmation += updated_shopping_list
                
                return changes_made, confirmation
            else:
                return changes_made, "No changes were made to the shopping list."
                
        except Exception as e:
            print(f"[ERROR] Shopping list processor error: {e}")
            return False, f"Error processing shopping list changes: {e}"
        finally:
            # Disconnect from database
            db.disconnect() 