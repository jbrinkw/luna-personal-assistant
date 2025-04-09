"""
This module handles inventory changes processing from natural language inputs.
"""

import os
import re
import sys # Add sys import
import traceback
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from db.db_functions import Database, Inventory, IngredientsFood
from helpers.ingredient_translator import IngredientTranslator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Add project root to sys.path ---
# This allows imports like `from db.db_functions import ...` to work correctly
# when the script is run directly from within its subdirectory.
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# Try using getcwd() assuming script is run from project root
project_root = os.getcwd() 
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End sys.path modification ---
print(f"DEBUG: sys.path after modification: {sys.path}") # Add this line

# Define models for extraction
class InventoryItem(BaseModel):
    operation: str = Field(..., description="CRUD operation: add, delete, or update")
    name: str = Field(..., description="Simplified item name")
    quantity: Optional[str] = Field(None, description="Quantity with units (e.g., '1 gallon', '2 pounds')") # Made Optional
    expiration: Optional[str] = Field(None, description="Expiration date in YYYY-MM-DD format")
    item_id: Optional[int] = Field(None, description="ID of the item to update or delete")

class InventoryItems(BaseModel):
    items: List[InventoryItem] = Field(..., description="List of inventory items to be processed")

class NaturalLanguageInventoryProcessor:
    def __init__(self, inventory_table: Inventory, db: Database):
        """Initialize processor with shared Inventory table object and DB connection."""
        self.inventory_table = inventory_table # Store passed Inventory object
        self.db = db # Store passed Database connection (for get_current_inventory_text)
        
        # Fetch the IngredientsFood table object needed by the translator
        # This assumes init_tables() was called elsewhere and db object is valid
        # A more robust approach might pass tables dict or the specific table obj
        try:
            # Ensure connection is active before using cursor
            if not self.db.conn:
                 self.db.connect()
            if not self.db.conn: # Check again after trying to connect
                 raise ConnectionError("Database connection failed before checking ingredients_foods")
                 
            temp_cursor = self.db.conn.cursor()
            temp_cursor.execute("SELECT 1 FROM ingredients_foods LIMIT 1") # Check if table exists
            temp_cursor.close()
            self.ingredients_foods_table = IngredientsFood(self.db)
        except Exception as e:
             raise RuntimeError(f"Failed to initialize IngredientsFood table for translator: {e}. Ensure table exists.") from e
        
        # Initialize the Ingredient Translator
        self.translator = IngredientTranslator(self.db, self.ingredients_foods_table)
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = "gpt-4o-mini" 
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, api_key=self.api_key)
        self.output_parser = PydanticOutputParser(pydantic_object=InventoryItems)
        self.format_instructions = self.output_parser.get_format_instructions()
        self.extraction_prompt_template = """\
Parse the following user input about inventory changes.
For each item mentioned, extract the following fields:
- operation: either 'add', 'delete', or 'update'
- name: a simplified item name (e.g., "Whole Milk" not "Great Value Whole Milk, Gallon")
- quantity: the quantity with units (e.g., '1 gallon')
- expiration: the expiration date in YYYY-MM-DD format, if specified
- item_id: for update or delete operations, the ID of the item to modify

Your main responsibility is to interpret natural language about inventory and determine the appropriate operations:

1.  **ADD vs UPDATE:**
    *   If the user clearly wants to **add** a new item, even if it's similar to an existing one (e.g., "add 80/20 ground beef" when "ground beef" exists), use the **'add'** operation. Only use 'update' if the user explicitly says "update", "change", or implies modifying an *existing* item's quantity/expiration.
    *   Do NOT assume an addition is an update just because the name is similar.

2.  **UPDATE Operations:**
    *   When processing an **'update'**, ONLY include the fields the user explicitly mentioned changing. 
    *   If the user only mentions updating the expiration date, do NOT include a quantity field in the output.
    *   If the user only mentions changing the quantity, do not include the expiration field.
    *   Identify the `item_id` of the specific item being updated.

3.  **Quantities:**
    *   If quantity is not specified for an **'add'** operation, use a sensible default like "1 unit" or "1 count".
    *   For **'update'** operations involving quantity changes, capture the quantity specified by the user. This quantity represents the *change* amount.
    *   IMPORTANT: Use NEGATIVE quantities when the user consumes, uses, or removes a specific amount (e.g., "used 2 eggs" → quantity: "-2", "drank a glass of milk" → quantity: "-1 glass").
    *   If the user says they finished/used up an item without specifying amount (e.g., "finished the cereal"), use a quantity like "-100%" or a very large negative number to indicate depletion.

4.  **DELETE Operations:**
    *   Use the **'delete'** operation ONLY when the user wants to remove an item *completely* without reference to quantity (e.g., "remove the cheese", "throw away expired milk"). Identify the `item_id`.
    *   If the user specifies a quantity to remove (e.g., "remove 3 apples"), use the **'update'** operation with a negative quantity instead.

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
                inventory_text += f"ID: {item['id']}, Name: {item['name']}, Quantity: {item['quantity']}, Expires: {item['expiration'] or 'N/A'}"
                # Also include the food ID if it exists
                food_id = item['ingredient_food_id'] if 'ingredient_food_id' in item.keys() and item['ingredient_food_id'] is not None else None
                if food_id is not None:
                     inventory_text += f", FoodID: {food_id}"
                inventory_text += "\n" # Add newline at the end
            
            return inventory_text.strip() # Strip trailing newline
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
        
        # Implement try-except for parsing robustness
        try:
            extracted_items = self.output_parser.parse(response.content)
            return extracted_items
        except Exception as e:
            print(f"[ERROR] Failed to parse inventory extractor output: {e}")
            # Return an empty list or raise a specific error
            return InventoryItems(items=[]) 
        
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
                    print(f"Processing ADD for: {item.name}")
                    # Step 1: Translate the ingredient name to get the food ID
                    matched, new = self.translator.translate_ingredients([[item.name, item.quantity]])
                    
                    ingredient_food_id = None
                    if len(matched) == 1 and len(new) == 0:
                        ingredient_food_id = matched[0][2] # Get ID from matched list
                        print(f"  -> Translated to existing Food ID: {ingredient_food_id}")
                    elif len(new) == 1 and len(matched) == 0:
                        ingredient_food_id = new[0][2] # Get ID from new list
                        print(f"  -> Translated to new Food ID: {ingredient_food_id}")
                    else:
                        # Handle ambiguity or failure
                        print(f"  [WARN] Translation for '{item.name}' yielded {len(matched)} matches and {len(new)} new items. Cannot reliably link Food ID. Adding without link.")
                        # Proceed without linking, or could skip/error

                    # Step 2: Check if an inventory item with this food ID already exists
                    existing_inventory_item_id = None
                    existing_item_details = None
                    update_instead_of_add = False

                    if ingredient_food_id is not None:
                        all_inventory_items = inventory.read() # Read current inventory
                        if all_inventory_items:
                            for inv_item in all_inventory_items:
                                inv_food_id = inv_item['ingredient_food_id'] if 'ingredient_food_id' in inv_item.keys() else None
                                if inv_food_id == ingredient_food_id:
                                    existing_inventory_item_id = inv_item['id']
                                    existing_item_details = inv_item
                                    update_instead_of_add = True
                                    print(f"  -> Found existing inventory item (ID: {existing_inventory_item_id}) with matching Food ID: {ingredient_food_id}. Will update instead of add.")
                                    break # Found first match

                    # Step 3: Perform either UPDATE or CREATE
                    if update_instead_of_add and existing_item_details is not None:
                        # --- Perform UPDATE --- 
                        print(f"  -> Updating inventory item ID: {existing_inventory_item_id}")
                        # Calculate new quantity
                        current_qty_num = self.extract_numeric_quantity(existing_item_details['quantity'])
                        # Use the quantity from the *item being added*
                        add_qty_str = item.quantity if item.quantity else "1" # Get quantity string or default
                        add_qty_num = self.extract_numeric_quantity(add_qty_str) 
                        
                        # Determine the unit - prioritize the unit from the item being added if it's specific
                        existing_unit = self.get_unit_from_quantity(existing_item_details['quantity'])
                        add_unit = self.get_unit_from_quantity(add_qty_str)
                        
                        # Use added unit if it's not the default 'units' (or empty), otherwise use existing
                        unit_to_use = add_unit if add_unit and add_unit != 'units' else existing_unit
                        if not unit_to_use: # Final fallback if both are empty/default
                            unit_to_use = 'units'
                            
                        print(f"  -> Units - Existing: '{existing_unit}', Added: '{add_unit}', Using: '{unit_to_use}'")
                        
                        new_qty_num = current_qty_num + add_qty_num
                        
                        # Format new quantity string
                        new_quantity_str = f"{new_qty_num:.2f} {unit_to_use}".strip() if isinstance(new_qty_num, float) and new_qty_num % 1 != 0 else f"{int(new_qty_num)} {unit_to_use}".strip()
                        
                        # Keep existing name, update expiration if provided in add request
                        name_to_use = existing_item_details['name']
                        expiration_to_use = item.expiration if item.expiration else existing_item_details['expiration']
                        
                        inventory.update(
                            item_id=existing_inventory_item_id, 
                            name=name_to_use, 
                            quantity=new_quantity_str, 
                            expiration=expiration_to_use, 
                            ingredient_food_id=ingredient_food_id # Keep the food ID link
                        )
                        change_msg = f"Updated existing: {name_to_use} | {existing_item_details['quantity']} → {new_quantity_str} | Expires: {expiration_to_use or 'N/A'} | FoodID: {ingredient_food_id}"
                        confirmation_messages.append(change_msg)
                        changes_made = True
                        items_processed += 1
                    
                    else:
                        # --- Perform CREATE (Original ADD logic) ---
                        print(f"  -> No existing inventory item found with Food ID {ingredient_food_id}. Creating new item.")
                        new_inventory_id = inventory.create(
                            item.name, 
                            item.quantity if item.quantity else "1 unit", # Use default if quantity missing
                            item.expiration, 
                            ingredient_food_id # Pass the determined ID
                        )
                        
                        if new_inventory_id is not None:
                            change_msg = f"Added: {item.name} | {item.quantity if item.quantity else '1 unit'} | Expires: {item.expiration or 'N/A'} | Linked Food ID: {ingredient_food_id or 'None'}"
                            confirmation_messages.append(change_msg)
                            changes_made = True
                            items_processed += 1
                        else:
                            print(f"  [ERROR] Failed to add inventory item '{item.name}' to DB.")
                
                elif item.operation.lower() == "delete":
                    target_item_id = item.item_id # Rely solely on the ID from the extractor
                    item_found_and_deleted = False

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
                        else:
                            # ID provided by LLM was invalid or item already deleted
                            print(f"[WARN] Item ID {target_item_id} provided for deletion not found in inventory.")
                        
                    if not item_found_and_deleted and target_item_id is None:
                         # LLM didn't provide an ID, and we have no fallback
                         print(f"[WARN] Could not delete item '{item.name}'. No item_id provided by extractor and name fallback is disabled.")

                
                elif item.operation.lower() == "update":
                    target_item_id = item.item_id # Rely solely on the ID from the extractor
                    item_found_and_updated = False
                    print(f"Processing UPDATE for: ID {item.item_id} / Name '{item.name}'")

                    if target_item_id is not None:
                        # Get current item to calculate new quantity if needed
                        current_result = inventory.read(target_item_id)
                        if current_result and current_result[0]:
                            current_item = current_result[0]
                            # Determine new name/expiration, defaulting to current if not provided in update
                            name = item.name if item.name and item.name != current_item['name'] else current_item['name']
                            current_expiration_str = current_item['expiration']
                            expiration = item.expiration if item.expiration else current_expiration_str
                            
                            # Determine the ingredient_food_id
                            ingredient_food_id = current_item['ingredient_food_id'] if 'ingredient_food_id' in current_item.keys() and current_item['ingredient_food_id'] is not None else None
                            if item.name and item.name != current_item['name']:
                                print(f"  -> Name changed from '{current_item['name']}' to '{item.name}'. Translating new name...")
                                matched, new = self.translator.translate_ingredients([[item.name, item.quantity]])
                                if len(matched) == 1 and len(new) == 0:
                                    ingredient_food_id = matched[0][2]
                                    print(f"    -> Translated new name to existing Food ID: {ingredient_food_id}")
                                elif len(new) == 1 and len(matched) == 0:
                                    ingredient_food_id = new[0][2]
                                    print(f"    -> Translated new name to new Food ID: {ingredient_food_id}")
                                else:
                                    print(f"    [WARN] Translation for new name '{item.name}' was ambiguous. Keeping original Food ID: {ingredient_food_id}")
                                    # Keep original food ID if translation unclear
                                    
                            # --- Quantity Update Logic (only if quantity is provided) ---
                            new_quantity = current_item['quantity'] # Default to current quantity
                            delete_item_after_update = False
                            if item.quantity is not None:
                                print(f"  -> Quantity update requested: {item.quantity}")
                                # Extract numeric quantities and units
                                current_qty_num = self.extract_numeric_quantity(current_item['quantity'])
                                update_qty_num = self.extract_numeric_quantity(item.quantity)
                                unit = self.get_unit_from_quantity(current_item['quantity']) or self.get_unit_from_quantity(item.quantity)
                                new_qty_num = current_qty_num + update_qty_num
                                
                                if new_qty_num <= 0:
                                    delete_item_after_update = True
                                    change_msg = f"Deleted: {name} | {current_item['quantity']} | Expires: {current_expiration_str or 'N/A'} (quantity became <= 0 after update: {item.quantity})"
                                else:
                                    # Format new quantity string
                                    new_quantity = f"{new_qty_num:.2f} {unit}".strip() if isinstance(new_qty_num, float) and new_qty_num % 1 != 0 else f"{int(new_qty_num)} {unit}".strip()
                                    change_msg = f"Updated: {name} | {current_item['quantity']} → {new_quantity} | Expires: {expiration or 'N/A'} | FoodID: {ingredient_food_id or 'None'}"
                            else:
                                # No quantity change requested, just update other fields
                                change_msg = f"Updated: {name} | Qty: {new_quantity} | Expires: {expiration or 'N/A'} | FoodID: {ingredient_food_id or 'None'}"
                            # --- End Quantity Update Logic ---
                            
                            if delete_item_after_update:
                                inventory.delete(target_item_id)
                                
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
            print(traceback.format_exc()) # Print detailed traceback
            return False, "An error occurred while processing inventory changes."
        # No disconnect needed here 

# Example Usage (for testing purposes)
if __name__ == "__main__":
    print("--- Running NaturalLanguageInventoryProcessor Standalone Test ---")
    
    # Need to set up DB connection and potentially reset inventory for a clean test
    # Resetting the whole DB might be too much, maybe just clear inventory?
    db_test = None
    try:
        from db.db_functions import init_tables # Import here for testing
        from debug.reset_db import ResetDB # Import ResetDB for test setup
        
        # Ensure a clean state for testing
        print("\nResetting database for test...")
        resetter = ResetDB()
        resetter.reload_all()
        if resetter.db and resetter.db.conn:
             resetter.db.disconnect() # Disconnect after reset
        print("✓ Database reset for test.")
        
        print("\nInitializing database connection for test...")
        db_test, tables_test = init_tables()
        if not db_test or not tables_test or "inventory" not in tables_test or "ingredients_foods" not in tables_test:
             raise ConnectionError("Failed to initialize database tables for testing.")
        inventory_table_test = tables_test["inventory"]
        print("✓ Database initialized for test.")

        # Instantiate the processor
        processor = NaturalLanguageInventoryProcessor(inventory_table_test, db_test)

        # --- Test Cases ---
        test_inputs = [
            "I bought 2 lbs of 80/20 Ground Beef", # ADD - should link to existing ID 104
            "also got Great Value Whole Milk", # ADD - should link to existing ID 102
            "add some fresh spinach", # ADD - should generalize and add new food, then link inventory
            "used half the ground beef", # UPDATE (negative quantity)
            "update the Whole Milk expiration to 2024-12-31", # UPDATE expiration only
            "Delete the instant ramen", # DELETE
            "Need to add Walnuts, 1 bag" # ADD - new item, should generalize, add food, link inventory
        ]
        
        print("\nCurrent Inventory before tests:")
        print(processor.get_current_inventory_text())
        print("-" * 20)

        for i, user_input in enumerate(test_inputs):
            print(f"\n>>> Test {i+1}: Processing input: '{user_input}'")
            changes_made, confirmation = processor.process_inventory_changes(user_input)
            print(f"Changes Made: {changes_made}")
            print(f"Confirmation:\n{confirmation}")
            print("-" * 20)
            
        print("\nCurrent Inventory after tests:")
        print(processor.get_current_inventory_text())

    except Exception as e:
        print(f"\n--- Test Failed ---")
        print(f"An error occurred during the standalone test: {e}")
        traceback.print_exc()
    finally:
        # Cleanup database connection used for the test
        if db_test and db_test.conn:
            print("\nDisconnecting test database.")
            db_test.disconnect()
            
    print("\n--- Standalone Test Finished ---")