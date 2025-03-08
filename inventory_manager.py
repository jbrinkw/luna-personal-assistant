#!/usr/bin/env python
import config
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from db_functions import run_query, create_table

# Define models for extraction
class InventoryChange(BaseModel):
    operation: str = Field(..., description="CRUD operation: add, remove, or update")
    name: str = Field(..., description="Simplified item name")
    expiration_date: Optional[str] = Field(
        None, description="Expiration date in YYYY-MM-DD format (guessed if missing and item expires within a month)"
    )
    quantity: int = Field(..., description="Quantity change to be made")

class InventoryChangesData(BaseModel):
    changes: List[InventoryChange] = Field(
        ..., description="List of inventory changes to be applied"
    )

# Extractor class for inventory CRUD
class InventoryCRUDExtractor:
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.llm_model = "gpt-4o-mini"
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, openai_api_key=self.api_key)
        self.output_parser = PydanticOutputParser(pydantic_object=InventoryChangesData)
        self.format_instructions = self.output_parser.get_format_instructions()
        self.extraction_prompt_template = """\
Analyze the following user input and determine the inventory changes to be made.
For each change, output the following fields:
- operation: one of add, remove, update.
- name: a simplified item name.
- expiration_date: the expiration date in YYYY-MM-DD format. If an item is likely to expire within a month and no date is provided, guess an expiration date.
- quantity: the quantity to change.
Additionally, check the Existing Inventory (provided below) to decide:
- For items without an expiration date, if a similar item already exists (based on a case-insensitive match ignoring articles), increment its quantity rather than creating a new entry.
Return the results as a JSON object following this schema:
{format_instructions}

User Input: {user_input}

Existing Inventory: {existing_inventory}
"""
    def extract_changes(self, user_input: str, existing_inventory: str) -> InventoryChangesData:
        prompt = ChatPromptTemplate.from_template(template=self.extraction_prompt_template)
        messages = prompt.format_messages(
            user_input=user_input,
            format_instructions=self.format_instructions,
            existing_inventory=existing_inventory
        )
        response = self.chat.invoke(messages)
        parsed_output = self.output_parser.parse(response.content)
        return InventoryChangesData.parse_obj(parsed_output)

def update_inventory_in_db(user_input: str, existing_inventory: str):
    extractor = InventoryCRUDExtractor()
    changes_data = extractor.extract_changes(user_input, existing_inventory)
    
    if not changes_data.changes:
        print("No inventory changes extracted from the input.")
        return
    
    # Ensure the inventory table exists.
    create_table("""
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            quantity INT NOT NULL,
            expiration DATE
        )
    """)
    
    for change in changes_data.changes:
        if change.operation.lower() == "add":
            # For items with no expiration, check if an entry already exists.
            if change.expiration_date is None:
                query = "SELECT id, quantity FROM inventory WHERE LOWER(name) = LOWER(%s) AND expiration IS NULL"
                result = run_query(query, (change.name,))
                if result:
                    item_id, current_quantity = result[0]
                    new_quantity = current_quantity + change.quantity
                    query = "UPDATE inventory SET quantity=%s WHERE id=%s"
                    run_query(query, (new_quantity, item_id), commit=True)
                    continue
            # Insert new entry.
            query = "INSERT INTO inventory (name, quantity, expiration) VALUES (%s, %s, %s)"
            run_query(query, (change.name, change.quantity, change.expiration_date), commit=True)
        elif change.operation.lower() == "remove":
            # Remove specified quantity from matching items.
            query = "SELECT id, quantity FROM inventory WHERE LOWER(name) = LOWER(%s)"
            results = run_query(query, (change.name,))
            total_removed = 0
            if results:
                for item_id, current_quantity in results:
                    if total_removed < change.quantity:
                        remove_qty = min(change.quantity - total_removed, current_quantity)
                        new_quantity = current_quantity - remove_qty
                        if new_quantity == 0:
                            query = "DELETE FROM inventory WHERE id=%s"
                            run_query(query, (item_id,), commit=True)
                        else:
                            query = "UPDATE inventory SET quantity=%s WHERE id=%s"
                            run_query(query, (new_quantity, item_id), commit=True)
                        total_removed += remove_qty
        elif change.operation.lower() == "update":
            query = ("UPDATE inventory SET quantity=%s WHERE LOWER(name) = LOWER(%s) "
                     "AND (expiration = %s OR (expiration IS NULL AND %s IS NULL))")
            run_query(query, (change.quantity, change.name, change.expiration_date, change.expiration_date), commit=True)
    
    print("Inventory updated successfully:")
    for change in changes_data.changes:
        print(f"- {change.operation} | {change.name} | {change.expiration_date} | {change.quantity}")

# Example usage for testing:
if __name__ == "__main__":
    # Clear the inventory
    run_query("DELETE FROM inventory", commit=True)
    
    # Add new items to the inventory
    test_input = (
        "Add Spaghetti, ground beef, non-chunky tomato sauce, parmesan, pasta, store-bought Alfredo sauce, "
        "pre-cooked chicken, thin-sliced steak, white rice, black beans, extra cheese, mayo-toasted tortilla, "
        "pre-cooked pulled pork, BBQ sauce, instant mashed potatoes, rice."
    )
    existing_inventory = ""  # Inventory is cleared, so it's empty.
    update_inventory_in_db(test_input, existing_inventory)
