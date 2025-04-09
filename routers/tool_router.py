# tool_router.py

"""
tool_router.py

This router handles the routing of user input to the appropriate tools based on the requirements of the response. 
It operates immediately after user input is received and determines whether to use synchronous or asynchronous tools. 
The outputs are directed to the response context or message queue as needed.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union, Tuple
import traceback

# Corrected imports based on actual filenames and identified entry points
from tools.meal_suggestion_gen import generate_meal_suggestions # Function
from tools.meal_planner import MealPlanningTool # Class
from tools.new_meal_ideation import MealIdeationEngine # Class
# from tools.shopping_list_gen import ShoppingListGeneratorTool # Assumed class - File seems incomplete

from db.db_functions import Database # Keep for type hinting

# Load environment variables
load_dotenv()

# Router decision model (can likely be simplified if LLM just returns tool name)
class ToolRouterDecision(BaseModel):
    needs_meal_suggestion: bool = Field(False, description="Whether the user wants meal suggestions")
    needs_meal_planning: bool = Field(False, description="Whether the user wants structured meal planning")
    needs_shopping_list_generation: bool = Field(False, description="Whether the user wants a shopping list generated")
    needs_recipe_generation: bool = Field(False, description="Whether the user wants new recipe ideas generated")

class ToolRouter:
    def __init__(self, router_model, db: Database, tables: dict):
        """Initialize ToolRouter with the router model and shared DB objects."""
        self.router_model = router_model
        self.db = db 
        self.tables = tables
        
        print("Initializing Tools...")
        # Initialize tools, passing db/tables ONLY to classes that require them
        # Store functions directly, instantiate classes
        self.meal_suggestion_func = generate_meal_suggestions
        self.meal_planning_instance = MealPlanningTool(db, tables)
        # self.shopping_list_instance = ShoppingListGeneratorTool(db, tables) # Commented out - needs implementation
        # MealIdeationEngine needs db/tables - assumes it will be refactored to accept them
        self.recipe_generator_instance = MealIdeationEngine(db, tables)
        print("Tools Initialized.")
        
        self.tools = {
            "meal_suggestion": self.meal_suggestion_func,
            "meal_planning": self.meal_planning_instance,
            # "shopping_list_generator": self.shopping_list_instance, # Commented out
            "recipe_generator": self.recipe_generator_instance,
        }
        
        # Router prompt template - Consider simplifying this to just output the tool name
        self.router_prompt_template = """
Based on the latest user query in the conversation history, which specialized tool is most appropriate?

Available Tools:
- meal_suggestion: Use ONLY if the user explicitly asks for meal recommendations, or suggestions (e.g., 'what can I make?', 'suggest some recipes', 'any ideas for dinner?').
- meal_planning: Use ONLY if the user explicitly asks to plan meals for specific dates or periods (e.g., 'plan my week', 'what should I eat Monday?', 'add X to Tuesday plan').
- recipe_generator: Use ONLY if the user explicitly asks to generate a *new* recipe or concept (e.g., 'create a recipe for X', 'invent a dish using Y').
# - shopping_list_generator: Use ONLY if the user explicitly asks to create, modify, or view their shopping list. # Temporarily comment out
- none: Use for ALL other cases, including: general conversation, simple questions, statements about inventory changes (e.g., 'I bought X', 'I used Y'), requests to view data (e.g., 'show my inventory'), or if no other tool is explicitly requested.

Conversation History (Last 5 messages):
{message_history}

Latest User Query: {query}

**IMPORTANT**: Prioritize 'none' unless the user's request *clearly and directly* matches the specific function of another tool. Do not activate a tool based on keywords alone if the user is just making a statement or asking a general question.

Respond with ONLY the name of the single most appropriate tool from the list above (meal_suggestion, meal_planning, recipe_generator, none).
Tool Selection:"""

    def route_tool(self, chat_history):
        """
        Routes the user query to the appropriate tool based on the conversation history.
        Returns a dictionary indicating if a tool was activated and its output.
        """
        if not chat_history:
             return {"tool_activated": False, "tool_output": ""}
             
        user_messages = [msg for msg in chat_history if isinstance(msg, HumanMessage)]
        if not user_messages:
             return {"tool_activated": False, "tool_output": ""}
             
        recent_user_message = user_messages[-1].content
        
        # Format message history for the prompt
        history_text = "\n".join([
            f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
            for msg in chat_history[-5:] # Use last 5 messages
        ])
        
        # Format the prompt
        prompt = self.router_prompt_template.format(message_history=history_text, query=recent_user_message)
        messages = [HumanMessage(content=prompt)]
        
        # Use the router model to decide which tool to use
        response = self.router_model.invoke(messages)
        # Decision is expected to be just the tool name now
        decision = response.content.strip().lower()
        # Basic validation, remove potential quotes or formatting
        decision = decision.replace("'", "").replace("\"", "").replace("`", "").split(":")[-1].strip()
        
        print(f"[DEBUG] Tool router decision: '{decision}'")
        
        # Get the selected tool (function or instance) from the dictionary
        selected_tool_object = self.tools.get(decision)
        tool_name = decision if selected_tool_object else "none"

        if selected_tool_object and tool_name != "none":
            print(f"[INFO] Activating tool: {tool_name}")
            try:
                tool_output = ""
                # Check if the retrieved object is a function or a class instance
                # Need to import types for isinstance check
                import types 
                if isinstance(selected_tool_object, types.FunctionType):
                    # Call the function (generate_meal_suggestions)
                    # Assuming it takes chat_history as input
                    tool_output = selected_tool_object(chat_history)
                elif hasattr(selected_tool_object, 'execute'):
                    # Call the execute method on the instance (MealPlanningTool, MealIdeationEngine)
                    # Assuming execute takes chat_history
                    # TODO: Verify execute method signature for each tool class
                    tool_output = selected_tool_object.execute(chat_history)
                else:
                     print(f"[WARN] Selected tool object '{tool_name}' is neither a known function nor has an execute method.")
                     return {"tool_activated": False, "tool_output": ""}

                return {"tool_activated": True, "tool_name": tool_name, "tool_output": tool_output}
            except Exception as e:
                print(f"[ERROR] Error executing tool '{tool_name}': {e}")
                print(traceback.format_exc())
                # Provide a user-friendly error message
                error_msg = f"Sorry, I encountered an error while trying to run the {tool_name.replace('_', ' ')} tool. Please try again later or ask differently."
                return {"tool_activated": True, "tool_name": tool_name, "tool_output": error_msg} # Return error as output
        else:
            # No tool matched or decision was 'none'
            print(f"[INFO] No specialized tool activated for decision: '{decision}'")
            return {"tool_activated": False, "tool_output": ""}
