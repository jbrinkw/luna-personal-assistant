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
from tools.new_meal_ideation import generate_meal_ideas
from tools.meal_planner import handle_meal_planning_request
from tools.meal_suggestion_gen import generate_meal_suggestions

# Load environment variables
load_dotenv()

class ToolRouterDecision(BaseModel):
    needs_meal_generation: bool = Field(False, description="Whether general meal generation/recipe suggestion is needed")
    needs_meal_planning: bool = Field(False, description="Whether structured meal planning (intent generation or meal selection) is needed")
    needs_meal_suggestion: bool = Field(False, description="Whether meal suggestion filtering based on user preferences is needed")

class ToolRouter:
    def __init__(self, router_model):
        self.router_model = router_model
        self.output_parser = PydanticOutputParser(pydantic_object=ToolRouterDecision)
        self.format_instructions = self.output_parser.get_format_instructions()
        
        # Router prompt template - updated to include meal suggestions
        self.router_prompt_template = """\
Analyze the most recent user message and conversation context to determine if it requires:
1. Meal generation/recipe suggestions (needs_meal_generation)
2. Structured meal planning (needs_meal_planning) - generating intents or selecting meals based on prior intents
3. Meal suggestions based on preferences (needs_meal_suggestion)

Meal Generation/Recipe Suggestions Examples (needs_meal_generation=True):
- "What should I cook tonight?"
- "I need some meal ideas"
- "Suggest some recipes I can make"
- "What meals can I make with what I have?"
- "I want to try a new dish"
- "Give me some dinner options"
- User selecting options from a previously generated list of meal *descriptions* or *recipes* (not intents)

Structured Meal Planning Examples (needs_meal_planning=True):
- "Let's meal plan for next week"
- "I want to start meal planning"
- "Plan meals for the next 3 days"
- "Change my meal plan for tomorrow to be quick and easy"
- User interacting after being shown *meal intents* (e.g., "Breakfast: quick and easy")
- "Select meals based on these intents"
- "Proceed with selecting actual meals"

Meal Suggestion Examples (needs_meal_suggestion=True):
- "Suggest meals based on my preferences"
- "What meals would I like?"
- "Give me 5 meal suggestions"
- "What meals can I make with my current inventory?"
- "What are my best meal options?"
- "Show me meals that match my taste"
- "I'm looking for quick dinner ideas"

CRITICAL DISTINCTIONS:
- Meal Generation creates new recipe ideas from scratch → needs_meal_generation = True
- Meal Planning creates a structured plan with intents for specific days → needs_meal_planning = True  
- Meal Suggestion filters existing meals based on preferences → needs_meal_suggestion = True

It is possible for all to be false if the user is just chatting or asking a general question.

Return your decision as a JSON object following this schema:
{format_instructions}

User message history:
{message_history}

Most recent user message: 
{message}
"""

    def route_tool(self, message_history: List) -> Dict[str, Any]:
        """
        Routes user input to appropriate tools based on the latest message.
        Returns a dictionary with tool results or empty if no tools needed.
        """
        # For tracking routing decisions (for debugging)
        routing_decisions = []
        
        # Get the most recent user message
        if not message_history:
            return {"tool_activated": False, "tool_output": ""}
            
        # Find the most recent user message
        user_messages = [msg for msg in message_history if isinstance(msg, HumanMessage)]
        if not user_messages:
            return {"tool_activated": False, "tool_output": ""}
            
        recent_user_message = user_messages[-1].content
        
        # Format message history for the prompt
        history_text = ""
        for i, message in enumerate(message_history[-5:]):  # Only use last 5 messages for context
            role = "User" if isinstance(message, HumanMessage) else "Assistant"
            history_text += f"{role}: {message.content}\n"
        
        # Create the routing decision using the prompt template
        prompt = ChatPromptTemplate.from_template(template=self.router_prompt_template)
        messages = prompt.format_messages(
            message=recent_user_message,
            message_history=history_text,
            format_instructions=self.format_instructions
        )
        
        response = self.router_model.invoke(messages)
        
        try:
            # Parse the decision
            decision = self.output_parser.parse(response.content)
            needs_meal_generation = decision.needs_meal_generation
            needs_meal_planning = decision.needs_meal_planning
            needs_meal_suggestion = decision.needs_meal_suggestion
            
            # Add to routing decisions for tracking
            routing_decisions.append({
                "meal_generation": needs_meal_generation, 
                "meal_planning": needs_meal_planning,
                "meal_suggestion": needs_meal_suggestion
            })
            print(f"[DEBUG] Tool router decisions: {routing_decisions}")
            
            # --- Tool Activation Logic ---
            # Prioritize meal planning if detected
            if needs_meal_planning:
                print("[INFO] Activating structured meal planning tool")
                # Pass the full message history to the meal planner
                meal_plan_response = handle_meal_planning_request(message_history)
                return {
                    "tool_activated": True,
                    "tool_name": "meal_planning",
                    "tool_output": meal_plan_response 
                }
            
            # Handle meal suggestion if needed
            elif needs_meal_suggestion:
                print("[INFO] Activating meal suggestion tool")
                meal_suggestion_response = generate_meal_suggestions(message_history)
                return {
                    "tool_activated": True,
                    "tool_name": "meal_suggestion",
                    "tool_output": meal_suggestion_response
                }

            # Handle meal generation/recipe suggestions if needed (and not meal planning)
            elif needs_meal_generation:
                print("[INFO] Activating meal generation/recipe suggestion tool")
                meal_content = generate_meal_ideas(message_history)
                return {
                    "tool_activated": True,
                    "tool_name": "meal_generation",
                    "tool_output": meal_content
                }
            
            # No tools needed
            return {"tool_activated": False, "tool_output": ""}
            
        except Exception as e:
            print(f"[ERROR] Tool router error: {e}")
            return {"tool_activated": False, "tool_output": ""}
