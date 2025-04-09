# debug/test_new_meal_ideation_save.py
import sys
import os
import json
import traceback
from typing import List

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.db_functions import init_tables, Database, NewMealIdeas
from tools.new_meal_ideation import MealIdeationEngine # Import the engine
from debug.reset_db import ResetDB # For resetting DB state

# --- Mock LLM Responses ---
# Simulate Layer 1 response (descriptions)
MOCK_LAYER_1_RESPONSE = """
Okay, here are some meal ideas based on your preferences:

MEAL #1: Spicy Chicken Stir-fry
Description: A quick stir-fry with chicken, veggies, and a spicy sauce.

MEAL #2: Cheesy Baked Pasta
Description: A comforting pasta bake with lots of cheese and a simple tomato sauce.

MEAL #3: Lemon Herb Roasted Salmon
Description: Simple roasted salmon fillet with lemon and herbs, served with rice.

Would you like to:
1. Generate more meal ideas
2. Build out the full recipes for any of these options
"""

# Simulate Layer 2 response (recipes) - using format expected by new parser
MOCK_LAYER_2_RESPONSE = """
Here are the recipes for the selected meals:

RECIPE #1: Spicy Chicken Stir-fry
Recipe: 1. Cut chicken into bite-sized pieces. 2. Heat oil in a wok or large skillet. 3. Add chicken and cook until browned. 4. Add vegetables and stir-fry for 3-4 minutes. 5. Whisk together soy sauce, sriracha, ginger, and garlic. Pour over stir-fry. 6. Cook for 1-2 minutes until sauce thickens. 7. Serve over rice.
Ingredients: Chicken breast (1 lb), Broccoli florets (1 cup), Red bell pepper (1 sliced), Soy sauce (1/4 cup), Sriracha (1 tbsp), Fresh Ginger (1 tsp minced), Garlic cloves (2 minced), Sesame oil (1 tbsp), Cooked white rice (for serving)
Prep Time: 25 minutes

RECIPE #3: Lemon Herb Roasted Salmon
Recipe: 1. Preheat oven to 400°F (200°C). 2. Place salmon fillet on a baking sheet lined with parchment paper. 3. Drizzle with olive oil, lemon juice, salt, pepper, and dried herbs (like dill or parsley). 4. Roast for 12-15 minutes, or until cooked through. 5. Serve immediately with rice.
Ingredients: Salmon fillet (1 lb), Olive oil (1 tbsp), Lemon (1 juiced), Salt (to taste), Black pepper (to taste), Dried parsley (1 tsp), Cooked white rice (for serving)
Prep Time: 20 minutes

Would you like to:
1. Make adjustments to any recipe
2. Save these recipes to their collection
"""

# --- Test Functions ---

