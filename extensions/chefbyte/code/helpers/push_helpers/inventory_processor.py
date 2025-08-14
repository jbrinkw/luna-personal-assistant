"""
This module handles inventory changes processing from natural language inputs.
"""

import os
import re
import sys
import traceback
from typing import List, Optional, Tuple, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from datetime import datetime, date, timedelta

from db.db_functions import Database, Inventory, IngredientsFood
from helpers.ingredient_translator import IngredientTranslator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Add project root to sys.path ---
project_root = os.getcwd()
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End sys.path modification ---
print(f"DEBUG: sys.path after modification: {sys.path}")

# --- NEW Pydantic Models ---
class InventoryUpdateOperation(BaseModel):
    name: str = Field(..., description="The generalized name of the food item mentioned (e.g., 'Milk', 'Ground Beef')")
    operation_type: Literal['A', 'E'] = Field(..., description="Type of operation: 'A' for Add/Subtract quantity, 'E' for Expiration date update")
    value: str = Field(..., description="The value for the operation. For 'A', include sign and units (e.g., '+1 gallon', '-2', '-50g'). For 'E', use 'YYYY-MM-DD' format.")

class InventoryUpdateList(BaseModel):
    operations: List[InventoryUpdateOperation] = Field(..., description="List of inventory update operations to perform")
# --- End NEW Pydantic Models ---


