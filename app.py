# app.py

"""
app.py: This file orchestrates data flow and handles user input for the ChefByte application. 
It manages real-time tasks such as retrieving basic information from the database, performing updates, 
and handling meal suggestions. Additionally, it controls asynchronous background tasks for generating 
meal ideas and creating shopping lists.
"""

from langchain.schema import AIMessage, HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
from helpers.model_router import ModelRouter
from routers.pull_router import PullRouter
from routers.push_router import PushRouter
from routers.tool_router import ToolRouter

# Load environment variables
load_dotenv()

class ChefByteChat:
    def __init__(self, intelligence_level='low', use_local_resources=False):
        # Initialize the model router
        self.model_router = ModelRouter(intelligence_level, use_local_resources)
        self.model = self.model_router.get_model()
        
        # Create a separate model for internal routing (can use lower intelligence level)
        self.router_model = ModelRouter('medium', use_local_resources).get_model()
        
        # Initialize the pull router for context retrieval
        self.pull_router = PullRouter(self.router_model)
        
        # Initialize the push router for database updates
        self.push_router = PushRouter(self.router_model)
        
        # Initialize the tool router for activating tools like meal generation
        self.tool_router = ToolRouter(self.router_model)
        
        # Initialize system message with database capabilities explanation
        self.system_message = SystemMessage(content="""
You are ChefByte, a friendly cooking assistant with access to the user's refrigerator and pantry inventory. You are designed to help users find recipes, answer cooking questions, and manage their kitchen more effectively.

As a cooking assistant, you have several capabilities:
1. You can answer general cooking questions about techniques, substitutions, and tips.
2. You can suggest recipes based on ingredients the user has available.
3. You can explain cooking terms and methods.
4. You can convert measurements and calculate nutritional information.
5. You can help the user maintain their inventory by adding, removing, or updating items.

You can also help users manage their taste profile by:
- Adding likes or dislikes to their profile
- Setting dietary restrictions or allergies
- Making note of cuisine preferences
- Recording ingredient preferences or aversions

You can help users manage their saved meal recipes:
- Saving new recipes with ingredients, instructions, and prep time
- Updating existing recipes (changing ingredients, instructions, or prep time)
- Removing specific recipes or all recipes
- Viewing saved recipes

You can help users manage their shopping list:
- Adding items with quantities to the shopping list
- Updating quantities of items on the shopping list
- Removing specific items from the shopping list
- Clearing the entire shopping list
- Creating a new shopping list

You can help users plan meals for specific days:
- Adding meals to specific days (today, tomorrow, next Monday, etc.)
- Adding notes to daily meal plans
- Updating planned meals for specific days
- Viewing meal plans for the upcoming week
- Clearing plans for specific days
- Removing specific meals from a day's plan

You can suggest new recipe ideas to users:
- Recommending dishes based on their taste profile
- Suggesting seasonal or trending recipes
- Offering meal ideas that complement their current inventory
- Providing diverse cuisine options

You can tell users what meals they can make right now:
- Checking which saved recipes can be made with available ingredients
- Identifying new recipe ideas that match their current inventory
- Suggesting substitutions to make more recipes possible with current ingredients

You can provide information about ingredients:
- Details about minimum purchase quantities
- Where to buy specific ingredients (including Walmart links when available)
- Guidance on how much of an ingredient is needed for common recipes
- Information about ingredient shelf life and storage

When suggesting recipes, consider:
- Inventory: Focus on ingredients the user already has
- Taste profile: Avoid suggesting recipes with ingredients or cuisines the user dislikes
- Experience level: Match complexity to the user's cooking experience
- Time constraints: If mentioned, suggest recipes that fit the available time

If you see the user saying things like "I just bought some chicken" or "I used the last of the milk" or similar statements about their inventory, please make a note of that. Similarly, if you see the user saying they like or dislike certain foods, please make a note of that in their taste profile.

It's important to include notes about any changes made to inventory, recipes, shopping list, or meal plans in your responses to help the user understand what was updated.

First time users should be told about your inventory tracking capabilities and how they can update their inventory. You should encourage them to add items to their inventory and taste profile.
""")
        self.chat_history = [self.system_message]
    
    def process_message(self, user_input: str) -> str:
        """Process a user message and return the AI response"""
        # Add user message to history
        self.chat_history.append(HumanMessage(content=user_input))
        
        # Check if any tools need to be activated based on the user message
        tool_result = self.tool_router.route_tool(self.chat_history)
        
        # If a tool was activated, use its output directly
        if tool_result["tool_activated"]:
            tool_output = tool_result["tool_output"]
            tool_name = tool_result.get("tool_name", "tool")
            
            # Add tool response to chat history as an AI message
            self.chat_history.append(AIMessage(content=tool_output))
            
            print(f"[INFO] {tool_name} was activated and produced a response")
            return tool_output
            
        # If no tool was activated, proceed with normal context retrieval and response generation
        # Retrieve context using pull router
        context = self.pull_router.pull_context(self.chat_history)
        if context:
            print(f"Context retrieved from database: {len(context)} characters")
        else:
            print("No database context was needed for this query")
        
        # Create a temporary chat history with context for this specific response
        # The context is added as a system message so it's only visible to the model, not the user
        temp_history = [self.system_message]
        if context:
            temp_history.append(SystemMessage(content=context))
        
        # Add all user and AI messages from the original history
        for message in self.chat_history[1:]:  # Skip the first system message
            temp_history.append(message)
        
        # Check if any database updates need to be made based on the user's message
        updates_made, confirmation_message = self.push_router.push_updates(self.chat_history)
        
        # If updates were made, append a system message to inform the assistant
        if updates_made and confirmation_message:
            # Identify what type of update was made based on the confirmation message
            update_type = "database"
            if "INVENTORY" in confirmation_message:
                update_type = "inventory"
            elif "TASTE PROFILE" in confirmation_message:
                update_type = "taste profile"
            elif "SAVED MEAL" in confirmation_message:
                update_type = "saved meals"
            elif "SHOPPING LIST" in confirmation_message:
                update_type = "shopping list"
            elif "DAILY PLAN" in confirmation_message:
                update_type = "meal plan"
            
            update_notice = f"\n\nNOTE: {update_type.capitalize()} changes are being processed based on the user's request. A confirmation will be displayed after your response."
            temp_history.append(SystemMessage(content=update_notice))
            print(f"Database was updated based on user message: {update_type} changes")
        else:
            print("No database updates were needed")
        
        # Get response from model using the temporary history with context
        response = self.model.invoke(temp_history)
        
        # Add AI response to the original chat history
        self.chat_history.append(AIMessage(content=response.content))
        
        # Append confirmation message to the response if there were updates
        final_response = response.content
        if updates_made and confirmation_message:
            # Set the appropriate update type header for the confirmation
            update_header = "INVENTORY UPDATE CONFIRMATION"
            if "TASTE PROFILE" in confirmation_message:
                update_header = "TASTE PROFILE UPDATE CONFIRMATION"
            elif "SAVED MEAL" in confirmation_message:
                update_header = "SAVED MEALS UPDATE CONFIRMATION"
            elif "SHOPPING LIST" in confirmation_message:
                update_header = "SHOPPING LIST UPDATE CONFIRMATION"
            elif "DAILY PLAN" in confirmation_message:
                update_header = "MEAL PLAN UPDATE CONFIRMATION"
                
            final_response += f"\n\n--- {update_header} ---\n{confirmation_message}"
        
        return final_response
    
    def reset_conversation(self):
        """Reset the conversation history"""
        self.chat_history = [self.system_message]

    def set_intelligence_level(self, level):
        """Change the intelligence level of the model"""
        self.model_router.set_intelligence_level(level)
        self.model = self.model_router.get_model()
        
    def set_use_local_resources(self, use_local):
        """Toggle between local and API resources"""
        self.model_router.set_use_local_resources(use_local)
        self.model = self.model_router.get_model()


if __name__ == "__main__":
    # Create instance of ChefByte chat
    chef_chat = ChefByteChat()
    
    print("ChefByte Assistant (Press Ctrl+C to exit)")
    print("--------------------------------------------")
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                break
            
            if not user_input:
                continue
                
            response = chef_chat.process_message(user_input)
            print("\nChefByte:", response)
            
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")

