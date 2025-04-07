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
    def __init__(self, inventory_table: Inventory, db: Database):
        """Initialize processor with shared Inventory table object and DB connection."""
        self.inventory_table = inventory_table # Store passed Inventory object
        self.db = db # Store passed Database connection (for get_current_inventory_text)
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = "gpt-4o-mini" 
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

    def get_current_inventory_text(self):
        """Get the current inventory using the shared inventory table object."""
        # No need to create db or inventory object here, use self.inventory_table
        try:
            current_items = self.inventory_table.read()
            if not current_items:
                return "The inventory is currently empty."
            
            inventory_text = ""
            for item in current_items:
                # Access by column name
                inventory_text += f"ID: {item['id']}, Name: {item['name']}, Quantity: {item['quantity']}, Expires: {item['expiration'] or 'N/A'}\n"
            
            return inventory_text
        except Exception as e:
            print(f"[ERROR] Failed to get current inventory text in processor: {e}")
            return "Error retrieving current inventory."
        # No disconnect needed here, managed centrally

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
        Uses the shared self.inventory_table object.
        """
        # No need to initialize db or inventory here
        # Use self.inventory_table directly
        inventory = self.inventory_table 
        
        # Track all changes made
        changes_made = False
        confirmation_messages = []
        items_processed = 0
        
        try:
            # Get current inventory for context using refactored method
            current_inventory_text = self.get_current_inventory_text()
            
            # Extract items from natural language input
            inventory_items = self.extract_items(user_input, current_inventory_text)
            
            # Process each item based on the operation determined by the LLM
            for item in inventory_items.items:
                if item.operation.lower() == "add":
                    # Use self.inventory_table
                    inventory.create(item.name, item.quantity, item.expiration)
                    change_msg = f"Added: {item.name} | {item.quantity} | Expires: {item.expiration or 'N/A'}"
                    confirmation_messages.append(change_msg)
                    changes_made = True
                    items_processed += 1
                
                elif item.operation.lower() == "delete":
                    target_item_id = item.item_id
                    item_found_and_deleted = False
                    # Find item to delete
                    if target_item_id is None and item.name:
                        # Find by name if ID not provided
                        all_items = inventory.read()
                        if all_items:
                           for db_item in all_items:
                               if db_item['name'].lower() == item.name.lower():
                                   target_item_id = db_item['id']
                                   break # Found first match by name

                    if target_item_id is not None:
                        # Get item details before deletion for confirmation message
                        current_result = inventory.read(target_item_id)
                        if current_result and current_result[0]:
                            current_item = current_result[0]
                            item_name = current_item['name'] 
                            item_quantity = current_item['quantity']
                            item_expiration = current_item['expiration'] or "N/A"
                            inventory.delete(target_item_id)
                            change_msg = f"Deleted: {item_name} | {item_quantity} | Expires: {item_expiration}"
                            confirmation_messages.append(change_msg)
                            changes_made = True
                            items_processed += 1
                            item_found_and_deleted = True
                        
                    if not item_found_and_deleted:
                         print(f"[WARN] Could not find item to delete: {item.name or item.item_id}")

                
                elif item.operation.lower() == "update":
                    target_item_id = item.item_id
                    item_found_and_updated = False
                    # Find item to update
                    if target_item_id is None and item.name:
                        # Find by name if ID not provided
                        all_items = inventory.read()
                        if all_items:
                           for db_item in all_items:
                               if db_item['name'].lower() == item.name.lower():
                                   target_item_id = db_item['id']
                                   break # Found first match by name

                    if target_item_id is not None:
                        # Get current item to calculate new quantity if needed
                        current_result = inventory.read(target_item_id)
                        if current_result and current_result[0]:
                            current_item = current_result[0]
                            # Determine new name/expiration, defaulting to current if not provided in update
                            name = item.name if item.name and item.name != current_item['name'] else current_item['name']
                            current_expiration_str = current_item['expiration']
                            expiration = item.expiration if item.expiration else current_expiration_str
                            
                            # Extract numeric quantities
                            current_qty_num = self.extract_numeric_quantity(current_item['quantity'])
                            update_qty_num = self.extract_numeric_quantity(item.quantity)
                            unit = self.get_unit_from_quantity(current_item['quantity']) or self.get_unit_from_quantity(item.quantity)
                            new_qty_num = current_qty_num + update_qty_num
                            
                            if new_qty_num <= 0:
                                inventory.delete(target_item_id)
                                change_msg = f"Deleted: {name} | {current_item['quantity']} | Expires: {current_expiration_str or 'N/A'} (quantity became <= 0)"
                            else:
                                new_quantity = f"{new_qty_num:.2f} {unit}".strip() if isinstance(new_qty_num, float) and new_qty_num % 1 != 0 else f"{int(new_qty_num)} {unit}".strip()
                                inventory.update(target_item_id, name, new_quantity, expiration)
                                change_msg = f"Updated: {name} | {current_item['quantity']} → {new_quantity} | Expires: {expiration or 'N/A'}"
                                
                            confirmation_messages.append(change_msg)
                            changes_made = True
                            items_processed += 1
                            item_found_and_updated = True
                            
                    if not item_found_and_updated:
                         print(f"[WARN] Could not find item to update: {item.name or item.item_id}")
            
            # Construct final confirmation message
            if items_processed > 0:
                final_confirmation = f"INVENTORY UPDATE CONFIRMATION ({items_processed} item(s))\n-------------------------------------\n" + "\n".join(confirmation_messages)
            else:
                final_confirmation = "No inventory changes were detected or applied."
            
            return changes_made, final_confirmation
                  
        except Exception as e:
            print(f"[ERROR] Error processing inventory changes: {e}")
            import traceback
            print(traceback.format_exc()) # Print detailed traceback
            return False, "An error occurred while processing inventory changes."
        # No disconnect needed here 