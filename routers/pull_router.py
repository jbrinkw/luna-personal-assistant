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
    def __init__(self, router_model):
        self.router_model = router_model
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
        """Retrieve the current inventory from the database"""
        try:
            # Initialize database connection
            db = Database()
            inventory = Inventory(db)
            
            # Get all inventory items
            items = inventory.read()
            
            # Format inventory items for context
            if not items:
                inventory_context = "The inventory is currently empty."
            else:
                inventory_lines = []
                for item in items:
                    # Format: Name | Quantity | Expiration (if any)
                    expiration = item[3].strftime("%Y-%m-%d") if item[3] else "N/A"
                    inventory_lines.append(f"{item[1]} | {item[2]} | Expires: {expiration}")
                
                inventory_context = "\n".join(inventory_lines)
                
            db.disconnect()
            return inventory_context
            
        except Exception as e:
            print(f"[ERROR] Pull router error retrieving inventory: {e}")
            return "Error retrieving inventory information."
    
    def get_taste_profile_context(self):
        """Retrieve the taste profile from the database"""
        try:
            # Initialize database connection
            db = Database()
            taste_profile = TasteProfile(db)
            
            # Get taste profile
            profiles = taste_profile.read()
            
            # Format taste profile for context
            if not profiles or len(profiles) == 0:
                taste_profile_context = "No taste profile has been set."
            else:
                # Use the profile text directly
                taste_profile_context = profiles[0][0]
                
            db.disconnect()
            return taste_profile_context
            
        except Exception as e:
            print(f"[ERROR] Pull router error retrieving taste profile: {e}")
            return "Error retrieving taste profile information."
            
    def get_saved_meals_context(self):
        """Retrieve saved meals from the database"""
        try:
            # Initialize database connection
            db = Database()
            saved_meals = SavedMeals(db)
            
            # Get all saved meals
            meals = saved_meals.read()
            
            if not meals:
                return "You don't have any saved meals yet."
            
            # Simply return the meals data directly
            meals_data = []
            for meal in meals:
                meals_data.append({
                    "id": meal[0],
                    "name": meal[1],
                    "prep_time": meal[2],
                    "ingredients": meal[3],
                    "recipe": meal[4]
                })
            
            # Format as simple string
            meals_text = "\n".join([
                f"ID: {m['id']}, Name: {m['name']}, Prep Time: {m['prep_time']} minutes"
                for m in meals_data
            ])
            
            db.disconnect()
            return meals_text
            
        except Exception as e:
            print(f"[ERROR] Pull router error retrieving saved meals: {e}")
            return "Error retrieving saved meals information."
            
    def get_shopping_list_context(self):
        """Retrieve the shopping list from the database"""
        try:
            # Initialize database connection
            db = Database()
            shopping_list = ShoppingList(db)
            ingredients_food = IngredientsFood(db)
            
            # Get all shopping list items
            items = shopping_list.read()
            
            # Format shopping list items for context
            if not items:
                return "Your shopping list is currently empty."
            
            # Get all food items for lookup
            food_items = ingredients_food.read()
            food_dict = {item[0]: item[1] for item in food_items} if food_items else {}
            
            # Simply return the data as is
            shopping_items = []
            for item in items:
                item_id = item[0]
                amount = item[1]
                name = food_dict.get(item_id, f"Unknown item (ID: {item_id})")
                shopping_items.append(f"ID: {item_id}, Name: {name}, Amount: {amount}")
            
            db.disconnect()
            return "\n".join(shopping_items)
            
        except Exception as e:
            print(f"[ERROR] Pull router error retrieving shopping list: {e}")
            return "Error retrieving shopping list information."

    def get_daily_notes_context(self):
        """Retrieve daily planner notes for a 2-week window (past week and upcoming week)"""
        try:
            # Initialize database connection
            db = Database()
            daily_planner = DailyPlanner(db)
            saved_meals = SavedMeals(db)
            new_meal_ideas = NewMealIdeas(db)
            
            # Calculate date range (today +/- 7 days)
            today = date.today()
            start_date = today - timedelta(days=7)
            end_date = today + timedelta(days=7)
            
            # Get all daily planner entries
            all_entries = daily_planner.read()
            
            # Format daily planner entries for the date range
            if not all_entries:
                db.disconnect()
                return "No meal plans have been set for any days."
            
            # Get saved meals AND new meal ideas for reference (meal ID lookup)
            all_saved_meals = saved_meals.read()
            all_new_ideas = new_meal_ideas.read()
            
            # Combine into one dictionary for lookup
            meals_dict = {}
            if all_saved_meals:
                meals_dict.update({meal[0]: meal[1] for meal in all_saved_meals})
            if all_new_ideas:
                meals_dict.update({meal[0]: meal[1] for meal in all_new_ideas})
            
            # Filter entries within our date range and sort by date
            filtered_entries = []
            for entry in all_entries:
                entry_date = entry[0]
                if start_date <= entry_date <= end_date:
                    filtered_entries.append(entry)
            
            # Sort entries by date
            filtered_entries.sort(key=lambda x: x[0])
            
            if not filtered_entries:
                db.disconnect()
                return f"No meal plans found between {start_date} and {end_date}."
            
            # Format entries
            planner_items = []
            for entry in filtered_entries:
                entry_date = entry[0]
                notes = entry[1] or "No notes"
                
                # Format date nicely with day of week
                formatted_date = entry_date.strftime("%A, %B %d, %Y")
                
                # Handle meal IDs if present
                meal_ids_json = entry[2]
                meal_text = "No meals planned"
                
                if meal_ids_json:
                    try:
                        # Handle if meal_ids_json is already a list or needs parsing
                        if isinstance(meal_ids_json, list):
                             meal_ids = meal_ids_json
                        elif isinstance(meal_ids_json, str):
                             meal_ids = json.loads(meal_ids_json or '[]')
                        else:
                             meal_ids = []
                             
                        meal_names = []
                        if isinstance(meal_ids, list):
                            for meal_id in meal_ids:
                                # Use the combined meals_dict for lookup
                                meal_name = meals_dict.get(meal_id, f"Unknown meal (ID: {meal_id})") 
                                meal_names.append(meal_name)
                            
                            if meal_names:
                                meal_text = ", ".join(meal_names)
                        else:
                             meal_text = "Error: Meal IDs not a list"
                             
                    except json.JSONDecodeError:
                        meal_text = "Error parsing meals JSON"
                    except Exception as e:
                        print(f"[ERROR] Unexpected error processing meal IDs for {entry_date}: {e}")
                        meal_text = "Error processing meals"
                
                # Mark today's entry
                date_prefix = "TODAY: " if entry_date == today else ""
                
                planner_items.append(f"{date_prefix}{formatted_date}\nMeals: {meal_text}\nNotes: {notes}")
            
            db.disconnect()
            return "\n\n".join(planner_items)
            
        except Exception as e:
            print(f"[ERROR] Pull router error retrieving daily notes: {e}")
            # Ensure disconnection on error too
            if 'db' in locals() and db.conn:
                db.disconnect()
            return "Error retrieving daily planner information."
    
    def get_new_meal_ideas_context(self):
        """Retrieve new meal ideas from the database"""
        try:
            # Initialize database connection
            db = Database()
            new_meal_ideas = NewMealIdeas(db)
            
            # Get all new meal ideas
            meals = new_meal_ideas.read()
            
            if not meals:
                return "You don't have any suggested meal ideas yet."
            
            # Format meal ideas data
            meals_data = []
            for meal in meals:
                meals_data.append({
                    "id": meal[0],
                    "name": meal[1],
                    "prep_time": meal[2],
                    "ingredients": meal[3],
                    "recipe": meal[4]
                })
            
            # Format as simple string
            meals_text = "\n".join([
                f"ID: {m['id']}, Name: {m['name']}, Prep Time: {m['prep_time']} minutes"
                for m in meals_data
            ])
            
            db.disconnect()
            return meals_text
            
        except Exception as e:
            print(f"[ERROR] Pull router error retrieving new meal ideas: {e}")
            return "Error retrieving new meal ideas information."
    
    def get_instock_meals_context(self):
        """Retrieve meals that can be made with current ingredients"""
        try:
            # Initialize database connection
            db = Database()
            saved_meals_instock = SavedMealsInStockIds(db)
            new_meals_instock = NewMealIdeasInStockIds(db)
            saved_meals = SavedMeals(db)
            new_meal_ideas = NewMealIdeas(db)
            
            # Get all in-stock meal IDs
            saved_instock_ids = [item[0] for item in saved_meals_instock.read()] if saved_meals_instock.read() else []
            new_instock_ids = [item[0] for item in new_meals_instock.read()] if new_meals_instock.read() else []
            
            if not saved_instock_ids and not new_instock_ids:
                return "There are no meals you can make with your current ingredients."
            
            # Get meal details for in-stock meals
            instock_meals_text = []
            
            # Get saved meals that are in stock
            if saved_instock_ids:
                instock_meals_text.append("SAVED MEALS YOU CAN MAKE:")
                for meal_id in saved_instock_ids:
                    meal = saved_meals.read(meal_id)
                    if meal and meal[0]:
                        instock_meals_text.append(f"ID: {meal[0][0]}, Name: {meal[0][1]}, Prep Time: {meal[0][2]} minutes")
            
            # Get new meal ideas that are in stock
            if new_instock_ids:
                if instock_meals_text:  # Add separator if we already have saved meals
                    instock_meals_text.append("")
                instock_meals_text.append("NEW MEAL IDEAS YOU CAN MAKE:")
                for meal_id in new_instock_ids:
                    meal = new_meal_ideas.read(meal_id)
                    if meal and meal[0]:
                        instock_meals_text.append(f"ID: {meal[0][0]}, Name: {meal[0][1]}, Prep Time: {meal[0][2]} minutes")
            
            db.disconnect()
            return "\n".join(instock_meals_text)
            
        except Exception as e:
            print(f"[ERROR] Pull router error retrieving in-stock meals: {e}")
            return "Error retrieving information about meals you can make now."
    
    def get_ingredients_info_context(self):
        """Retrieve ingredients information from the database"""
        try:
            # Initialize database connection
            db = Database()
            ingredients = IngredientsFood(db)
            
            # Get all ingredients
            items = ingredients.read()
            
            if not items:
                return "No ingredients information is available."
            
            # Format ingredients for context
            ingredients_text = []
            for item in items:
                item_id = item[0]
                name = item[1]
                min_amount = item[2]
                walmart_link = item[3] if item[3] else "No link available"
                
                ingredients_text.append(f"ID: {item_id}, Name: {name}")
                ingredients_text.append(f"  Minimum Purchase: {min_amount}")
                ingredients_text.append(f"  Purchase Link: {walmart_link}")
            
            db.disconnect()
            return "\n".join(ingredients_text)
            
        except Exception as e:
            print(f"[ERROR] Pull router error retrieving ingredients info: {e}")
            return "Error retrieving ingredients information."
   