class NaturalLanguageInventoryProcessor:
    def __init__(self, inventory_table: Inventory, db: Database):
        """Initialize processor with shared Inventory table object and DB connection."""
        self.inventory_table = inventory_table
        self.db = db

        try:
            if not self.db.conn:
                self.db.connect()
            if not self.db.conn:
                raise ConnectionError("Database connection failed before checking ingredients_foods")

            temp_cursor = self.db.conn.cursor()
            temp_cursor.execute("SELECT 1 FROM ingredients_foods LIMIT 1")
            temp_cursor.close()
            self.ingredients_foods_table = IngredientsFood(self.db)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize IngredientsFood table for translator: {e}. Ensure table exists.") from e

        self.translator = IngredientTranslator(self.db, self.ingredients_foods_table)

        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = "gpt-4o-mini"
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, api_key=self.api_key)
        
        # --- Update Output Parser ---
        self.output_parser = PydanticOutputParser(pydantic_object=InventoryUpdateList)
        # --- End Update ---
        
        self.format_instructions = self.output_parser.get_format_instructions()
        
        # --- Updated Extraction Prompt ---
        self.extraction_prompt_template = """\
Parse the user input about inventory changes. Your goal is to identify items and the specific modification requested for each.

Focus ONLY on quantity changes and expiration date changes. Do NOT infer other operations like 'delete'.

For each item mentioned, determine:
1.  `name`: The generalized name of the food item (e.g., "Milk" not "Great Value Whole Milk", "Ground Beef" not "80/20 Ground Beef").
2.  `operation_type`:
    *   'A' if the user is adding, removing, or using a quantity of the item.
    *   'E' if the user is setting or changing the expiration date.
3.  `value`:
    *   For 'A': The quantity change, INCLUDING the sign (+ or -) and units if specified (e.g., "+1 gallon", "-2", "-50g"). If no quantity is mentioned for an addition (e.g., "add milk"), use "+1 unit". If a user says they "finished" or "used up" an item, use a value like "-100%".
    *   For 'E': The expiration date in "YYYY-MM-DD" format. If the user says "tomorrow", "next week", etc., calculate the actual date. Today is {current_date}.

Examples:
- "add milk" -> name: "Milk", operation_type: "A", value: "+1 unit"
- "I bought 2 lbs of ground beef" -> name: "Ground Beef", operation_type: "A", value: "+2 lbs"
- "used 3 eggs" -> name: "Eggs", operation_type: "A", value: "-3"
- "set the milk expiration date to tomorrow" -> name: "Milk", operation_type: "E", value: "{tomorrow_date}"
- "remove the cheese" -> name: "Cheese", operation_type: "A", value: "-100%"
- "i finished the cereal" -> name: "Cereal", operation_type: "A", value: "-100%"
- "add apples and set their expiration to next friday" -> [{{ "name": "Apples", "operation_type": "A", "value": "+1 unit"}}, {{ "name": "Apples", "operation_type": "E", "value": "{next_friday_date}"}}]

Current Inventory (for context only, do not modify based on this, just use it to understand names):
{current_inventory}

Return the results as a JSON object following this schema:
{format_instructions}

User Input: {user_input}
"""
        # --- End Updated Extraction Prompt ---

    def get_current_inventory_text(self):
        """Get the current inventory using the shared inventory table object."""
        try:
            current_items = self.inventory_table.read()
            if not current_items:
                return "The inventory is currently empty."
            
            inventory_text = ""
            for item in current_items:
                inventory_text += f"ID: {item['id']}, Name: {item['name']}, Quantity: {item['quantity']}, Expires: {item['expiration'] or 'N/A'}"
                food_id = item['ingredient_food_id'] if 'ingredient_food_id' in item.keys() and item['ingredient_food_id'] is not None else None
                if food_id is not None:
                     inventory_text += f", FoodID: {food_id}"
                inventory_text += "\n"
            
            return inventory_text.strip()
        except Exception as e:
            print(f"[ERROR] Failed to get current inventory text in processor: {e}")
            return "Error retrieving current inventory."


    def extract_operations(self, user_input: str, current_inventory: str) -> InventoryUpdateList:
        # --- Updated Extraction Method ---
        """Extracts inventory update operations using the new model and prompt."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        # Simple calculation for next Friday, more robust date parsing might be needed
        days_until_friday = (4 - today.weekday() + 7) % 7
        next_friday = today + timedelta(days=days_until_friday if days_until_friday > 0 else 7)

        prompt = ChatPromptTemplate.from_template(template=self.extraction_prompt_template)
        messages = prompt.format_messages(
            user_input=user_input,
            format_instructions=self.format_instructions,
            current_inventory=current_inventory,
            current_date=today.strftime('%Y-%m-%d'),
            tomorrow_date=tomorrow.strftime('%Y-%m-%d'),
            next_friday_date=next_friday.strftime('%Y-%m-%d')
        )
        response = self.chat.invoke(messages)
        try:
            extracted_operations = self.output_parser.parse(response.content)
            # print(f"[DEBUG] Extracted Operations: {extracted_operations}") # Debug print
            return extracted_operations
        except Exception as e:
            print(f"[ERROR] Failed to parse inventory update operations: {e}")
            print(f"LLM Raw Output:\n{response.content}") # Log raw output on error
            return InventoryUpdateList(operations=[])
        # --- End Updated Extraction Method ---

    def _parse_quantity_value(self, value_str: str) -> Tuple[Optional[float], Optional[str]]:
        # --- Updated Quantity Parsing Helper ---
        """Extracts numeric change and unit from value string like '+1 gallon' or '-2'."""
        if not isinstance(value_str, str):
            return None, None

        value_str = value_str.strip()
        
        # Handle percentage case first
        if value_str == "-100%":
            return -float('inf'), '%' # Use infinity to signify deletion

        # Find sign and numeric part (including decimals, fractions)
        match = re.match(r'([+-]?)(\d+(?:[./]\d+)?)', value_str)
        number = None
        unit = None

        if match:
            sign = match.group(1)
            amount_str = match.group(2)
            
            try:
                if '/' in amount_str:
                    num_part, denom_part = amount_str.split('/')
                    base_num = float(num_part) / float(denom_part)
                else:
                    base_num = float(amount_str)
                
                number = -base_num if sign == '-' else base_num

                # Extract unit part after the number
                unit_part = value_str[match.end():].strip()
                unit_match = re.match(r'^([a-zA-Z]+)', unit_part)
                if unit_match:
                    unit = unit_match.group(1).lower()
                    # Simple plural handling
                    if len(unit) > 1 and unit.endswith('s'):
                        unit = unit[:-1]
                elif unit_part: # Handle non-standard units like 'large'
                    unit = unit_part.lower()
                
            except ValueError:
                number = None # Parsing failed

        # Default unit if number was parsed but unit wasn't
        if number is not None and unit is None:
            unit = 'unit'
            
        # print(f"[DEBUG] Parsed Quantity: Input='{value_str}', Number={number}, Unit='{unit}'") # Debug print
        return number, unit
        # --- End Updated Quantity Parsing Helper ---

    def process_inventory_changes(self, user_input: str) -> Tuple[bool, str]:
        # --- REFACTORED ---
        """
        Process inventory changes based on operations extracted from natural language input.
        Operations are based on food_id. Handles implicit creation and deletion.
        """
        inventory = self.inventory_table
        changes_made = False
        confirmation_messages = []
        items_processed = 0

        try:
            current_inventory_text = self.get_current_inventory_text()
            update_list = self.extract_operations(user_input, current_inventory_text)

            if not update_list.operations:
                 return False, "No inventory operations were detected."

            for op in update_list.operations:
                print(f"Processing Operation: Name='{op.name}', Type='{op.operation_type}', Value='{op.value}'")
                
                # 1. Translate name to food_id
                # Use translate_ingredients which finds or creates the food item
                matched, new = self.translator.translate_ingredients([[op.name, ""]]) # Quantity doesn't matter here
                
                food_id = None
                linked_name = op.name # Default to original name if no link
                
                if matched:
                    food_id = matched[0][2]
                    # Fetch canonical name robustly
                    try:
                        food_info = self.ingredients_foods_table.read(food_id)
                        if food_info:
                            linked_name = food_info[0]['name'] 
                    except Exception as e:
                         print(f"[WARN] Could not fetch canonical name for FoodID {food_id}: {e}")
                    print(f"  -> Linked to existing FoodID: {food_id} ({linked_name})")
                elif new:
                    food_id = new[0][2]
                    try:
                        food_info = self.ingredients_foods_table.read(food_id)
                        if food_info:
                             linked_name = food_info[0]['name'] 
                    except Exception as e:
                         print(f"[WARN] Could not fetch canonical name for newly created FoodID {food_id}: {e}")
                    print(f"  -> Linked to NEW FoodID: {food_id} ({linked_name})")
                else:
                    print(f"  [WARN] Could not translate or create FoodID for '{op.name}'. Skipping operation.")
                    continue # Skip if no food_id link

                # 2. Find existing inventory item(s) for this food_id
                existing_inventory_items = []
                all_inventory = inventory.read() # Read current inventory state
                if all_inventory:
                    for inv_item_row in all_inventory:
                        # Ensure accessing by key
                        if 'ingredient_food_id' in inv_item_row.keys() and inv_item_row['ingredient_food_id'] == food_id:
                            existing_inventory_items.append(dict(inv_item_row)) # Convert Row to dict

                target_inventory_item = existing_inventory_items[0] if existing_inventory_items else None
                target_inventory_id = target_inventory_item['id'] if target_inventory_item else None

                print(f"  -> Found {len(existing_inventory_items)} existing inventory items for FoodID {food_id}. Targetting ID: {target_inventory_id}")

                # 3. Perform Operation
                if op.operation_type == 'E': # Expiration Update
                    if target_inventory_item:
                        try:
                            # Basic validation, db function might do more
                            datetime.strptime(op.value, '%Y-%m-%d') 
                            inventory.update(target_inventory_id, expiration=op.value)
                            changes_made = True
                            items_processed += 1
                            confirmation_messages.append(f"Updated expiration for {linked_name} (ID: {target_inventory_id}) to {op.value}.")
                            print(f"  -> Updated expiration for inventory ID {target_inventory_id}")
                        except ValueError:
                             print(f"  [WARN] Invalid date format '{op.value}' for expiration update. Skipping.")
                        except Exception as e:
                             print(f"  [ERROR] Failed to update expiration for inventory ID {target_inventory_id}: {e}")
                    else:
                        print(f"  [WARN] Cannot update expiration for non-existent item '{linked_name}' (FoodID: {food_id}). Skipping.")

                elif op.operation_type == 'A': # Quantity Add/Subtract
                    qty_change, unit_change = self._parse_quantity_value(op.value)
                    
                    if qty_change is None:
                         print(f"  [WARN] Could not parse quantity value '{op.value}' for '{linked_name}'. Skipping.")
                         continue

                    if target_inventory_item:
                        # --- Item Exists: Update or Delete ---
                        # Use _parse_quantity_value to handle parsing existing quantity robustly
                        current_qty_num, current_unit = self._parse_quantity_value("+" + target_inventory_item['quantity']) 

                        # Handle deletion case (-100% or quantity becomes <= 0 after addition)
                        # Need to check if current_qty_num was parsed successfully
                        should_delete = (qty_change == -float('inf')) or \
                                        (current_qty_num is not None and (current_qty_num + qty_change <= 0))

                        if should_delete:
                            try:
                                inventory.delete(target_inventory_id)
                                changes_made = True
                                items_processed += 1
                                confirmation_messages.append(f"Removed {linked_name} (ID: {target_inventory_id}) from inventory.")
                                print(f"  -> Deleted inventory ID {target_inventory_id}")
                            except Exception as e:
                                print(f"  [ERROR] Failed to delete inventory ID {target_inventory_id}: {e}")
                        else:
                            # Perform quantity update
                            if current_qty_num is None:
                                print(f"  [WARN] Could not parse current quantity '{target_inventory_item['quantity']}' for '{linked_name}'. Cannot perform addition. Setting quantity to the change value.")
                                new_qty_num = qty_change # Set to the change value directly
                                unit_to_use = unit_change if unit_change else 'unit'
                            else:
                                # Basic addition - assumes compatible units for now!
                                # TODO: Add unit conversion logic if necessary
                                unit_to_use = unit_change if unit_change else current_unit # Prioritize incoming unit? Or existing? Let's try incoming.
                                if not unit_to_use: unit_to_use = 'unit' # Fallback
                                
                                if current_unit and unit_change and current_unit != unit_change:
                                    print(f"  [WARN] Unit mismatch for '{linked_name}': Have '{current_unit}', adding '{unit_change}'. Performing simple addition - result unit will be '{unit_to_use}'.")
                                
                                new_qty_num = current_qty_num + qty_change
                                
                            # Format new quantity string
                            if new_qty_num % 1 == 0: # Integer
                                new_quantity_str = f"{int(new_qty_num)} {unit_to_use}".strip()
                            else: # Float
                                new_quantity_str = f"{new_qty_num:.2f} {unit_to_use}".strip()

                            try:
                                inventory.update(target_inventory_id, quantity=new_quantity_str)
                                changes_made = True
                                items_processed += 1
                                confirmation_messages.append(f"Updated quantity for {linked_name} (ID: {target_inventory_id}): {target_inventory_item['quantity']} -> {new_quantity_str}.")
                                print(f"  -> Updated quantity for inventory ID {target_inventory_id} to '{new_quantity_str}'")
                            except Exception as e:
                                print(f"  [ERROR] Failed to update quantity for inventory ID {target_inventory_id}: {e}")

                    else:
                        # --- Item Doesn't Exist: Create ---
                        if qty_change > 0:
                            # Format quantity string for creation
                            unit_to_use = unit_change if unit_change else 'unit'
                            if qty_change % 1 == 0:
                                create_quantity_str = f"{int(qty_change)} {unit_to_use}".strip()
                            else:
                                create_quantity_str = f"{qty_change:.2f} {unit_to_use}".strip()
                                
                            try:
                                new_inv_id = inventory.create(
                                    name=linked_name, # Use canonical name from translator
                                    quantity=create_quantity_str,
                                    expiration=None, # Expiration handled separately
                                    ingredient_food_id=food_id
                                )
                                if new_inv_id is not None:
                                    changes_made = True
                                    items_processed += 1
                                    confirmation_messages.append(f"Added new item: {linked_name} (Qty: {create_quantity_str}) linked to FoodID {food_id}.")
                                    print(f"  -> Created new inventory item ID {new_inv_id} for FoodID {food_id}")
                                else:
                                    print(f"  [ERROR] Failed to create new inventory item for '{linked_name}'.")
                            except Exception as e:
                                print(f"  [ERROR] Failed to create new inventory item for '{linked_name}': {e}")
                        else:
                            # Trying to subtract from or delete a non-existent item
                            print(f"  [WARN] Cannot subtract/delete quantity for non-existent item '{linked_name}' (FoodID: {food_id}). Skipping.")

            # Construct final confirmation message
            if items_processed > 0:
                final_confirmation = f"INVENTORY UPDATE CONFIRMATION ({items_processed} operation(s))\n-------------------------------------\n" + "\n".join(confirmation_messages)
            else:
                final_confirmation = "No inventory changes were applied based on your request."

            return changes_made, final_confirmation

        except Exception as e:
            print(f"[ERROR] Error processing inventory changes: {e}")
            print(traceback.format_exc())
            return False, "An error occurred while processing inventory changes."
        # --- END REFACTORED ---

# Example Usage (for testing purposes)
if __name__ == "__main__":
    print("--- Running NaturalLanguageInventoryProcessor Standalone Test ---")
    db_test = None
    try:
        from db.db_functions import init_tables
        from debug.reset_db import ResetDB

        print("\nResetting database for test...")
        resetter = ResetDB()
        resetter.reload_all()
        if resetter.db and resetter.db.conn:
             resetter.db.disconnect()
        print("✓ Database reset for test.")

        print("\nInitializing database connection for test...")
        db_test, tables_test = init_tables()
        if not db_test or not tables_test or "inventory" not in tables_test or "ingredients_foods" not in tables_test:
             raise ConnectionError("Failed to initialize database tables for testing.")
        inventory_table_test = tables_test["inventory"]
        print("✓ Database initialized for test.")

        processor = NaturalLanguageInventoryProcessor(inventory_table_test, db_test)

        # --- NEW Test Cases ---
        test_inputs = [
            "add 1 gallon of whole milk", # Should find ID 102, CREATE item with 1 gallon
            "add milk",                   # Should find ID 102, UPDATE item, add 1 unit (total should be ~ 1 gallon + 1 unit)
            "use 2 eggs",                 # Should find ID 117, UPDATE item, subtract 2 (1 dozen -> 10 unit)
            "set expiration for eggs to 2025-12-31", # Should find ID 117, UPDATE expiration
            "remove the bacon",           # Should find ID 105, find item, DELETE item
            "add 500g ground beef",       # Should find ID 104, UPDATE item, add 500g (have 1 lb -> 1 lb + 500g - unit mismatch!)
            "add fresh bananas",          # Should generalize, create new food ID, CREATE inventory item +1 unit
            "set banana expiration date tomorrow", # Should find new banana ID, UPDATE item expiration
            "i finished the spinach",     # Should find/create spinach ID, find item?, DELETE item
            "i need to buy butter"        # Should NOT result in any operation
        ]

        print("\nInitial Inventory:")
        print(processor.get_current_inventory_text())
        print("-" * 30)

        for i, user_input in enumerate(test_inputs):
            print(f"\n>>> Test {i+1}: Processing input: '{user_input}'")
            changes_made, confirmation = processor.process_inventory_changes(user_input)
            print(f"Changes Made: {changes_made}")
            print(f"Confirmation:\n{confirmation}")
            print("-" * 30)
            print("\nCurrent Inventory:")
            print(processor.get_current_inventory_text()) # Show inventory after each step
            print("-" * 30)


    except Exception as e:
        print(f"\n--- Test Failed ---")
        print(f"An error occurred during the standalone test: {e}")
        traceback.print_exc()
    finally:
        if db_test and db_test.conn:
            print("\nDisconnecting test database.")
            db_test.disconnect()

    print("\n--- Standalone Test Finished ---")