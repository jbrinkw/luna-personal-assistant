import sys
import os
import json
import traceback
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from dotenv import load_dotenv

# Add project root to sys.path if needed, assuming it might be run directly
# Or rely on the calling script having the path configured
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import project-specific database functions
try:
    # Assuming db_functions.py is in a 'db' directory at the project root
    from db.db_functions import Database, IngredientsFood 
except ImportError:
    print("Error: Could not import Database or IngredientsFood from db.db_functions.")
    print("Ensure the script is run in an environment where 'db' module is accessible.")
    sys.exit(1)

# Load environment variables (needed for API key)
load_dotenv()

# --- Pydantic Model for LLM Output ---
class GeneralizedIngredient(BaseModel):
    generalized_name: str = Field(..., description="The generalized, common name for the ingredient")

class IngredientTranslator:
    def __init__(self, db: Database, ingredients_foods_table: IngredientsFood):
        """
        Initializes the IngredientTranslator.

        Args:
            db: An active Database connection object.
            ingredients_foods_table: An initialized IngredientsFood table object.
        """
        self.db = db
        self.ingredients_foods_table = ingredients_foods_table
        
        # --- LLM Setup ---
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Error: OPENAI_API_KEY not found in environment variables.")
            
        self.llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", api_key=self.api_key)
        self.generalization_parser = PydanticOutputParser(pydantic_object=GeneralizedIngredient)
        self.generalization_format_instructions = self.generalization_parser.get_format_instructions()
        self.generalization_prompt_template = ChatPromptTemplate.from_template("""
Given the specific ingredient name provided by a user, provide a concise, generalized, common name for it. 
Focus on the core food item, removing brand names, sizes, packaging details, and minor descriptors unless essential (e.g., 'smoked paprika' vs 'paprika').

Examples:
- Input: "Great Value Whole Vitamin D Milk, Gallon, Plastic, Jug, 128 Fl Oz" -> Output: "Whole Milk"
- Input: "Oscar Mayer Naturally Hardwood Smoked Bacon, 16 oz." -> Output: "Bacon"
- Input: "Organic Baby Spinach, 5 oz Clamshell" -> Output: "Spinach"
- Input: "McCormick Ground Cumin, 1.5 oz" -> Output: "Cumin"
- Input: "Fresh Garlic Clove" -> Output: "Garlic"
- Input: "Kikkoman Soy sauce" -> Output: "Soy Sauce"
- Input: "Barilla Spaghetti Pasta, 16 oz" -> Output: "Spaghetti"
- Input: "Extra Sharp Cheddar Cheese block" -> Output: "Extra Sharp Cheddar Cheese"

{format_instructions}

Specific Ingredient Name: {specific_name}
""")
        print("[OK] IngredientTranslator initialized.")

    def _find_ingredient_match(self, input_name: str) -> Optional[int]:
        """Internal method to find a matching ingredient ID in the database."""
        try:
            all_foods = self.ingredients_foods_table.read()
            if not all_foods:
                return None

            input_lower = input_name.lower()

            # 1. Exact case-insensitive match
            for food in all_foods:
                # Ensure we access by key, as db functions return Row objects (dict-like)
                if food['name'].lower() == input_lower:
                    print(f"  [Match] Exact match found for '{input_name}': ID {food['id']} ({food['name']})")
                    return food['id']

            # 2. Substring match (prioritize shorter DB names)
            potential_matches = []
            for food in all_foods:
                db_name_lower = food['name'].lower()
                # Check containment both ways
                if db_name_lower in input_lower or input_lower in db_name_lower:
                    potential_matches.append(food)
            
            if potential_matches:
                potential_matches.sort(key=lambda x: len(x['name']))
                best_match = potential_matches[0]
                print(f"  [Match] Substring match found for '{input_name}': ID {best_match['id']} ({best_match['name']})")
                return best_match['id']

            # 3. No match found
            # print(f"  [No Match] No match found for '{input_name}'") # Keep console cleaner
            return None

        except Exception as e:
            print(f"  [Error] Error during matching for '{input_name}': {e}")
            traceback.print_exc()
            return None

    def _generalize_ingredient_name(self, specific_name: str) -> Optional[str]:
        """Internal method uses LLM to generalize the ingredient name."""
        print(f"    Attempting generalization for: '{specific_name}'")
        try:
            messages = self.generalization_prompt_template.format_messages(
                specific_name=specific_name,
                format_instructions=self.generalization_format_instructions
            )
            response = self.llm.invoke(messages)
            parsed_response = self.generalization_parser.parse(response.content)
            generalized = parsed_response.generalized_name.strip()
            
            if not generalized or generalized.lower() == "ingredient name": 
                print(f"    [WARN] LLM returned empty/placeholder generalization for '{specific_name}'")
                return None
                
            print(f"    LLM suggested generalization: '{generalized}'")
            return generalized
        except Exception as e:
            print(f"    [Error] LLM generalization failed for '{specific_name}': {e}")
            traceback.print_exc()
            return None

    def translate_ingredients(self, ingredients: List[List[str]]) -> Tuple[List[List[Any]], List[List[Any]]]:
        """
        Processes a list of ingredients, matching existing ones and generalizing/adding new ones.

        Args:
            ingredients: A list of lists, where each inner list is [name(str), quantity(str)].

        Returns:
            A tuple containing two lists:
            - matched_ingredients: [[name, quantity, matched_id], ...]
            - new_ingredients: [[name, quantity, new_id], ...]
        """
        matched_ingredients = []
        new_ingredients = []

        print(f"--- Translating {len(ingredients)} Ingredients ---")
        for i, item in enumerate(ingredients):
            if len(item) != 2:
                print(f"  [WARN] Skipping invalid ingredient item at index {i}: {item}. Expected [name, quantity].")
                continue
                
            ingredient_name, quantity = item
            print(f"Processing ({i+1}/{len(ingredients)}): {ingredient_name}")
            
            matched_id = self._find_ingredient_match(ingredient_name)
            
            if matched_id is not None:
                matched_ingredients.append([ingredient_name, quantity, matched_id])
            else:
                print(f"    -> No initial match. Needs generalization.")
                generalized_name = self._generalize_ingredient_name(ingredient_name)

                if generalized_name:
                    # Check if the *generalized* name now matches
                    generalized_match_id = self._find_ingredient_match(generalized_name)
                    
                    if generalized_match_id is not None:
                        print(f"    Generalized name '{generalized_name}' matched existing ID: {generalized_match_id}. Adding to matched list.")
                        matched_ingredients.append([ingredient_name, quantity, generalized_match_id])
                    else:
                        # Generalized name is not in DB, add it
                        print(f"    Generalized name '{generalized_name}' not found in DB. Adding...")
                        try:
                            # Use the ingredients_foods_table object passed during init
                            new_id = self.ingredients_foods_table.create(
                                name=generalized_name,
                                min_amount_to_buy=1, # Default value
                                walmart_link=""      # Default value
                            )
                            if new_id is not None:
                                print(f"    ✓ Successfully added '{generalized_name}' with new ID: {new_id}")
                                new_ingredients.append([ingredient_name, quantity, new_id])
                            else:
                                # create() returns the ID (int) or None/raises error
                                print(f"    ✗ Failed to add generalized ingredient '{generalized_name}' to DB (create returned None).")
                        except Exception as e:
                            print(f"    ✗ Error adding generalized ingredient '{generalized_name}' to DB: {e}")
                            traceback.print_exc()
                else:
                    print(f"    Skipping add for '{ingredient_name}' due to generalization failure.")

        print("--- Translation Finished ---")
        return matched_ingredients, new_ingredients