def run_test_pipeline(db: Database, tables: dict):
    """Simulates the Layer 1 -> Layer 2 -> Layer 3 pipeline."""
    engine = MealIdeationEngine(db, tables)

    print("\n--- Simulating Layer 1 (Generating Descriptions) ---")
    # We don't actually need to call the LLM, just parse the mock response
    parsed_descriptions = engine._parse_meal_descriptions(MOCK_LAYER_1_RESPONSE)
    if not parsed_descriptions or len(parsed_descriptions) != 3:
        print("[FAIL] Layer 1 Parsing failed.")
        return
    print(f"[OK] Layer 1 Parsed Descriptions: {parsed_descriptions}")
    # Manually set the engine's state
    engine.current_meal_descriptions = parsed_descriptions

    print("\n--- Simulating Layer 2 (Generating Recipes for #1 and #3) ---")
    # Again, just parse the mock Layer 2 response
    parsed_recipes = engine._parse_recipes(MOCK_LAYER_2_RESPONSE)
    if not parsed_recipes or len(parsed_recipes) != 2:
         print("[FAIL] Layer 2 Parsing or Translation failed significantly.")
         # Check if *any* recipes were parsed even if not all
         if parsed_recipes:
              print(f"  -> Only {len(parsed_recipes)} recipe(s) parsed successfully.")
         else:
              print("  -> No recipes parsed successfully.")
         # Decide whether to continue or stop the test
         # For now, let's stop if parsing is completely broken
         return
         
    print(f"[OK] Layer 2 Parsed & Translated Recipes: {parsed_recipes}")
    # Manually set engine state (important: needs to reflect *which* recipes were generated)
    # Assuming _parse_recipes correctly stores the generated recipes
    engine.current_recipes = parsed_recipes 
    # We need to know which *original* numbers these correspond to for saving
    selected_for_layer_2 = [1, 3] 

    print("\n--- Simulating Layer 3 (Saving Recipes #1 and #3) ---")
    # Use the indices corresponding to the selection [1, 3]
    # In this test, parsed_recipes[0] corresponds to #1, parsed_recipes[1] to #3
    # The save_recipes function expects the *original* numbers [1, 3] if it needs mapping,
    # but our current implementation relies on the state `self.current_recipes`
    # directly. Let's assume selected_items refers to the items *to be saved* from the
    # `current_recipes` state. For this test, we want to save both parsed recipes.
    # So we pass the indices/numbers relative to the *generated* recipes.
    # **Correction:** The router passes the originally selected numbers. `save_recipes`
    # needs to handle this mapping if `current_recipes` doesn't include all initially selected.
    # Let's test saving the recipes currently in `engine.current_recipes` by assuming
    # the user confirmed saving *these specific ones*.
    # A more robust test would mock the router determining selected_items=[1, 3] for Layer 3.
    
    # Let's save the recipes that were successfully parsed in the previous step.
    # We need indices relative to `engine.current_recipes`. Since both were parsed, save 1 and 2.
    items_to_save_indices = [1, 2] # Indices within engine.current_recipes

    # Call save_recipes - modify if it expects original numbers vs indices
    # Current save_recipes iterates through self.current_recipes, so selection list might be simpler?
    # Let's try passing the *original* numbers [1, 3] and see if save_recipes handles it.
    # **Revisiting save_recipes:** It iterates `self.current_recipes`. `selected_items` isn't
    # strictly used to *index* `self.current_recipes` in the current code, just checked for emptiness.
    # This is slightly flawed logic in the original `save_recipes`.
    # Let's proceed assuming we want to save *all* recipes currently held in `engine.current_recipes`.
    # We can achieve this by passing a non-empty list to `save_recipes`.
    
    success, confirmation = engine.save_recipes(selected_items=selected_for_layer_2) # Pass original selection

    print(f"\nSave Success: {success}")
    print(f"Save Confirmation:\n{confirmation}")

    # Verify database content
    print("\n--- Verifying Database Content ---")
    new_ideas_table = tables["new_meal_ideas"]
    all_ideas = new_ideas_table.read()

    found_stir_fry = False
    found_salmon = False
    if all_ideas:
        print(f"Found {len(all_ideas)} entries in new_meal_ideas:")
        for idea in all_ideas:
            idea_id = idea['id']
            name = idea['name']
            prep_time = idea['prep_time']
            ingredients_json = idea['ingredients']
            recipe_text = idea['recipe']
            
            print(f"\n  ID: {idea_id}")
            print(f"  Name: {name}")
            print(f"  Prep Time: {prep_time}")
            print(f"  Recipe: {recipe_text[:100]}...") # Show snippet
            
            try:
                ingredients = json.loads(ingredients_json)
                print("  Ingredients (Parsed JSON):")
                if isinstance(ingredients, list):
                     # Check if ingredients are in the new format [id, name, amount]
                    is_new_format = all(isinstance(ing, list) and len(ing) == 3 for ing in ingredients)
                    print(f"    Format: {'[id, name, amount]' if is_new_format else 'Unknown/Old'}")
                    for ing in ingredients[:3]: # Show first few
                        print(f"      - {ing}")
                    if len(ingredients) > 3:
                         print("      ...")
                         
                    # Verification checks
                    if name == "Spicy Chicken Stir-fry" and is_new_format:
                         found_stir_fry = True
                         # Check for a known ingredient ID (assuming 'Pre-cooked chicken' is ID 119)
                         has_chicken = any(item[0] == 119 or (item[0] is None and "chicken" in item[1].lower()) for item in ingredients)
                         print(f"    Verification: Found Stir-fry in new format. Has chicken ID (119)? {has_chicken}")
                    if name == "Lemon Herb Roasted Salmon" and is_new_format:
                         found_salmon = True
                         # Check for a known ingredient ID (assuming 'Salmon' is ID 134)
                         has_salmon = any(item[0] == 134 for item in ingredients)
                         print(f"    Verification: Found Salmon in new format. Has salmon ID (134)? {has_salmon}")
                         
                else:
                    print(f"    Ingredients JSON is not a list: {ingredients_json}")
                    
            except json.JSONDecodeError:
                print(f"  Ingredients: Failed to parse JSON - {ingredients_json}")
            except Exception as e:
                 print(f"  Error processing ingredients: {e}")

    else:
        print("  No entries found in new_meal_ideas.")
        
    if found_stir_fry and found_salmon:
         print("\n[TEST RESULT - SUCCESS] Both recipes found in DB with new ingredient format.")
    else:
         print("\n[TEST RESULT - FAIL] One or both recipes missing or not in the correct format.")


# --- Main Execution ---
if __name__ == "__main__":
    print("--- Running New Meal Ideation Save Test ---")
    db_test = None
    try:
        # 1. Reset DB to baseline state
        print("\nResetting database...")
        resetter = ResetDB()
        resetter.reload_all()
        if resetter.db and resetter.db.conn:
            resetter.db.disconnect()
        print("✓ Database reset complete.")
        
        # 2. Initialize DB connection for the test
        print("\nInitializing DB for test...")
        db_test, tables_test = init_tables()
        if not db_test or not tables_test:
            raise ConnectionError("Failed to initialize database for test.")
        print("✓ DB initialized.")
        
        # 3. Run the test pipeline
        run_test_pipeline(db_test, tables_test)

    except Exception as e:
        print(f"\n--- Test Failed Unexpectedly ---")
        print(f"Error: {e}")
        print(traceback.format_exc())
    finally:
        # 4. Clean up DB connection
        if db_test and db_test.conn:
            print("\nDisconnecting test database.")
            db_test.disconnect()

    print("\n--- Test Script Finished ---") 