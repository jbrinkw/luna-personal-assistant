# pull_router.py

"""
This module contains the PullRouter class, which is responsible for handling user input
and checking if the response requires data from the database. It adds the necessary data
to the response context for further processing.
"""

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import os
import json
import re
from typing import List
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from db.db_functions import Database, Inventory, TasteProfile, SavedMeals, ShoppingList, IngredientsFood, DailyPlanner, NewMealIdeas, SavedMealsInStockIds, NewMealIdeasInStockIds
import traceback

# Load environment variables
load_dotenv()

# Define models for extraction
class PullRouterDecision(BaseModel):
    needs_inventory: bool = Field(..., description="Whether inventory information is needed")
    needs_taste_profile: bool = Field(..., description="Whether taste profile information is needed")
    needs_saved_meals: bool = Field(..., description="Whether saved meals information is needed")
    needs_shopping_list: bool = Field(..., description="Whether shopping list information is needed")
    needs_daily_notes: bool = Field(..., description="Whether daily planner information is needed")
    needs_new_meal_ideas: bool = Field(..., description="Whether new meal ideas information is needed")
    needs_instock_meals: bool = Field(..., description="Whether information about meals that can be made with current ingredients is needed")
    needs_ingredients_info: bool = Field(..., description="Whether ingredients information is needed")