# Example Usage (for testing purposes)
if __name__ == "__main__":
    print("--- Running IngredientTranslator Standalone Test ---")
    
    # Need to set up DB and potentially reset for a clean test
    try:
        from debug.reset_db import ResetDB # Import here for testing only
        from db.db_functions import init_tables
        
        print("\nResetting ingredients_foods table for test...")
        resetter = ResetDB()
        resetter.reload_ingredients_foods()
        if resetter.db and resetter.db.conn:
            resetter.db.disconnect() # Disconnect resetter's connection
        print("✓ ingredients_foods table reset.")

        print("\nInitializing database connection for test...")
        db_test, tables_test = init_tables()
        if not db_test or not tables_test or "ingredients_foods" not in tables_test:
             raise ConnectionError("Failed to initialize database for testing.")
        ingredients_table_test = tables_test["ingredients_foods"]
        print("✓ Database initialized for test.")

        # Instantiate the translator
        translator = IngredientTranslator(db_test, ingredients_table_test)

        # Sample data from pig2.py
        sample_ingredients_test = [
            ["Ground beef 80/20", "1 lb"], 
            ["Oscar Mayer Thick Cut Bacon", "12 oz"], 
            ["Organic Baby Spinach", "5 oz"], 
            ["Sesame seeds", "1 tbsp"], 
            ["Kikkoman Soy sauce", "1/4 cup"], 
            ["Fresh Garlic Clove", "2 cloves"], 
            ["Whole Ginger Root", "1 inch"], 
            ["Fairlife chocolate milk", "1 bottle"], 
            ["Great Value Whole Vitamin D Milk, Gallon", "1 gallon"] 
        ]
        print(f"\nTest Input Ingredients ({len(sample_ingredients_test)}):")
        for item in sample_ingredients_test:
             print(f"- {item[0]} ({item[1]})")

        # Run the translation
        matched, new = translator.translate_ingredients(sample_ingredients_test)

        # Print results
        print("\n--- Test Results ---")
        print("\nMatched Ingredients:")
        if matched:
            for name, qty, id_val in matched:
                print(f"- {name} ({qty}) -> ID: {id_val}")
        else:
            print("  None")
            
        print("\nNew Ingredients (Generalized & Added):")
        if new:
            for name, qty, id_val in new:
                 print(f"- {name} ({qty}) -> Generalized & Added as ID: {id_val}")
        else:
            print("  None")

    except Exception as e:
        print(f"\n--- Test Failed ---")
        print(f"An error occurred during the standalone test: {e}")
        traceback.print_exc()
    finally:
        # Cleanup database connection used for the test
        if 'db_test' in locals() and db_test and db_test.conn:
            print("\nDisconnecting test database.")
            db_test.disconnect()
            
    print("\n--- Standalone Test Finished ---")
