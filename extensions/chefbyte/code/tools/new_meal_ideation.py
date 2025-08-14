# new_meal_ideation.py

"""
This script generates new meal ideas based on user intent and existing data.
It utilizes the taste profile, saved meals, and user intent to create meal suggestions.
The output is a list of meals, each containing the name, preparation time, ingredients, and recipe.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from db.db_functions import Database, init_tables, IngredientsFood
from helpers.ingredient_translator import IngredientTranslator
import json
from typing import List, Optional, Dict, Tuple, Any
import re
import traceback # For error logging

# Load environment variables
load_dotenv()

# Define Pydantic models
class RouterDecision(BaseModel):
    layer: int = Field(..., description="Which layer to activate: 1 for meal descriptions, 2 for full recipes, 3 for saving to database", ge=1, le=3)
    limit_to_inventory: bool = Field(False, description="Whether to limit meal generation to current inventory items")
    selected_items: List[int] = Field(default=[], description="List of item numbers the user has selected to proceed with")

class MealDescription(BaseModel):
    name: str = Field(..., description="The name of the meal")
    description: str = Field(..., description="Brief description of the meal")

# Define an intermediate model for raw ingredient parsing from LLM
class RawIngredient(BaseModel):
    name: str = Field(..., description="Ingredient name as extracted from text")
    amount: str = Field(..., description="Ingredient amount/quantity as extracted from text")

# Updated MealRecipe model to use the final [id, name, amount] format
class MealRecipe(BaseModel):
    name: str = Field(..., description="The name of the meal")
    # Use Tuple for the inner structure: [Optional[int], str, str]
    ingredients: List[Tuple[Optional[int], str, str]] = Field(..., description="List of translated ingredients: [food_id, name, amount]")
    prep_time_minutes: int = Field(..., description="Preparation time in minutes")
    recipe: str = Field(..., description="Detailed recipe instructions")

class MealIdeationEngine:
    def __init__(self, db: Database, tables: dict, llm_model="gpt-4o-mini"):
        """Initialize engine with shared DB/Table objects and LLM model."""
        self.db = db
        self.tables = tables
        self.llm_model = llm_model
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        
        # Initialize IngredientTranslator - requires IngredientsFood table object
        try:
            # Ensure IngredientsFood table object exists in the passed tables dict
            if "ingredients_foods" not in self.tables:
                raise ValueError("'ingredients_foods' table object not found in provided tables dictionary.")
            self.translator = IngredientTranslator(self.db, self.tables["ingredients_foods"])
            print("[MealIdeationEngine] IngredientTranslator initialized.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize IngredientTranslator in MealIdeationEngine: {e}")
            raise # Re-raise the error to prevent engine from initializing incorrectly
        
        # Initialize the Pydantic output parsers
        self.router_parser = PydanticOutputParser(pydantic_object=RouterDecision)
        self.recipe_parser = PydanticOutputParser(pydantic_object=List[MealRecipe])
        
        # Router prompt template
        self.router_prompt = (
            "You are an AI assistant analyzing a user message to route meal ideation requests.\n"
            "Based **only on the single user message provided**, decide:\n"
            "1. Which generation layer to activate:\n"
            "   - Layer 1 (Descriptions): If user is asking for initial meal *ideas* or *suggestions* (e.g., 'give me ideas', 'suggest meals'). Use this as default if unsure.\n"
            "   - Layer 2 (Recipes): If user explicitly asks for full *recipes* for previously mentioned ideas (e.g., 'get recipe for option 1', 'show me how to make the first one'). \n"
            "   - Layer 3 (Save): If user explicitly asks to *save* the recipes just presented (e.g., 'save these', 'add them to my list'). \n\n"
            "2. Whether to limit suggestions to current inventory:\n"
            "   - True if the user's message explicitly asks for meals they can make *now* or *with current ingredients*.\n"
            "   - False otherwise (default).\n\n"
            "3. Which numbered items the user selected (if Layer 2 or 3 is chosen):\n"
            "   - Extract numbers if the user refers to specific options (e.g., 'recipe for 1 and 3', 'save number 2').\n"
            "   - Return an empty list otherwise.\n\n"
            "User Message:\n{user_message}\n\n"
            "{format_instructions}"
        )
        
        # Layer 1: Meal descriptions generation prompt
        self.description_generation_prompt = (
            "You are a culinary AI helping generate personalized meal suggestions.\n"
            "Analyze the message history below and determine what kind of meals the user is interested in.\n"
            "Then generate 3 interesting meal ideas that match the user's preferences and requests.\n\n"
            "Message History:\n{message_history}\n\n"
            "Consider these sources of preferences:\n"
            "1. Taste Profile:\n{taste_profile}\n"
            "2. Saved Meals:\n{saved_meals}\n"
            "3. Existing Meal Ideas:\n{existing_meal_ideas}\n\n"
            "Using these preferences as inspiration:\n"
            "- Create new meals that match their taste profile\n"
            "- Take inspiration from elements of their saved meals they enjoy\n"
            "- DO NOT duplicate any saved meals or existing meal ideas\n"
            "{inventory_constraint}\n"
            "- Focus on creating meals that align with what the user is asking for\n\n"
            "Current Inventory:\n{current_inventory}\n\n"
            "IMPORTANT: Number each meal suggestion (1, 2, 3) for the user to easily reference them.\n"
            "Format each suggestion as:\n"
            "MEAL #1: <meal name>\n"
            "Description: <brief description>\n\n"
            "MEAL #2: <meal name>\n"
            "Description: <brief description>\n\n"
            "MEAL #3: <meal name>\n"
            "Description: <brief description>\n\n"
            "After presenting the meal ideas, ask the user if they would like to:\n"
            "1. Generate more meal ideas\n"
            "2. Build out the full recipes for any of these options\n\n"
            "New Meal Ideas:"
        )
        
        # Layer 2: Full recipe generation prompt
        self.recipe_generation_prompt = (
            "You are a culinary AI helping develop complete recipes based on meal descriptions.\n"
            "Generate detailed recipes for these selected meal ideas:\n{selected_meal_descriptions}\n\n"
            "Consider these sources of preferences:\n"
            "1. Taste Profile:\n{taste_profile}\n"
            "2. Saved Meals:\n{saved_meals}\n\n"
            "Using these preferences as inspiration:\n"
            "- Create recipes that match their taste profile\n"
            "- Take inspiration from elements of their saved meals they enjoy\n"
            "- Make the recipes practical and achievable\n"
            "{inventory_constraint}\n\n"
            "Current Inventory:\n{current_inventory}\n\n"
            "IMPORTANT: Maintain the same numbering from the original meal descriptions.\n"
            "For each meal, provide the following in this exact order:\n"
            "1. Name of the meal\n"
            "2. Detailed recipe instructions\n"
            "3. Ingredients with amounts (e.g., 'Flour (1 cup)', 'Eggs (2 large)')\n" # Instruct LLM on ingredient format
            "4. Prep time in minutes\n\n"
            "Format each recipe as:\n"
            "RECIPE #{meal_number}: <meal name>\n"
            "Recipe: <detailed cooking instructions>\n"
            "Ingredients: <ingredient1 (amount)>, <ingredient2 (amount)>, ...\n" # Example format
            "Prep Time: <time in minutes> minutes\n\n"
            "After presenting the recipes, ask the user if they would like to:\n"
            "1. Make adjustments to any recipe\n"
            "2. Save these recipes to their collection\n\n"
            "Complete Recipes:"
        )

        # Layer 3: Pydantic model for the *intermediate* parsing of raw ingredients
        class RawMealRecipe(BaseModel):
            name: str = Field(..., description="The name of the meal")
            ingredients: List[RawIngredient] = Field(..., description="List of raw ingredients with names and amounts")
            prep_time_minutes: int = Field(..., description="Preparation time in minutes")
            recipe: str = Field(..., description="Detailed recipe instructions")

        # Updated parser for Layer 3 extraction to use RawMealRecipe
        self.save_recipe_parser = PydanticOutputParser(pydantic_object=RawMealRecipe)
        self.save_extraction_prompt = (
            "Extract the recipe details (name, ingredients, prep_time_minutes, recipe instructions) from the following text.\n"
            "Ensure ingredients are a list of objects, each with 'name' and 'amount'. Extract these directly from the text (e.g., from 'Flour (1 cup)' extract name='Flour', amount='1 cup').\n"
            "Ensure prep_time_minutes is an integer.\n\n"
            "Recipe Text:\n{recipe_text}\n\n"
            "{format_instructions}"
        )
        
        # State management (simple example)
        self.current_meal_descriptions: List[MealDescription] = []
        self.current_recipes: List[MealRecipe] = []

    def _get_taste_profile(self) -> str:
        """Get taste profile using shared table object."""
        # Use self.tables
        taste_profile = self.tables["taste_profile"].read()
        return taste_profile if taste_profile else "No taste profile available"

    def _get_inventory(self) -> str:
        """Get inventory using shared table object."""
        # Use self.tables
        inventory_items = self.tables["inventory"].read()
        inventory_str = ""
        if inventory_items:
            for item in inventory_items:
                 # Access by key
                name = item['name']
                quantity = item['quantity']
                expiration = item['expiration']
                exp_str = f", Expires: {expiration}" if expiration else ""
                inventory_str += f"- {name}, Quantity: {quantity}{exp_str}\n"
        return inventory_str if inventory_str else "No inventory items available"

    def _get_saved_meals(self) -> str:
        """Get saved meals using shared table object."""
        # Use self.tables
        saved_meals = self.tables["saved_meals"].read()
        saved_meals_str = ""
        if saved_meals:
            for meal in saved_meals:
                 # Access by key
                name = meal['name']
                ingredients = meal['ingredients'] # Keep as JSON string for context
                saved_meals_str += f"Meal: {name}\nIngredients: {ingredients}\n\n"
        return saved_meals_str if saved_meals_str else "No saved meals available"
    
    def _get_existing_meal_ideas(self) -> str:
        """Get existing meal ideas using shared table object."""
        # Use self.tables
        meal_ideas = self.tables["new_meal_ideas"].read()
        meal_ideas_str = ""
        if meal_ideas:
            for meal in meal_ideas:
                 # Access by key
                name = meal['name']
                ingredients = meal['ingredients'] # Keep as JSON string for context
                meal_ideas_str += f"Meal: {name}\nIngredients: {ingredients}\n\n"
        return meal_ideas_str if meal_ideas_str else "No existing meal ideas available"
    
    def clear_meal_ideas_table(self):
        """Clear the new meal ideas table using shared table object."""
        # Use self.tables
        new_ideas_table = self.tables["new_meal_ideas"]
        try:
            print("\n=== CLEARING NEW MEAL IDEAS TABLE ===")
            meal_ideas = new_ideas_table.read()
            if meal_ideas:
                count = 0
                for meal in meal_ideas:
                     # Access by key
                    meal_id = meal['id']
                    new_ideas_table.delete(meal_id)
                    count += 1
                print(f"Cleared {count} meal ideas from the table")
            else:
                print("New meal ideas table is already empty")
        except Exception as e:
            print(f"Error clearing new meal ideas table: {str(e)}")

    def router(self, message_history: List) -> Tuple[int, bool, List[int]]:
        """Determine which layer to activate, whether to limit to inventory, and selected items, based on the latest message."""
        # Extract the single user message
        user_message = ""
        if message_history and isinstance(message_history[-1], HumanMessage):
            user_message = message_history[-1].content
        else:
            print("[WARN MealIdeationEngine Router] No user message found in history.")
            # Default to layer 1, no inventory limit, no selections
            return 1, False, [] 

        format_instructions = self.router_parser.get_format_instructions()
        prompt = ChatPromptTemplate.from_template(self.router_prompt)
        # Format prompt using only the single user message
        formatted_prompt = prompt.format(
            user_message=user_message,
            format_instructions=format_instructions
        )

        try:
            response = self.chat.invoke(formatted_prompt)
            decision = self.router_parser.parse(response.content)
            # Basic validation
            layer = max(1, min(3, decision.layer)) # Ensure layer is 1, 2, or 3
            limit = bool(decision.limit_to_inventory)
            # Ensure selected_items is a list of integers
            items = [int(item) for item in decision.selected_items if isinstance(item, (int, str)) and str(item).isdigit()] 
            return layer, limit, items
        except Exception as e:
            print(f"Error parsing router decision: {e}")
            # Fallback to layer 1 if parsing fails
            return 1, False, []

    def generate_meal_descriptions(self, message_history: List, limit_to_inventory: bool) -> str:
        """Layer 1: Generate meal descriptions."""
        history_text = "\n".join([f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}" for msg in message_history])
        inventory_constraint = "- ONLY suggest meals that can be made with the current inventory items" if limit_to_inventory else "- Suggest meals using available ingredients when possible, but don't be limited by inventory"
        
        # Get fresh context data
        taste_profile = self._get_taste_profile()
        saved_meals_context = self._get_saved_meals()
        existing_ideas_context = self._get_existing_meal_ideas()
        inventory_context = self._get_inventory()
            
        prompt = ChatPromptTemplate.from_template(self.description_generation_prompt)
        formatted_prompt = prompt.format(
            message_history=history_text,
            taste_profile=taste_profile,
            saved_meals=saved_meals_context,
            existing_meal_ideas=existing_ideas_context,
            inventory_constraint=inventory_constraint,
            current_inventory=inventory_context
        )
        
        try:
            response = self.chat.invoke(formatted_prompt)
            response_content = response.content.strip()
            print(f"\n=== LAYER 1 RESPONSE ===\n{response_content}\n=== END LAYER 1 RESPONSE ===\n")
            
            # TODO: Parse descriptions from response_content to store in self.current_meal_descriptions
            # This requires defining a reliable parsing method (regex, LLM, etc.)
            self.current_meal_descriptions = self._parse_meal_descriptions(response_content)
            
            return response_content
        except Exception as e:
            print(f"[ERROR] Layer 1 (Descriptions) failed: {e}")
            return "Sorry, I had trouble coming up with meal descriptions right now."

    def _parse_meal_descriptions(self, text: str) -> List[MealDescription]:
        """Helper to parse meal descriptions from LLM output (example using regex)."""
        descriptions = []
        # Simple regex example, might need refinement
        matches = re.findall(r"MEAL\s*#?\d+:\s*(.*?)\nDescription:\s*(.*?)(?=\nMEAL|$)", text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            name = match[0].strip()
            desc = match[1].strip()
            if name and desc:
                 descriptions.append(MealDescription(name=name, description=desc))
        self.current_meal_descriptions = descriptions # Update state
        print(f"[DEBUG] Parsed Descriptions: {self.current_meal_descriptions}")
        return descriptions

    def generate_recipes(self, message_history: List, selected_items: List[int], limit_to_inventory: bool) -> str:
        """Layer 2: Generate full recipes for selected meal descriptions."""
        if not selected_items:
            return "Please tell me which meal numbers you'd like recipes for (e.g., 'show me recipe 1')."
        if not self.current_meal_descriptions:
             return "I don't have any meal descriptions to generate recipes from. Please ask for some ideas first."

        selected_descriptions_text = ""
        valid_selected_items = []
        for item_num in selected_items:
             index = item_num - 1
             if 0 <= index < len(self.current_meal_descriptions):
                 meal_desc = self.current_meal_descriptions[index]
                 selected_descriptions_text += f"MEAL #{item_num}: {meal_desc.name}\nDescription: {meal_desc.description}\n\n"
                 valid_selected_items.append(item_num)
             else:
                  print(f"[WARN] Invalid selection number ignored: {item_num}")
                  
        if not valid_selected_items:
             return "The item numbers you selected don't match the previous suggestions. Please try again."

        history_text = "\n".join([f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}" for msg in message_history])
        inventory_constraint = "- ONLY use ingredients from the current inventory" if limit_to_inventory else "- Use available ingredients when possible, but add others if needed"
        
        # Get fresh context data
        taste_profile = self._get_taste_profile()
        saved_meals_context = self._get_saved_meals()
        inventory_context = self._get_inventory()

        prompt = ChatPromptTemplate.from_template(self.recipe_generation_prompt)
        formatted_prompt = prompt.format(
            selected_meal_descriptions=selected_descriptions_text,
            taste_profile=taste_profile,
            saved_meals=saved_meals_context,
            inventory_constraint=inventory_constraint,
            current_inventory=inventory_context,
            # If using Pydantic parser for recipes, add format instructions here
            # format_instructions=self.recipe_parser.get_format_instructions() 
        )

        try:
            response = self.chat.invoke(formatted_prompt)
            response_content = response.content.strip()
            print(f"\n=== LAYER 2 RESPONSE ===\n{response_content}\n=== END LAYER 2 RESPONSE ===\n")
            
            # Parse recipes using the updated _parse_recipes method
            # This will now populate self.current_recipes with MealRecipe objects
            # containing the final translated ingredient format [id, name, amount]
            self.current_recipes = self._parse_recipes(response_content) 
            
            return response_content
        except Exception as e:
            print(f"[ERROR] Layer 2 (Recipes) failed: {e}")
            return "Sorry, I had trouble generating the recipes right now."

    def _parse_recipes(self, text: str) -> List[MealRecipe]:
        """Helper to parse full recipes from LLM output, including ingredient translation."""
        final_recipes: List[MealRecipe] = []
        
        # Split text into blocks for each recipe
        # Assuming headers like "RECIPE #1: Meal Name"
        recipe_blocks = re.split(r"RECIPE\s*#?\d+:.*?\n", text)[1:] # Get content after headers
        meal_names = re.findall(r"RECIPE\s*#?\d+:\s*(.*?)\n", text, re.IGNORECASE) # Extract names
        
        if len(recipe_blocks) != len(meal_names):
             print(f"[WARN] Mismatch between recipe blocks ({len(recipe_blocks)}) and names ({len(meal_names)}). Parsing may be incomplete.")
             # Adjust loop range to avoid index errors
             num_to_process = min(len(recipe_blocks), len(meal_names))
        else:
             num_to_process = len(recipe_blocks)
             
        # Get format instructions for the intermediate raw ingredient parsing
        format_instructions = self.save_recipe_parser.get_format_instructions()
        
        for i in range(num_to_process):
            block = recipe_blocks[i]
            recipe_name = meal_names[i].strip()
            
            # Reconstruct the text for the intermediate parser
            parser_input_text = f"RECIPE #{i+1}: {recipe_name}\n{block.strip()}"
            
            prompt = ChatPromptTemplate.from_template(self.save_extraction_prompt)
            formatted_prompt = prompt.format(
                recipe_text=parser_input_text,
                format_instructions=format_instructions
            )
            
            try:
                # 1. Parse raw recipe details (name, raw_ingredients, prep_time, recipe) using LLM
                response = self.chat.invoke(formatted_prompt)
                raw_parsed_recipe: RawMealRecipe = self.save_recipe_parser.parse(response.content)
                
                # Ensure name consistency
                raw_parsed_recipe.name = recipe_name
                
                # 2. Translate raw ingredients using IngredientTranslator
                print(f"\n--- Translating Ingredients for '{recipe_name}' ---")
                raw_ingredients_list = [[ing.name, ing.amount] for ing in raw_parsed_recipe.ingredients]
                
                # Use the translator instance
                matched_tuples, new_tuples = self.translator.translate_ingredients(raw_ingredients_list)
                
                # Combine matched and new into the final [id, name, amount] format
                translated_ingredients: List[Tuple[Optional[int], str, str]] = []
                for orig_name, amount, food_id in matched_tuples:
                    # Use the matched ID, original name, and amount
                    translated_ingredients.append((food_id, orig_name, amount)) 
                for orig_name, amount, food_id in new_tuples:
                    # Use the new ID, original name, and amount
                    translated_ingredients.append((food_id, orig_name, amount))
                print("--- Ingredient Translation Finished ---")
                
                # 3. Create the final MealRecipe object with translated ingredients
                final_recipe = MealRecipe(
                    name=raw_parsed_recipe.name,
                    ingredients=translated_ingredients,
                    prep_time_minutes=raw_parsed_recipe.prep_time_minutes,
                    recipe=raw_parsed_recipe.recipe
                )
                final_recipes.append(final_recipe)
                
            except Exception as e:
                 print(f"[ERROR] Failed to parse or translate recipe block #{i+1} ('{recipe_name}'): {e}")
                 print(traceback.format_exc()) # Add traceback for parsing/translation errors
                      
        self.current_recipes = final_recipes # Update state with successfully parsed & translated recipes
        print(f"[DEBUG] Parsed & Translated Recipes: {self.current_recipes}")
        return final_recipes

    def save_recipes(self, selected_items: List[int]) -> Tuple[bool, str]:
        """Layer 3: Save selected recipes to the new_meal_ideas table."""
        if not selected_items:
            return False, "Please specify which recipe numbers you want to save."
        if not self.current_recipes:
             return False, "I don't have any recipes generated to save. Please generate recipes first."

        saved_count = 0
        skipped_count = 0
        confirmation_messages = []
        new_ideas_table = self.tables["new_meal_ideas"]

        # Map selected item numbers to indices in self.current_recipes
        # Assumes self.current_recipes maintains the order corresponding to original numbering
        recipes_to_save = []
        original_indices = {} # Map recipe index back to original number if needed
        
        # This mapping is tricky if recipe parsing failed for some items.
        # A better approach might be to store recipes in a dictionary keyed by original number.
        # For now, assume self.current_recipes aligns with successful parses.
        # We need a way to link the recipe objects back to the selected numbers.
        # Let's assume the MealRecipe object's name is sufficient for confirmation.
        # original_number = selected_items[i] if i < len(selected_items) else -1 # Fallback (if needed)
        
        # Check if a recipe with the same name already exists
        # TODO: Implement check against saved_meals and new_meal_ideas by name
        # existing_check = new_ideas_table.read_by_name(recipe_obj.name) ... etc.
        
        for i, recipe_obj in enumerate(self.current_recipes): 
             # This simple check assumes the order is preserved and matches the *selection* order
             # Example: If user selected [1, 3], current_recipes[0] is #1, current_recipes[1] is #3
             # We need to map this back if saving confirmation needs the original number.
             original_number = selected_items[i] if i < len(selected_items) else -1 # Fallback
             
             try:
                 # Pass the final MealRecipe object's fields to the create function
                 # The 'ingredients' field is already the list of [id, name, amount] tuples
                 new_id = new_ideas_table.create(
                     name=recipe_obj.name,
                     prep_time=recipe_obj.prep_time_minutes,
                     ingredients=recipe_obj.ingredients, # Pass the translated list
                     recipe=recipe_obj.recipe
                 )
                 if new_id:
                     confirmation_messages.append(f"Saved '{recipe_obj.name}' (ID: {new_id}) to New Meal Ideas.")
                     saved_count += 1
                 else:
                     confirmation_messages.append(f"Failed to save '{recipe_obj.name}'.")
                     skipped_count += 1
             except Exception as e:
                 print(f"[ERROR] Failed to save recipe '{recipe_obj.name}': {e}")
                 confirmation_messages.append(f"Error saving '{recipe_obj.name}'.")
                 skipped_count += 1

        if saved_count > 0:
             final_confirmation = f"Saved {saved_count} recipe(s) to your New Meal Ideas.\n" + "\n".join(confirmation_messages)
             return True, final_confirmation
        elif skipped_count > 0:
             return False, "Could not save the selected recipe(s) due to errors." 
        else:
             # This case happens if selected_items was valid but current_recipes was empty
             return False, "No valid recipes were available to save for your selection."

    # --- Execute Method --- 
    def execute(self, chat_history: List[Dict[str, str]]) -> str:
        """Main entry point called by the ToolRouter."""
        try:
            # 1. Route to determine layer and parameters
            layer, limit_to_inventory, selected_items = self.router(chat_history)
            print(f"[INFO] MealIdeationEngine - Layer: {layer}, Limit Inventory: {limit_to_inventory}, Selected: {selected_items}")

            # 2. Execute the appropriate layer
            if layer == 1:
                # Generate Descriptions
                output = self.generate_meal_descriptions(chat_history, limit_to_inventory)
            elif layer == 2:
                # Generate Recipes for selected descriptions
                output = self.generate_recipes(chat_history, selected_items, limit_to_inventory)
            elif layer == 3:
                # Save selected recipes
                # Layer 3 needs selected items from the *previous* turn (recipes shown)
                # The router needs context to know which recipes were presented.
                # For simplicity now, assume selected_items refers to recipes shown in the *last assistant message*
                # This requires parsing the last assistant message or better state management.
                # Let's assume selected_items from router directly maps to recipe indices for now.
                success, output = self.save_recipes(selected_items)
            else:
                output = "Internal error: Invalid layer determined by router."
                
            return output

        except Exception as e:
            print(f"[ERROR] MealIdeationEngine execution failed: {e}")
            print(traceback.format_exc())
            return "Sorry, I encountered an error while generating recipe ideas."


# Optional: Top-level function if preferred over class instance
def generate_meal_ideas(message_history: List) -> str:
    """Main function to generate meal ideas based on message history using the engine."""
    # Need to handle DB connection if using this function directly
    try:
        db, tables = init_tables()
        if not db or not tables:
             return "Error: Could not initialize database for meal ideation."
        engine = MealIdeationEngine(db, tables)
        result = engine.execute(message_history)
        db.disconnect() # Disconnect after use
        return result
    except Exception as e:
         print(f"[ERROR] generate_meal_ideas function failed: {e}")
         print(traceback.format_exc())
         # Ensure DB disconnects even on error if connection was made
         if 'db' in locals() and db:
              db.disconnect()
         return "Sorry, an error occurred while generating meal ideas."
