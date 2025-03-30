# push_router.py

"""
This router runs after a response is generated and pushes updates to the database if necessary.
"""

import os
from typing import Tuple
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from db.db_functions import Database
from routers.push_helpers.inventory_processor import NaturalLanguageInventoryProcessor
from routers.push_helpers.taste_profile_processor import TasteProfileProcessor
from routers.push_helpers.saved_meals_processor import SavedMealsProcessor
from routers.push_helpers.shopping_list_processor import ShoppingListProcessor
from routers.push_helpers.daily_notes_processor import DailyNotesProcessor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PushRouter:
    def __init__(self, router_model):
        self.router_model = router_model
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Initialize inventory processor with simpler model
        self.inventory_processor = NaturalLanguageInventoryProcessor()
        
        # Initialize taste profile processor
        self.taste_profile_processor = TasteProfileProcessor()
        
        # Initialize saved meals processor
        self.saved_meals_processor = SavedMealsProcessor()
        
        # Initialize shopping list processor
        self.shopping_list_processor = ShoppingListProcessor()
        
        # Initialize daily notes processor
        self.daily_notes_processor = DailyNotesProcessor()
        
        # High-level routing prompt
        self.router_prompt = """
You are a router that determines if a user message requires database updates. 
Analyze the most recent user message and determine if it's requesting inventory changes, taste profile updates, saved meals changes, shopping list changes, or daily plan changes.

Examples of inventory changes:
- Adding items: "Add milk, eggs, and bread to my inventory"
- Updating items: "Update the quantity of apples to 5"
- Deleting items: "Remove the expired chicken from inventory"
- Inventory changes: "I just bought some vegetables"
- Stock tracking: "I used up all the flour"

Examples of taste profile updates:
- Adding preferences: "Add that I like spicy food to my taste profile"
- Removing preferences: "I actually don't like mushrooms"
- Dietary restrictions: "I need to avoid dairy products"
- Food allergies: "Add that I'm allergic to peanuts"
- Updating preferences: "Update my taste profile to include that I prefer whole grain bread"

Examples of saved meals changes:
- Adding recipes: "Save this spaghetti carbonara recipe"
- Creating meals: "Add a new recipe for chocolate cake"
- Updating recipes: "Update the chicken curry recipe to use less spice"
- Modifying prep time: "Change the prep time for lasagna to 45 minutes"
- Deleting recipes: "Remove the pizza recipe from my saved meals"
- Adding ingredients: "Add garlic to my tomato sauce recipe"

Examples of shopping list changes:
- Adding items: "Add milk and eggs to my shopping list"
- Updating quantities: "Change the amount of apples to 5 on my shopping list"
- Removing items: "Remove bread from my shopping list"
- Clearing the list: "Clear my shopping list"
- New shopping list: "I need to buy chicken, rice, and vegetables"

Examples of daily plan changes:
- Adding meals to days: "Add spaghetti to my meal plan for tomorrow"
- Setting a plan: "I want to cook lasagna on Friday"
- Updating plans: "Change my Tuesday dinner to chicken curry"
- Adding notes: "Add a note to my Saturday plan to buy fresh ingredients"
- Clearing plans: "Clear my meal plan for next Monday"
- Removing meals: "Remove lasagna from my Friday plan"

Return one of:
- "inventory" if the message involves inventory changes
- "taste_profile" if the message involves taste profile updates
- "saved_meals" if the message involves saved meals changes
- "shopping_list" if the message involves shopping list changes
- "daily_notes" if the message involves daily meal plan changes
- "none" if no database updates are needed

Most recent user message: {message}
"""

    def push_updates(self, chat_history) -> Tuple[bool, str]:
        """
        Main function to determine if updates to the database are needed based on the chat history.
        Returns a tuple of (bool, str): 
        - bool: True if updates were made, False otherwise
        - str: Confirmation message with details of changes made, or empty string if no changes
        """
        # For tracking routing decisions (for debugging)
        routing_decisions = []
        
        # Get the most recent user message
        if not chat_history:
            routing_decisions.append(False)
            print(f"[DEBUG] Push router decisions: {routing_decisions}")
            return False, ""
            
        # Find the most recent user message
        user_messages = [msg for msg in chat_history if isinstance(msg, HumanMessage)]
        if not user_messages:
            routing_decisions.append(False)
            print(f"[DEBUG] Push router decisions: {routing_decisions}")
            return False, ""
            
        recent_user_message = user_messages[-1].content
        
        # Use the routing model to decide if this message requires database updates
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=self.router_prompt.format(message=recent_user_message))
        ]
        
        response = self.router_model.invoke(messages)
        response_text = response.content.strip().lower()
        
        # Check what type of update is needed
        needs_inventory_update = "inventory" in response_text
        needs_taste_profile_update = "taste_profile" in response_text
        needs_saved_meals_update = "saved_meals" in response_text
        needs_shopping_list_update = "shopping_list" in response_text
        needs_daily_notes_update = "daily_notes" in response_text
        
        routing_decisions.append(f"inventory: {needs_inventory_update}, taste_profile: {needs_taste_profile_update}, saved_meals: {needs_saved_meals_update}, shopping_list: {needs_shopping_list_update}, daily_notes: {needs_daily_notes_update}")
        
        # Handle inventory updates
        if needs_inventory_update:
            result, confirmation = self.handle_inventory_update(recent_user_message, chat_history)
            routing_decisions.append(result)
            print(f"[DEBUG] Push router decisions: {routing_decisions}")
            return result, confirmation
        
        # Handle taste profile updates
        elif needs_taste_profile_update:
            result, confirmation = self.handle_taste_profile_update(recent_user_message, chat_history)
            routing_decisions.append(result)
            print(f"[DEBUG] Push router decisions: {routing_decisions}")
            return result, confirmation
            
        # Handle saved meals updates
        elif needs_saved_meals_update:
            result, confirmation = self.handle_saved_meals_update(recent_user_message, chat_history)
            routing_decisions.append(result)
            print(f"[DEBUG] Push router decisions: {routing_decisions}")
            return result, confirmation
        
        # Handle shopping list updates
        elif needs_shopping_list_update:
            result, confirmation = self.handle_shopping_list_update(recent_user_message, chat_history)
            routing_decisions.append(result)
            print(f"[DEBUG] Push router decisions: {routing_decisions}")
            return result, confirmation
            
        # Handle daily notes updates
        elif needs_daily_notes_update:
            result, confirmation = self.handle_daily_notes_update(recent_user_message, chat_history)
            routing_decisions.append(result)
            print(f"[DEBUG] Push router decisions: {routing_decisions}")
            return result, confirmation
        
        # No updates needed
        print(f"[DEBUG] Push router decisions: {routing_decisions}")
        return False, ""

    def handle_inventory_update(self, user_message, chat_history) -> Tuple[bool, str]:
        """
        Processes inventory updates based on the user message.
        Returns a tuple of (bool, str):
        - bool: True if updates were made, False otherwise
        - str: Confirmation message with details of changes made
        """
        try:
            # Process the user message using the inventory processor
            result, confirmation = self.inventory_processor.process_inventory_changes(user_message)
            return result, confirmation
        except Exception as e:
            print(f"[ERROR] Push router error processing inventory update: {e}")
            return False, ""

    def handle_taste_profile_update(self, user_message, chat_history) -> Tuple[bool, str]:
        """
        Processes taste profile updates based on the user message.
        Returns a tuple of (bool, str):
        - bool: True if updates were made, False otherwise
        - str: Confirmation message with details of changes made
        """
        try:
            # Process the user message using the taste profile processor
            result, confirmation = self.taste_profile_processor.update_taste_profile(user_message)
            return result, confirmation
        except Exception as e:
            print(f"[ERROR] Push router error processing taste profile update: {e}")
            return False, ""
            
    def handle_saved_meals_update(self, user_message, chat_history) -> Tuple[bool, str]:
        """
        Processes saved meals updates based on the user message.
        Returns a tuple of (bool, str):
        - bool: True if updates were made, False otherwise
        - str: Confirmation message with details of changes made
        """
        try:
            # Process the user message using the saved meals processor
            result, confirmation = self.saved_meals_processor.process_saved_meals_changes(user_message)
            return result, confirmation
        except Exception as e:
            print(f"[ERROR] Push router error processing saved meals update: {e}")
            return False, ""
            
    def handle_shopping_list_update(self, user_message, chat_history) -> Tuple[bool, str]:
        """
        Processes shopping list updates based on the user message.
        Returns a tuple of (bool, str):
        - bool: True if updates were made, False otherwise
        - str: Confirmation message with details of changes made
        """
        try:
            # Process the user message using the shopping list processor
            result, confirmation = self.shopping_list_processor.process_shopping_list_changes(user_message)
            return result, confirmation
        except Exception as e:
            print(f"[ERROR] Push router error processing shopping list update: {e}")
            return False, ""
            
    def handle_daily_notes_update(self, user_message, chat_history) -> Tuple[bool, str]:
        """
        Processes daily plan updates based on the user message.
        Returns a tuple of (bool, str):
        - bool: True if updates were made, False otherwise
        - str: Confirmation message with details of changes made
        """
        try:
            # Process the user message using the daily notes processor
            result, confirmation = self.daily_notes_processor.process_daily_notes_changes(user_message)
            return result, confirmation
        except Exception as e:
            print(f"[ERROR] Push router error processing daily notes update: {e}")
            return False, ""
