# tools/meal_suggestion_gen.py

"""
This tool handles meal suggestion requests by:
1. Using the existing meal_suggestion_context_builder to generate context
2. Filtering the suggestions to return the best matches
3. Formatting the results for display

It uses pydantic output parsing to return a list of meal IDs that best match the user's request.
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
from typing import List, Optional, Dict, Any, Union
from helpers.meal_suggestion_context_builder import MealSuggestionContextBuilder

# Load environment variables
load_dotenv()

class MealSuggestionResult(BaseModel):
    """Model for meal suggestion filtering results"""
    meal_ids: List[int] = Field(..., description="List of meal IDs to suggest to the user")
    explanation: Optional[str] = Field(None, description="Optional explanation of why these meals were chosen")

class MealSuggestionFilter:
    """Filters meal suggestions based on user intent and context"""
    def __init__(self, llm_model="gpt-4o-mini"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        self.output_parser = PydanticOutputParser(pydantic_object=MealSuggestionResult)
        
        # Filter prompt template
        self.filter_prompt = """
You are a meal suggestion assistant tasked with choosing the most relevant meals based on user intent.

CONTEXT: The following meals have been pre-filtered to match basic user preferences:
{meal_context}

USER INTENT: {user_intent}

Your task is to select the meal IDs that best match the user's intent. 
Default to choosing 3 meals if the user doesn't specify a quantity.
If the user asks for a specific number, adjust accordingly.
If the user has specific criteria like "quick meals" or "vegetarian options", prioritize those.

Return only the meal IDs as a JSON array.

{format_instructions}
"""

    def filter_suggestions(self, user_intent: str, meal_context: str) -> List[int]:
        """Filter meal suggestions based on user intent and context"""
        format_instructions = self.output_parser.get_format_instructions()
        
        prompt = ChatPromptTemplate.from_template(self.filter_prompt)
        formatted_prompt = prompt.format(
            meal_context=meal_context,
            user_intent=user_intent,
            format_instructions=format_instructions
        )
        
        try:
            response = self.chat.invoke(formatted_prompt)
            result = self.output_parser.parse(response.content)
            return result.meal_ids
        except Exception as e:
            print(f"Error filtering meal suggestions: {str(e)}")
            # Extract meal IDs manually if parsing fails
            try:
                # Look for meal IDs in the context
                import re
                meal_ids = []
                for line in meal_context.split("\n"):
                    if "Meal ID:" in line:
                        id_match = re.search(r"Meal ID: (\d+)", line)
                        if id_match:
                            meal_ids.append(int(id_match.group(1)))
                # Return up to 3 meal IDs
                return meal_ids[:3]
            except:
                # If all else fails, return empty list
                return []

class MealSuggestionFormatter:
    """Formats meal suggestions for display"""
    def __init__(self):
        # Initialize db connection silently
        self.db, self.tables = init_tables(verbose=False) 
        
    def format_meal_suggestions(self, meal_ids: List[int]) -> str:
        """Format meal suggestions for display"""
        if not meal_ids:
            return "I couldn't find any meal suggestions that match your request. Could you provide more details about what you're looking for?"
        
        output = "Here are some meal suggestions that might interest you:\n\n"
        
        for i, meal_id in enumerate(meal_ids, 1):
            # Try to find the meal in saved_meals first
            meal_data = self.tables["saved_meals"].read(meal_id)
            meal_type = "Saved Recipe"
            
            # If not found, try new_meal_ideas
            if not meal_data:
                meal_data = self.tables["new_meal_ideas"].read(meal_id)
                meal_type = "New Meal Idea"
            
            if meal_data and len(meal_data) > 0:
                # Use dictionary access since db functions return Row objects
                meal = meal_data[0] 
                name = meal['name']
                prep_time = meal['prep_time_minutes'] if meal_type == "Saved Recipe" else meal['prep_time']
                
                # Parse ingredients (new format: [[food_id, name, quantity], ...])
                try:
                    ingredients_json_str = meal['ingredients']
                    ingredients = json.loads(ingredients_json_str) if isinstance(ingredients_json_str, str) else ingredients_json_str
                    
                    # Format ingredients list based on new format
                    ingredients_text = ""
                    if isinstance(ingredients, list):
                        formatted_ings = []
                        for ing_data in ingredients:
                            # Expecting [food_id, name, quantity]
                            if isinstance(ing_data, list) and len(ing_data) >= 3:
                                # Use name (index 1) and quantity (index 2)
                                ing_name = ing_data[1] 
                                ing_quantity = ing_data[2]
                                formatted_ings.append(f"{ing_name} ({ing_quantity})")
                            else:
                                # Handle potential older format or unexpected data gracefully
                                formatted_ings.append(f"{str(ing_data)} (Format Error)")
                        ingredients_text = ", ".join(formatted_ings)
                    else:
                        ingredients_text = "[Invalid Ingredients Data Structure]"

                except (json.JSONDecodeError, TypeError) as e:
                    print(f"[WARN] Error parsing/formatting ingredients for meal ID {meal_id}: {e}")
                    ingredients_text = "[Ingredients Error]"
                
                # Add to output
                output += f"**Suggestion {i}: {name}**\n"
                output += f"Type: {meal_type}\n"
                output += f"Prep Time: {prep_time} minutes\n"
                output += f"Ingredients: {ingredients_text}\n"
                output += f"Meal ID: {meal_id}\n\n"
            
        output += "Would you like to see the full recipe for any of these options? Just ask!"
        return output

def generate_meal_suggestions(message_history: List) -> str:
    """Main function to generate meal suggestions based on message history"""
    # Extract user intent from message history
    user_intent = ""
    if message_history:
        # Get most recent user message
        for message in reversed(message_history):
            if isinstance(message, HumanMessage):
                user_intent = message.content
                break
    
    # Get all message history as a single string for context
    full_history = "\n".join([
        f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
        for msg in message_history[-5:] # Only use last 5 messages for context
    ])
    
    # Generate context using the existing context builder
    context_builder = MealSuggestionContextBuilder()
    meal_context = context_builder.build_context(full_history)
    
    # Filter the suggestions
    suggestion_filter = MealSuggestionFilter()
    meal_ids = suggestion_filter.filter_suggestions(user_intent, meal_context)
    
    # Format the results
    formatter = MealSuggestionFormatter()
    result = formatter.format_meal_suggestions(meal_ids)
    
    return result
