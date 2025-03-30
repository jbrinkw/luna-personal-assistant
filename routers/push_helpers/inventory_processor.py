"""
This module handles inventory changes processing from natural language inputs.
"""

import os
import re
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from db.db_functions import Database, Inventory
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define models for extraction
class InventoryItem(BaseModel):
    operation: str = Field(..., description="CRUD operation: add, delete, or update")
    name: str = Field(..., description="Simplified item name")
    quantity: str = Field(..., description="Quantity with units (e.g., '1 gallon', '2 pounds')")
    expiration: Optional[str] = Field(None, description="Expiration date in YYYY-MM-DD format")
    item_id: Optional[int] = Field(None, description="ID of the item to update or delete")

class InventoryItems(BaseModel):
    items: List[InventoryItem] = Field(..., description="List of inventory items to be processed")

class NaturalLanguageInventoryProcessor:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = "gpt-4o-mini"  # Using a simpler model for efficiency
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, api_key=self.api_key)
        self.output_parser = PydanticOutputParser(pydantic_object=InventoryItems)
        self.format_instructions = self.output_parser.get_format_instructions()
        self.extraction_prompt_template = """\
Parse the following user input about inventory changes.
For each item mentioned, extract the following fields:
- operation: either 'add', 'delete', or 'update'
- name: a simplified item name
- quantity: the quantity with units (e.g., '1 gallon')
- expiration: the expiration date in YYYY-MM-DD format
- item_id: for update or delete operations, the ID of the item to modify

Your main responsibility is to interpret natural language about inventory and determine the appropriate operations:

1. When the user wants to "add" something that already exists in inventory (or something very similar):
   - Use "update" operation instead of "add"
   - Identify the existing item ID and include it
   - Example: if "whole milk" exists and user says "add milk", mark it as update with the ID of whole milk

2. When the user mentions adding expiration dates to existing items:
   - Mark it as "update" operation and include the item ID
   - For perishable items without specified dates, suggest reasonable expiration dates

3. For quantities:
   - If not specified, use sensible defaults like "1 unit" or "1 pound"
   - For updates, include the quantity to add (not the total)
   - IMPORTANT: Use NEGATIVE quantities when the user consumes or uses items
   - Example: "I drank a glass of milk" → update with quantity "-1 glass"
   - Example: "I used 2 eggs" → update with quantity "-2"
   - Example: "I finished the cereal" → update with quantity that will zero out the item

4. When the user wants to remove items:
   - ONLY use the "delete" operation when the user wants to remove an item COMPLETELY and DOES NOT specify a quantity
   - Example: "remove the cheese" → delete operation
   - Example: "throw away the expired milk" → delete operation
   - If the user specifies a quantity to reduce, use "update" with a NEGATIVE quantity instead
   - Example: "remove 3 apples" → update with quantity "-3 apples"
   - Example: "take out 2 eggs" → update with quantity "-2 eggs"
   - For ambiguous deletions (e.g., "remove milk" when multiple milk items exist), prefer the oldest or most generic item

Current Inventory:
{current_inventory}

Return the results as a JSON object following this schema:
{format_instructions}

User Input: {user_input}
"""

    def get_current_inventory_text(self, db=None):
        """Get the current inventory as a formatted text string for the prompt"""
        if not db:
            db = Database()
            inventory = Inventory(db)
            close_after = True
        else:
            inventory = Inventory(db)
            close_after = False
        
        try:
            current_items = inventory.read()
            if not current_items:
                return "The inventory is currently empty."
            
            inventory_text = ""
            for item in current_items:
                inventory_text += f"ID: {item[0]}, Name: {item[1]}, Quantity: {item[2]}, Expires: {item[3] or 'N/A'}\n"
            
            return inventory_text
        finally:
            if close_after:
                db.disconnect()

    def extract_items(self, user_input: str, current_inventory: str) -> InventoryItems:
        prompt = ChatPromptTemplate.from_template(template=self.extraction_prompt_template)
        messages = prompt.format_messages(
            user_input=user_input,
            format_instructions=self.format_instructions,
            current_inventory=current_inventory
        )
        response = self.chat.invoke(messages)
        # Print raw LLM output for debugging
        #print(f"[DEBUG] Extractor LLM raw output (truncated): '{response.content[:300]}...'")
        
        extracted_items = self.output_parser.parse(response.content)
        return extracted_items
        
    def extract_numeric_quantity(self, quantity_str):
        """Extract numeric value from quantity string like '2 pounds' -> 2"""
        # Find all numbers in the string (handles decimals too)
        numbers = re.findall(r'-?\d+\.?\d*', quantity_str)
        if numbers:
            return float(numbers[0])
        return 1.0  # Default to 1 if no number found
    
    def get_unit_from_quantity(self, quantity_str):
        """Extract unit from quantity string like '2 pounds' -> 'pounds'"""
        # Remove all digits, decimal points, and common separators
        unit = re.sub(r'[-\d.,]+', '', quantity_str).strip()
        # Return the unit or a default
        return unit if unit else "units"

    def process_inventory_changes(self, user_input: str) -> Tuple[bool, str]:
        """
        Process inventory changes based on natural language input.
        Returns a tuple of (bool, str):
        - bool: True if any changes were made, False otherwise
        - str: Confirmation message with details of all changes made
        """
        # Initialize database connection
        db = Database()
        inventory = Inventory(db)
        
        # Track all changes made
        changes_made = False
        confirmation_messages = []
        items_processed = 0
        
        try:
            # Get current inventory for context
            current_inventory = self.get_current_inventory_text(db)
            
            # Extract items from natural language input
            inventory_items = self.extract_items(user_input, current_inventory)
            
            # Process each item based on the operation determined by the LLM
            for item in inventory_items.items:
                if item.operation.lower() == "add":
                    # Add new item to inventory
                    inventory.create(item.name, item.quantity, item.expiration)
                    change_msg = f"Added: {item.name} | {item.quantity} | Expires: {item.expiration or 'N/A'}"
                    confirmation_messages.append(change_msg)
                    changes_made = True
                    items_processed += 1
                
                elif item.operation.lower() == "delete":
                    # Find items with matching name or ID
                    if item.item_id:
                        # Get item details before deletion for confirmation message
                        current = inventory.read(item.item_id)
                        if current and current[0]:
                            item_name = current[0][1]
                            item_quantity = current[0][2]
                            item_expiration = current[0][3].strftime("%Y-%m-%d") if current[0][3] else "N/A"
                            inventory.delete(item.item_id)
                            change_msg = f"Deleted: {item_name} | {item_quantity} | Expires: {item_expiration}"
                            confirmation_messages.append(change_msg)
                            changes_made = True
                            items_processed += 1
                    else:
                        all_items = inventory.read()
                        for db_item in all_items:
                            if db_item[1].lower() == item.name.lower():
                                item_name = db_item[1]
                                item_quantity = db_item[2]
                                item_expiration = db_item[3].strftime("%Y-%m-%d") if db_item[3] else "N/A"
                                inventory.delete(db_item[0])
                                change_msg = f"Deleted: {item_name} | {item_quantity} | Expires: {item_expiration}"
                                confirmation_messages.append(change_msg)
                                changes_made = True
                                items_processed += 1
                                break
                
                elif item.operation.lower() == "update":
                    # Update based on item_id if provided
                    if item.item_id is not None:
                        # Get current item to calculate new quantity if needed
                        current = inventory.read(item.item_id)
                        if current:
                            current_item = current[0]
                            # Keep original name if not specified
                            name = item.name if item.name != current_item[1] else current_item[1]
                            # Keep original expiration if not specified
                            expiration = item.expiration if item.expiration else current_item[3]
                            
                            # Extract numeric values from quantities
                            current_qty_num = self.extract_numeric_quantity(current_item[2])
                            update_qty_num = self.extract_numeric_quantity(item.quantity)
                            
                            # Get unit from current quantity or use the update's unit
                            unit = self.get_unit_from_quantity(current_item[2]) or self.get_unit_from_quantity(item.quantity)
                            
                            # Calculate new quantity
                            new_qty_num = current_qty_num + update_qty_num
                            
                            # If quantity becomes zero or negative, delete the item
                            if new_qty_num <= 0:
                                inventory.delete(item.item_id)
                                change_msg = f"Deleted: {name} | {current_item[2]} | Expires: {current_item[3].strftime('%Y-%m-%d') if current_item[3] else 'N/A'} (quantity is now {new_qty_num})"
                                confirmation_messages.append(change_msg)
                                changes_made = True
                                items_processed += 1
                            else:
                                # Format new quantity with unit
                                new_quantity = f"{new_qty_num} {unit}".strip()
                                
                                # Update the item with new quantity
                                inventory.update(item.item_id, name, new_quantity, expiration)
                                change_msg = f"Updated: {name} | {current_item[2]} → {new_quantity} | Expires: {expiration.strftime('%Y-%m-%d') if expiration else 'N/A'}"
                                confirmation_messages.append(change_msg)
                                changes_made = True
                                items_processed += 1
                    # Fallback to name matching if no item_id
                    else:
                        all_items = inventory.read()
                        for db_item in all_items:
                            if db_item[1].lower() == item.name.lower():
                                # Extract numeric values from quantities
                                current_qty_num = self.extract_numeric_quantity(db_item[2])
                                update_qty_num = self.extract_numeric_quantity(item.quantity)
                                
                                # Get unit from current quantity or use the update's unit
                                unit = self.get_unit_from_quantity(db_item[2]) or self.get_unit_from_quantity(item.quantity)
                                
                                # Calculate new quantity
                                new_qty_num = current_qty_num + update_qty_num
                                
                                # If quantity becomes zero or negative, delete the item
                                if new_qty_num <= 0:
                                    inventory.delete(db_item[0])
                                    change_msg = f"Deleted: {db_item[1]} | {db_item[2]} | Expires: {db_item[3].strftime('%Y-%m-%d') if db_item[3] else 'N/A'} (quantity is now {new_qty_num})"
                                    confirmation_messages.append(change_msg)
                                    changes_made = True
                                    items_processed += 1
                                else:
                                    # Format new quantity with unit
                                    new_quantity = f"{new_qty_num} {unit}".strip()
                                    
                                    # Update the item with new quantity
                                    expiration = item.expiration if item.expiration else db_item[3]
                                    inventory.update(db_item[0], item.name, new_quantity, expiration)
                                    change_msg = f"Updated: {item.name} | {db_item[2]} → {new_quantity} | Expires: {expiration.strftime('%Y-%m-%d') if expiration else 'N/A'}"
                                    confirmation_messages.append(change_msg)
                                    changes_made = True
                                    items_processed += 1
                                break
            
            print(f"[DEBUG] Processed {items_processed} inventory items. Changes: {confirmation_messages}")
            
            # Prepare confirmation message
            if confirmation_messages:
                # Get current inventory after changes
                current_inventory_data = inventory.read()
                current_inventory_summary = []
                if current_inventory_data:
                    for item in current_inventory_data:
                        expiration = item[3].strftime("%Y-%m-%d") if item[3] else "N/A"
                        current_inventory_summary.append(f"{item[1]} | {item[2]} | Expires: {expiration}")
                
                confirmation = "INVENTORY CHANGES:\n"
                confirmation += "\n".join(confirmation_messages)
                confirmation += "\n\nCURRENT INVENTORY:\n"
                
                if current_inventory_summary:
                    confirmation += "\n".join(current_inventory_summary)
                else:
                    confirmation += "Inventory is empty."
                
                return changes_made, confirmation
            else:
                return changes_made, ""
                
        except Exception as e:
            print(f"[ERROR] Inventory processor error: {e}")
            return False, ""
        finally:
            # Disconnect from database
            db.disconnect() 