class PullRouter:
    def __init__(self, router_model, db, tables):
        """Initialize PullRouter with the main router model and database objects."""
        self.router_model = router_model
        self.db = db  # Store the passed Database object
        self.tables = tables # Store the passed dictionary of table objects
        
        self.output_parser = PydanticOutputParser(pydantic_object=PullRouterDecision)
        self.format_instructions = self.output_parser.get_format_instructions()
        
        # Router prompt template
        self.router_prompt_template = """\
Analyze the most recent user message and determine if it's asking about inventory information, taste profile information, saved meals information, shopping list information, daily planner information, new meal ideas, in-stock meals, or ingredients information.

Examples of inventory queries:
- "What food do I have?"
- "When does my milk expire?"
- "How much flour do I have left?"
- "Show me my inventory"
- "What ingredients do I have for making pasta?"
- "What's in my fridge?"
- "Do I have tomatoes?"

Examples of taste profile queries:
- "What foods do I like?"
- "What are my taste preferences?"
- "What's my taste profile?"
- "What do I usually eat?"
- "What are my dietary preferences?"
- "Show me my preferred foods"
- "What foods do I dislike?"

Examples of saved meals queries:
- "What recipes do I have saved?"
- "Show me my saved recipes"
- "Do I have a recipe for spaghetti?"
- "What meals have I saved?"
- "What's the recipe for lasagna?"
- "How do I make that chicken curry recipe I saved?"
- "List all my saved recipes"

Examples of shopping list queries:
- "What's on my shopping list?"
- "Show me my shopping list"
- "Do I need to buy milk?"
- "What do I need to buy?"
- "What items am I out of?"
- "What's on my grocery list?"
- "Is bread on my shopping list?"

Examples of daily planner queries:
- "What's on my meal plan for this week?"
- "Show me my meal plan"
- "What am I cooking tomorrow?"
- "What's for dinner this weekend?"
- "What meals do I have planned?"
- "Show me my schedule for next week"
- "What did I plan for this month?"

Examples of new meal ideas queries:
- "What new recipes do you suggest?"
- "Show me some meal ideas"
- "What new dishes can I try?"
- "Give me recipe suggestions"
- "What new meals have you recommended?"

Examples of in-stock meals queries:
- "What can I make with what I have?"
- "Show me recipes I can make right now"
- "What meals can I cook with my current ingredients?"
- "What's possible with my inventory?"
- "What can I cook without shopping?"

Examples of ingredients information queries:
- "Tell me about this ingredient"
- "How much chicken do I need to buy for 4 people?"
- "What's the minimum amount of flour I should purchase?"
- "Where can I buy this ingredient?"
- "Tell me about ingredient quantities"

Return your decision as a JSON object following this schema:
{format_instructions}

Most recent user message: {message}
"""

    def pull_context(self, chat_history):
        """
        Main function to determine what database context is needed based on the chat history.
        Returns a string with the relevant context information from the database.
        """
        # For tracking routing decisions (for debugging)
        routing_decisions = []
        
        # Get the most recent user message
        if not chat_history:
            routing_decisions.append(False)
            return ""
            
        # Find the most recent user message
        user_messages = [msg for msg in chat_history if isinstance(msg, HumanMessage)]
        if not user_messages:
            routing_decisions.append(False)
            return ""
            
        recent_user_message = user_messages[-1].content
        
        # Create the routing decision using the prompt template
        prompt = ChatPromptTemplate.from_template(template=self.router_prompt_template)
        messages = prompt.format_messages(
            message=recent_user_message,
            format_instructions=self.format_instructions
        )
        
        response = self.router_model.invoke(messages)
        
        try:
            # Parse the decision
            decision = self.output_parser.parse(response.content)
            needs_inventory = decision.needs_inventory
            needs_taste_profile = decision.needs_taste_profile
            needs_saved_meals = decision.needs_saved_meals
            needs_shopping_list = decision.needs_shopping_list
            needs_daily_notes = decision.needs_daily_notes
            needs_new_meal_ideas = decision.needs_new_meal_ideas
            needs_instock_meals = decision.needs_instock_meals
            needs_ingredients_info = decision.needs_ingredients_info
            
            # Add to routing decisions for tracking
            routing_decisions.append({
                "inventory": needs_inventory, 
                "taste_profile": needs_taste_profile,
                "saved_meals": needs_saved_meals,
                "shopping_list": needs_shopping_list,
                "daily_notes": needs_daily_notes,
                "new_meal_ideas": needs_new_meal_ideas,
                "instock_meals": needs_instock_meals,
                "ingredients_info": needs_ingredients_info
            })
            
            # Get context based on needs
            context = ""
            
            # Get inventory context if needed
            if needs_inventory:
                inventory_context = self.get_inventory_context()
                if inventory_context:
                    context += f"CURRENT INVENTORY:\n{inventory_context}\n\n"
                    routing_decisions.append(True)
                else:
                    routing_decisions.append(False)
            
            # Get taste profile context if needed
            if needs_taste_profile:
                taste_profile_context = self.get_taste_profile_context()
                if taste_profile_context:
                    context += f"TASTE PROFILE:\n{taste_profile_context}\n\n"
                    routing_decisions.append(True)
                else:
                    routing_decisions.append(False)
            
            # Get saved meals context if needed
            if needs_saved_meals:
                saved_meals_context = self.get_saved_meals_context()
                if saved_meals_context:
                    context += f"SAVED MEALS:\n{saved_meals_context}\n\n"
                    routing_decisions.append(True)
                else:
                    routing_decisions.append(False)
            
            # Get shopping list context if needed
            if needs_shopping_list:
                shopping_list_context = self.get_shopping_list_context()
                if shopping_list_context:
                    context += f"SHOPPING LIST:\n{shopping_list_context}\n\n"
                    routing_decisions.append(True)
                else:
                    routing_decisions.append(False)
                    
            # Get daily notes context if needed
            if needs_daily_notes:
                daily_notes_context = self.get_daily_notes_context()
                if daily_notes_context:
                    context += f"DAILY MEAL PLANS:\n{daily_notes_context}\n\n"
                    routing_decisions.append(True)
                else:
                    routing_decisions.append(False)
            
            # Get new meal ideas context if needed
            if needs_new_meal_ideas:
                new_meal_ideas_context = self.get_new_meal_ideas_context()
                if new_meal_ideas_context:
                    context += f"NEW MEAL IDEAS:\n{new_meal_ideas_context}\n\n"
                    routing_decisions.append(True)
                else:
                    routing_decisions.append(False)
                    
            # Get in-stock meals context if needed
            if needs_instock_meals:
                instock_meals_context = self.get_instock_meals_context()
                if instock_meals_context:
                    context += f"MEALS YOU CAN MAKE NOW:\n{instock_meals_context}\n\n"
                    routing_decisions.append(True)
                else:
                    routing_decisions.append(False)
                    
            # Get ingredients information if needed
            if needs_ingredients_info:
                ingredients_info_context = self.get_ingredients_info_context()
                if ingredients_info_context:
                    context += f"INGREDIENTS INFORMATION:\n{ingredients_info_context}\n\n"
                    routing_decisions.append(True)
                else:
                    routing_decisions.append(False)
            
            print(f"[DEBUG] Pull router decisions: {routing_decisions}")
            return context
            
        except Exception as e:
            print(f"[ERROR] Pull router error parsing decision: {e}")
            routing_decisions.append(False)
            print(f"[DEBUG] Pull router decisions: {routing_decisions}")
            return ""
    
    def get_inventory_context(self):
        """Get inventory context using the shared database connection."""
        try:
            inventory_table = self.tables['inventory'] # Get Inventory object from dict
            current_items = inventory_table.read()
            if not current_items:
                return "The inventory is currently empty."
            
            context = ""
            for item in current_items:
                # Access by column name using self.db.conn.row_factory
                name = item['name']
                quantity = item['quantity']
                expiration = item['expiration'] or 'N/A' # Use string directly
                context += f"- {name}: {quantity} (Expires: {expiration})\n"
            return context
        except Exception as e:
            print(f"[ERROR] PullRouter failed to get inventory context: {e}")
            return "Error retrieving inventory."
    
    def get_taste_profile_context(self):
        """Get taste profile context using the shared database connection."""
        try:
            taste_profile_table = self.tables['taste_profile'] # Get TasteProfile object
            profile = taste_profile_table.read() # read() now returns the string or None
            if profile:
                return profile
            else:
                return "No taste profile set."
        except Exception as e:
            print(f"[ERROR] PullRouter failed to get taste profile context: {e}")
            return "Error retrieving taste profile."
            
    def get_saved_meals_context(self):
        """Get saved meals context using the shared database connection."""
        try:
            saved_meals_table = self.tables['saved_meals'] # Get SavedMeals object
            all_meals = saved_meals_table.read()
            if not all_meals:
                return "No saved meals found."
            
            context = ""
            for meal in all_meals:
                meal_id = meal['id']
                name = meal['name']
                prep_time = meal['prep_time_minutes']
                ingredients_json = meal['ingredients'] # Already a JSON string
                recipe = meal['recipe']
                
                # Shorten recipe for context if needed
                recipe_snippet = recipe[:100] + '...' if len(recipe) > 100 else recipe
                
                # Format ingredients string for context
                ingredients_str = "[See details]" # Keep context concise
                try:
                    ingredients_list = json.loads(ingredients_json) if isinstance(ingredients_json, str) else ingredients_json
                    if isinstance(ingredients_list, list):
                        ingredients_str = ", ".join([f"{ing.get('name', '?')}" for ing in ingredients_list])
                    else:
                        ingredients_str = str(ingredients_list)
                except (json.JSONDecodeError, TypeError):
                     ingredients_str = "[Error parsing ingredients]"

                context += f"ID: {meal_id}, Name: {name}, Prep: {prep_time}m, Ingredients: {ingredients_str}, Recipe: {recipe_snippet}\n"
            return context
        except Exception as e:
            print(f"[ERROR] PullRouter failed to get saved meals context: {e}")
            return "Error retrieving saved meals."
            
    def get_shopping_list_context(self):
        """Get shopping list context using the shared database connection."""
        try:
            shopping_list_table = self.tables['shopping_list']
            ingredients_table = self.tables['ingredients_foods']
            
            shopping_items = shopping_list_table.read()
            if not shopping_items:
                return "Shopping list is empty."
            
            # Get food names for IDs
            all_food_items = ingredients_table.read()
            food_dict = {item['id']: item['name'] for item in all_food_items} if all_food_items else {}
            
            context = ""
            for item in shopping_items:
                item_id = item['id']
                amount = item['amount']
                name = food_dict.get(item_id, f"Unknown (ID: {item_id})")
                amount_str = f"{amount:.2f}" if isinstance(amount, float) and amount % 1 != 0 else str(amount)
                context += f"- {name}: {amount_str}\n"
            return context
        except Exception as e:
            print(f"[ERROR] PullRouter failed to get shopping list context: {e}")
            return "Error retrieving shopping list."

    def get_daily_notes_context(self):
        """Get daily notes context for the upcoming week."""
        try:
            daily_planner_table = self.tables['daily_planner']
            saved_meals_table = self.tables['saved_meals']
            
            today = date.today()
            end_date = today + timedelta(days=7)
            
            all_entries = daily_planner_table.read() # Reads all, ordered by date
            if not all_entries:
                return "No meal plans found for the upcoming week."
                
            context = ""
            found_entries = False
            for entry in all_entries:
                entry_date_str = entry['day']
                try:
                    entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    continue # Skip invalid date format
                
                # Filter for the next 7 days
                if today <= entry_date <= end_date:
                    found_entries = True
                    notes = entry['notes'] or "No notes"
                    meal_ids_json = entry['meal_ids']
                    
                    meal_names = []
                    try:
                        meal_ids = json.loads(meal_ids_json) if meal_ids_json and isinstance(meal_ids_json, str) else []
                        if isinstance(meal_ids, list):
                             for mid in meal_ids:
                                try:
                                    meal_id_int = int(mid)
                                    meal_result = saved_meals_table.read(meal_id_int)
                                    if meal_result and meal_result[0]:
                                        meal_names.append(meal_result[0]['name'])
                                    else:
                                        meal_names.append(f"Unknown (ID:{meal_id_int})")
                                except (ValueError, TypeError):
                                     meal_names.append(f"Invalid ID ({mid})")
                        else:
                            meal_names.append("[Invalid meal data]")
                    except (json.JSONDecodeError, TypeError):
                        meal_names.append("[Error parsing meal data]")
                        
                    meal_text = ", ".join(meal_names) if meal_names else "No meals planned"
                    formatted_date = entry_date.strftime("%A, %B %d")
                    context += f"{formatted_date}: {meal_text} (Notes: {notes})\n"
            
            if not found_entries:
                 return "No meal plans found for the upcoming week."
                 
            return context.strip()
        except Exception as e:
            print(f"[ERROR] PullRouter failed to get daily notes context: {e}")
            print(traceback.format_exc()) # Print stack trace for debugging
            return "Error retrieving daily meal plans."

    def get_new_meal_ideas_context(self):
        """Get new meal ideas context using the shared database connection."""
        try:
            new_ideas_table = self.tables['new_meal_ideas']
            all_ideas = new_ideas_table.read()
            if not all_ideas:
                return "No new meal ideas found."
            
            context = ""
            for idea in all_ideas:
                idea_id = idea['id']
                name = idea['name']
                prep_time = idea['prep_time']
                # Keep context concise
                context += f"ID: {idea_id}, Name: {name}, Prep: {prep_time}m\n"
            return context
        except Exception as e:
            print(f"[ERROR] PullRouter failed to get new meal ideas context: {e}")
            return "Error retrieving new meal ideas."
            
    def get_instock_meals_context(self):
        """Get context about meals (saved and new) that can be made with current inventory."""
        try:
            saved_instock_table = self.tables['saved_meals_instock_ids']
            new_instock_table = self.tables['new_meal_ideas_instock_ids']
            saved_meals_table = self.tables['saved_meals']
            new_ideas_table = self.tables['new_meal_ideas']
            
            saved_ids = [row['id'] for row in saved_instock_table.read() or []]
            new_ids = [row['id'] for row in new_instock_table.read() or []]
            
            context = ""
            context += "Saved Meals You Can Make:\n"
            if saved_ids:
                 for meal_id in saved_ids:
                     meal_result = saved_meals_table.read(meal_id)
                     if meal_result and meal_result[0]:
                         name = meal_result[0]['name']
                         prep = meal_result[0]['prep_time_minutes']
                         context += f"- ID {meal_id}: {name} ({prep} mins)\n"
            else:
                 context += "(None)\n"
                 
            context += "\nNew Meal Ideas You Can Make:\n"
            if new_ids:
                 for idea_id in new_ids:
                     idea_result = new_ideas_table.read(idea_id)
                     if idea_result and idea_result[0]:
                         name = idea_result[0]['name']
                         prep = idea_result[0]['prep_time']
                         context += f"- ID {idea_id}: {name} ({prep} mins)\n"
            else:
                 context += "(None)\n"
                 
            return context.strip()
        except Exception as e:
            print(f"[ERROR] PullRouter failed to get in-stock meals context: {e}")
            return "Error retrieving in-stock meals."
            
    def get_ingredients_info_context(self):
        """Get ingredients information context using the shared database connection."""
        try:
            ingredients_table = self.tables['ingredients_foods']
            all_ingredients = ingredients_table.read()
            if not all_ingredients:
                return "No ingredients information available."
            
            context = ""
            for ingredient in all_ingredients:
                ing_id = ingredient['id']
                name = ingredient['name']
                min_buy = ingredient['min_amount_to_buy']
                link = ingredient['walmart_link']
                link_text = f" | Link: {link}" if link else ""
                context += f"ID: {ing_id}, Name: {name}, Min Buy: {min_buy}{link_text}\n"
            return context
        except Exception as e:
            print(f"[ERROR] PullRouter failed to get ingredients info context: {e}")
            return "Error retrieving ingredients information."
   