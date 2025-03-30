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
from db.db_functions import Database, init_tables
import json
from typing import List, Optional, Dict, Tuple, Any
import re

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

class MealRecipe(BaseModel):
    name: str = Field(..., description="The name of the meal")
    ingredients: List[dict] = Field(..., description="List of ingredients with amounts")
    prep_time_minutes: int = Field(..., description="Preparation time in minutes")
    recipe: str = Field(..., description="Detailed recipe instructions")

class MealIdeationEngine:
    def __init__(self, llm_model="gpt-4o-mini"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        
        # Initialize database and tables
        self.db, self.tables = init_tables()
        
        # Get data from database
        self.taste_profile = self._get_taste_profile()
        self.current_inventory = self._get_inventory()
        self.saved_meals = self._get_saved_meals()
        self.existing_meal_ideas = self._get_existing_meal_ideas()
        
        # Initialize the Pydantic output parsers
        self.router_parser = PydanticOutputParser(pydantic_object=RouterDecision)
        
        # Router prompt template
        self.router_prompt = (
            "You are an AI assistant that analyzes user message history to determine their meal generation needs.\n"
            "Based on the conversation, decide:\n"
            "1. Which generation layer to activate:\n"
            "   - Layer 1: Generate initial meal descriptions (if user is asking for meal ideas or suggestions)\n"
            "   - Layer 2: Generate full recipes (if user has selected meal descriptions and wants recipes)\n"
            "   - Layer 3: Save recipes to database (if user has reviewed recipes and wants to save them)\n\n"
            "2. Whether to limit suggestions to current inventory:\n"
            "   - True if the user explicitly asks for meals they can make with what they have\n"
            "   - False otherwise (default)\n\n"
            "3. Which numbered items the user has selected (if any):\n"
            "   - If user has said something like 'I like options 1 and 3' or 'Let's go with the first meal'\n"
            "   - Return those numbers in the selected_items field (e.g., [1, 3] or [1])\n"
            "   - Return an empty list if no selections are made\n\n"
            "Message History:\n{message_history}\n\n"
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
            "3. Ingredients with amounts\n"
            "4. Prep time in minutes\n\n"
            "Format each recipe as:\n"
            "RECIPE #{meal_number}: <meal name>\n"
            "Recipe: <detailed cooking instructions>\n"
            "Ingredients: <ingredient1 (amount)>, <ingredient2 (amount)>, ...\n"
            "Prep Time: <time in minutes> minutes\n\n"
            "After presenting the recipes, ask the user if they would like to:\n"
            "1. Make adjustments to any recipe\n"
            "2. Save these recipes to their collection\n\n"
            "Complete Recipes:"
        )

    def _get_taste_profile(self) -> str:
        """Get taste profile from database"""
        result = self.tables["taste_profile"].read()
        if result and len(result) > 0:
            return result[0][0]
        return "No taste profile available"

    def _get_inventory(self) -> str:
        """Get inventory from database"""
        inventory_items = self.tables["inventory"].read()
        inventory_str = ""
        if inventory_items:
            for item in inventory_items:
                item_id, name, quantity, expiration = item
                exp_str = f", Expires: {expiration}" if expiration else ""
                inventory_str += f"- {name}, Quantity: {quantity}{exp_str}\n"
        return inventory_str if inventory_str else "No inventory items available"

    def _get_saved_meals(self) -> str:
        """Get saved meals from database"""
        saved_meals = self.tables["saved_meals"].read()
        saved_meals_str = ""
        if saved_meals:
            for meal in saved_meals:
                meal_id, name, prep_time, ingredients, recipe = meal
                saved_meals_str += f"Meal: {name}\nIngredients: {ingredients}\n\n"
        return saved_meals_str if saved_meals_str else "No saved meals available"
    
    def _get_existing_meal_ideas(self) -> str:
        """Get existing meal ideas from database"""
        meal_ideas = self.tables["new_meal_ideas"].read()
        meal_ideas_str = ""
        if meal_ideas:
            for meal in meal_ideas:
                meal_id, name, prep_time, ingredients, recipe = meal
                meal_ideas_str += f"Meal: {name}\nIngredients: {ingredients}\n\n"
        return meal_ideas_str if meal_ideas_str else "No existing meal ideas available"
    
    def clear_meal_ideas_table(self):
        """Clear the new meal ideas table for testing"""
        try:
            print("\n=== CLEARING DATABASE ===")
            # Get all existing meal ideas
            meal_ideas = self.tables["new_meal_ideas"].read()
            if meal_ideas:
                for meal in meal_ideas:
                    meal_id = meal[0]
                    self.tables["new_meal_ideas"].delete(meal_id)
                print(f"Cleared {len(meal_ideas)} meal ideas from the table")
            else:
                print("Database is already empty")
        except Exception as e:
            print(f"Error clearing database: {str(e)}")

    def router(self, message_history: List) -> Tuple[int, bool, List[int]]:
        """Determine which layer to activate, whether to limit to inventory, and selected items"""
        # Format the message history for the prompt
        history_text = ""
        for i, message in enumerate(message_history):
            role = "User" if isinstance(message, HumanMessage) else "Assistant"
            history_text += f"{role}: {message.content}\n"
            
        format_instructions = self.router_parser.get_format_instructions()
        
        # The LLM should analyze the message history to determine:
        # 1. Which layer to activate based on the conversation context
        # 2. Whether to limit suggestions to inventory
        # 3. Which numbered items the user has selected
        prompt = ChatPromptTemplate.from_template(self.router_prompt)
        formatted_prompt = prompt.format(
            message_history=history_text,
            format_instructions=format_instructions
        )
        
        try:
            response = self.chat.invoke(formatted_prompt)
            print("\n=== ROUTER RESPONSE ===")
            print(response.content.strip())
            print("=== END ROUTER RESPONSE ===\n")
            
            # Parse the router decision
            decision = self.router_parser.parse(response.content)
            return decision.layer, decision.limit_to_inventory, decision.selected_items
            
        except Exception as e:
            print(f"Error in router: {str(e)}")
            # Default to layer 1, no inventory limitation, no selections
            return 1, False, []

    def generate_meal_descriptions(self, message_history: List, limit_to_inventory: bool) -> str:
        """Layer 1: Generate meal descriptions based on message history"""
        # Format the message history for the prompt
        history_text = ""
        for i, message in enumerate(message_history):
            role = "User" if isinstance(message, HumanMessage) else "Assistant"
            history_text += f"{role}: {message.content}\n"
            
        # Set inventory constraint based on limit_to_inventory flag
        if limit_to_inventory:
            inventory_constraint = "- ONLY suggest meals that can be made with the current inventory items"
        else:
            inventory_constraint = "- Suggest meals that use available ingredients when possible, but don't be limited by inventory"
            
        prompt = ChatPromptTemplate.from_template(self.description_generation_prompt)
        formatted_prompt = prompt.format(
            message_history=history_text,
            taste_profile=self.taste_profile,
            saved_meals=self.saved_meals,
            existing_meal_ideas=self.existing_meal_ideas,
            inventory_constraint=inventory_constraint,
            current_inventory=self.current_inventory
        )
        
        try:
            response = self.chat.invoke(formatted_prompt)
            return response.content.strip()
        except Exception as e:
            raise Exception(f"Error generating meal descriptions: {str(e)}")

    def generate_full_recipes(self, meal_descriptions: str, selected_items: List[int], limit_to_inventory: bool) -> str:
        """Layer 2: Generate full recipes based on selected meal descriptions"""
        # If we have selected items, filter the meal descriptions to only include those items
        if selected_items:
            filtered_descriptions = ""
            lines = meal_descriptions.split('\n')
            
            include_next_lines = False
            current_meal_num = None
            
            for line in lines:
                # Check if this is a meal header line with numbering
                if line.startswith("MEAL #"):
                    try:
                        meal_num = int(line.split("#")[1].split(":")[0].strip())
                        current_meal_num = meal_num
                        include_next_lines = meal_num in selected_items
                    except:
                        include_next_lines = False
                
                # If we're currently including lines for a selected meal, add this line
                if include_next_lines:
                    filtered_descriptions += line + "\n"
            
            selected_meal_descriptions = filtered_descriptions.strip()
        else:
            # If no selections made, use all descriptions
            selected_meal_descriptions = meal_descriptions
            
        # Set inventory constraint based on limit_to_inventory flag
        if limit_to_inventory:
            inventory_constraint = "- ONLY use ingredients from the current inventory"
        else:
            inventory_constraint = "- Use available ingredients when possible, but don't be limited by inventory"
            
        prompt = ChatPromptTemplate.from_template(self.recipe_generation_prompt)
        formatted_prompt = prompt.format(
            selected_meal_descriptions=selected_meal_descriptions,
            meal_number="meal_number", # This is a placeholder that will be replaced in the recipe
            taste_profile=self.taste_profile,
            saved_meals=self.saved_meals,
            inventory_constraint=inventory_constraint,
            current_inventory=self.current_inventory
        )
        
        try:
            response = self.chat.invoke(formatted_prompt)
            return response.content.strip()
        except Exception as e:
            raise Exception(f"Error generating full recipes: {str(e)}")

    def extract_meal_descriptions_from_history(self, message_history: List) -> str:
        """Extract meal descriptions from message history for Layer 2"""
        descriptions = ""
        
        # Search backward through the message history to find the most recent meal descriptions
        for message in reversed(message_history):
            if isinstance(message, AIMessage):
                content = message.content
                # Look for numbered meal descriptions
                if "MEAL #" in content and "Description:" in content:
                    descriptions = content
                    break
        
        if not descriptions:
            # If not found in AI messages, check user messages (they might have edited/selected)
            for message in reversed(message_history):
                if isinstance(message, HumanMessage):
                    content = message.content
                    if "MEAL #" in content and "Description:" in content:
                        descriptions = content
                        break
        
        return descriptions.strip() if descriptions else "No meal descriptions found in message history"

    def extract_recipes_from_history(self, message_history: List) -> str:
        """Extract full recipes from message history for Layer 3"""
        recipes = ""
        
        # Search backward through the message history to find the most recent recipes
        for message in reversed(message_history):
            if isinstance(message, AIMessage):
                content = message.content
                # Debug: print the content we're searching
                print(f"Looking for recipe in content (length {len(content)}): {content[:100]}...")
                # Look for recipes - check various possible formats
                if "RECIPE #" in content:
                    recipes = content
                    print(f"Found recipe with 'RECIPE #' format")
                    break
                elif "Recipe:" in content and "Ingredients:" in content:
                    recipes = content
                    print(f"Found recipe with 'Recipe:' and 'Ingredients:' format")  
                    break
        
        if not recipes:
            # If not found in AI messages, check user messages (they might have edited)
            for message in reversed(message_history):
                if isinstance(message, HumanMessage):
                    content = message.content
                    if "RECIPE #" in content or ("Recipe:" in content and "Ingredients:" in content):
                        recipes = content
                        break
        
        return recipes.strip() if recipes else "No recipes found in message history"

    def save_selected_recipes(self, recipes_text: str, selected_items: List[int]) -> str:
        """Layer 3: Save selected recipes to database"""
        print("\n=== SAVING RECIPES ===")
        print(f"Selected items: {selected_items}")
        print(f"Recipe text length: {len(recipes_text)}")
        print(f"Recipe text starts with: {recipes_text[:100]}...")
        
        # Try to handle the format with LAYER prefix from our chat interface
        if recipes_text.startswith("[LAYER"):
            first_line_end = recipes_text.find("\n")
            if first_line_end > 0:
                recipes_text = recipes_text[first_line_end:].strip()
                print("Stripped LAYER prefix from recipe text")
        
        # Split the text into individual recipes
        recipe_sections = []
        
        # First try to split by RECIPE # format
        if "RECIPE #" in recipes_text:
            recipe_sections = recipes_text.split("RECIPE #")
            # Remove empty first section if it exists
            if recipe_sections and not recipe_sections[0].strip():
                recipe_sections = recipe_sections[1:]
            print(f"Found {len(recipe_sections)} recipe sections using 'RECIPE #' format")
        # Fallback: try other formats if no sections found
        else:
            # Try other formats here if needed
            print("Using alternative recipe parsing logic")
            # Just use the whole text as one recipe if we can't split
            recipe_sections = [recipes_text]
        
        saved_recipes = []
        
        for i, section in enumerate(recipe_sections):
            if not section.strip():
                continue
                
            try:
                # If using RECIPE # format, extract the number
                recipe_num = i + 1  # Default to section index + 1
                if section.startswith(str(i+1) + ":"):
                    recipe_num = i + 1
                elif ":" in section and section.split(":", 1)[0].strip().isdigit():
                    recipe_num = int(section.split(":", 1)[0].strip())
                
                print(f"Processing recipe #{recipe_num}")
                
                # Check if this recipe is selected (or if no selections were provided, include all)
                if selected_items and recipe_num not in selected_items:
                    print(f"Skipping recipe #{recipe_num}: Not selected")
                    continue
                
                # Split the section by newlines
                lines = section.split('\n')
                
                # Extract the name - first try to get it from format like "RECIPE #1: Name"
                name = ""
                if ":" in lines[0]:
                    name = lines[0].split(":", 1)[1].strip()
                else:
                    # Try to find a line that looks like a recipe name (first non-empty line)
                    for line in lines:
                        if line.strip() and not line.startswith("Recipe:") and not line.startswith("Ingredients:"):
                            name = line.strip()
                            break
                
                if not name:
                    print(f"Skipping recipe #{recipe_num}: No name found")
                    continue
                
                print(f"Recipe name: {name}")
                
                # Initialize variables
                ingredients_line = ""
                prep_time = 30  # Default prep time
                recipe_text = ""
                
                # First pass: Find any multiline ingredients sections
                multiline_ingredients = []
                in_ingredients_section = False
                for line_idx, line in enumerate(lines):
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Check for ingredient section start
                    if line == "Ingredients:" or line == "Ingredients":
                        in_ingredients_section = True
                        continue
                    # Check for end of ingredients section (next section starts or prep time)
                    elif in_ingredients_section and (line.startswith("Prep Time:") or line.startswith("Recipe:") or line == ""):
                        in_ingredients_section = False
                    # Collect ingredients while in the ingredients section
                    elif in_ingredients_section:
                        multiline_ingredients.append(line)
                
                # If we found multiline ingredients, combine them
                if multiline_ingredients:
                    ingredients_line = ", ".join(multiline_ingredients)
                    print(f"Found multiline ingredients: {ingredients_line}")
                
                # Second pass: Process the rest of the details (recipe steps, prep time, etc)
                in_recipe_section = False
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Extract recipe instructions
                    if line.startswith("Recipe:"):
                        in_recipe_section = True
                        recipe_text = line.replace("Recipe:", "").strip()
                    elif in_recipe_section and (line.startswith("Ingredients:") or line.startswith("Prep Time:")):
                        in_recipe_section = False
                        if line.startswith("Ingredients:") and not ingredients_line:
                            ingredients_line = line.replace("Ingredients:", "").strip()
                    elif in_recipe_section:
                        # Still in recipe section, add to recipe text
                        recipe_text += "\n" + line
                    elif line.startswith("Ingredients:") and not ingredients_line:
                        # Direct ingredient line
                        ingredients_line = line.replace("Ingredients:", "").strip()
                    elif "Prep Time:" in line or "Prep time:" in line:
                        # Extract prep time - handle various formats
                        time_text = line
                        if "Prep Time:" in line:
                            time_text = line.split("Prep Time:", 1)[1]
                        elif "Prep time:" in line:
                            time_text = line.split("Prep time:", 1)[1]
                        
                        # Find number in the text
                        import re
                        time_match = re.search(r'\d+', time_text)
                        if time_match:
                            prep_time = int(time_match.group())
                
                # If we still don't have recipe text but have numbered steps, try to collect them
                if not recipe_text:
                    recipe_steps = []
                    in_steps = False
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        # Look for numbered steps like "1. Step one" or just steps starting with numbers
                        if re.match(r'^\d+\.?\s', line):
                            in_steps = True
                            recipe_steps.append(line)
                        elif in_steps and not line.startswith("Ingredients:") and not "Prep Time:" in line:
                            # Continue adding lines as part of the steps
                            recipe_steps.append(line)
                        elif line.startswith("Ingredients:") or "Prep Time:" in line:
                            # Stop collecting steps when we hit ingredients or prep time
                            in_steps = False
                    
                    if recipe_steps:
                        recipe_text = "\n".join(recipe_steps)
                
                # Check if we have enough data to save the recipe
                print(f"Ingredients line: {ingredients_line}")
                print(f"Recipe text: {recipe_text[:50]}..." if recipe_text else "No recipe text found")
                print(f"Prep time: {prep_time}")
                
                if not ingredients_line:
                    print(f"Skipping recipe #{recipe_num} '{name}': No ingredients found")
                    continue
                
                if not recipe_text:
                    # Even without recipe text, we'll still save it if we have ingredients
                    recipe_text = "No detailed instructions provided."
                    print(f"No recipe instructions found, but continuing with default text")
                
                # Convert ingredients to proper JSON format
                # Handle different formats: comma-separated list, or bullet points
                if "\n-" in ingredients_line:
                    # Bullet point format
                    ingredients_list = [item.strip().lstrip('-').strip() for item in ingredients_line.split('\n-')]
                else:
                    # Comma separated format
                    ingredients_list = [item.strip() for item in ingredients_line.split(',')]
                
                # Process ingredients into JSON - ignoring food database lookup
                ingredients_json = json.dumps([
                    {"name": item.split('(')[0].strip() if '(' in item else item.strip(), 
                     "amount": item.split('(')[1].split(')')[0].strip() if '(' in item and ')' in item else "to taste"} 
                    for item in ingredients_list if item.strip()
                ])
                
                # Create meal in database
                meal_id = self.tables["new_meal_ideas"].create(
                    name=name,
                    prep_time=prep_time,
                    ingredients=ingredients_json,
                    recipe=recipe_text
                )
                
                if meal_id:
                    print(f"Added recipe: {name} (ID: {meal_id})")
                    saved_recipes.append({"number": recipe_num, "name": name, "id": meal_id})
                    
            except Exception as e:
                print(f"Error processing recipe {i+1}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Create a summary of saved recipes
        if saved_recipes:
            summary = "Successfully saved the following recipes to your collection:\n"
            for recipe in saved_recipes:
                summary += f"- Recipe #{recipe['number']}: {recipe['name']} (ID: {recipe['id']})\n"
            return summary
        else:
            return "No recipes were saved to the database. Please try again with valid recipe selections."

    def process_message_history(self, message_history: List) -> Dict[str, Any]:
        """Main function to process message history and generate appropriate meal content"""
        # Clear meal ideas table for testing (only in test mode)
        if os.getenv("TEST_MODE", "false").lower() == "true":
            self.clear_meal_ideas_table()
        
        # Run router to determine which layer to activate
        layer, limit_to_inventory, selected_items = self.router(message_history)
        
        result = {
            "layer": layer,
            "limit_to_inventory": limit_to_inventory,
            "selected_items": selected_items,
            "content": ""
        }
        
        if layer == 1:
            # Layer 1: Generate meal descriptions
            print(f"\n=== LAYER {layer} ===")
            all_descriptions = self.generate_meal_descriptions(message_history, limit_to_inventory)
            result["content"] = all_descriptions
            
        elif layer == 2:
            # Layer 2: Generate full recipes
            print(f"\n=== LAYER {layer} ===")
            
            # Extract meal descriptions from message history
            meal_descriptions = self.extract_meal_descriptions_from_history(message_history)
            
            if "No meal descriptions found" in meal_descriptions:
                result["content"] = "No meal descriptions found in message history. Please generate meal ideas first."
            else:
                recipes = self.generate_full_recipes(meal_descriptions, selected_items, limit_to_inventory)
                result["content"] = recipes
                
        elif layer == 3:
            # Layer 3: Save selected recipes to database
            print(f"\n=== LAYER {layer} ===")
            
            # Extract recipes from message history
            recipes = self.extract_recipes_from_history(message_history)
            
            if "No recipes found" in recipes:
                result["content"] = "No recipes found in message history. Please generate recipes first."
            else:
                save_result = self.save_selected_recipes(recipes, selected_items)
                result["content"] = save_result
                
        return result

# Main function to be called by the tool router
def generate_meal_ideas(message_history):
    """Generate meal ideas based on message history"""
    engine = MealIdeationEngine()
    result = engine.process_message_history(message_history)
    return result["content"]
