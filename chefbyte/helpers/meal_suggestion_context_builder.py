# meal_suggestion_context_builder.py

"""
This module provides functionality to build meal suggestion context
based on user intent by analyzing message history and retrieving
appropriate meal options.
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
import random

# Load environment variables
load_dotenv()

# Define Pydantic models
class UserPreferences(BaseModel):
    restrict_to_inventory: bool = Field(
        True, 
        description="Whether to restrict meal suggestions to what can be made with current inventory"
    )
    open_to_new_meals: bool = Field(
        True, 
        description="Whether the user is open to new meal suggestions not in their saved collection"
    )
    only_want_new_meals: bool = Field(
        False, 
        description="Whether the user only wants new meal suggestions and no saved meals"
    )

class MealSuggestion(BaseModel):
    meal_id: int = Field(..., description="The ID of the suggested meal")
    name: str = Field(..., description="The name of the meal")
    meal_type: str = Field(..., description="Type of meal: 'saved' or 'new'")
    prep_time: int = Field(..., description="Preparation time in minutes")
    description: Optional[str] = Field(None, description="Brief description of the meal")

class MealSuggestionContextBuilder:
    def __init__(self, llm_model="gpt-4o-mini"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        
        # Initialize database and tables
        self.db, self.tables = init_tables()
        
        # Initialize the Pydantic output parsers
        self.preferences_parser = PydanticOutputParser(pydantic_object=UserPreferences)
        
        # Preferences analyzer prompt template
        self.preferences_prompt = (
            "You are an AI assistant that analyzes user message history to determine meal preferences.\n"
            "Based on the conversation, determine:\n\n"
            "1. If the user wants to restrict meal suggestions to what they can make with their current inventory:\n"
            "   - True if the user mentions wanting to cook with what they have on hand\n"
            "   - True if the user asks 'what can I make with what I have'\n"
            "   - False if they seem open to buying new ingredients\n"
            "   - Default to True if unclear\n\n"
            "2. If the user is open to new meal suggestions not in their saved collection:\n"
            "   - True if the user asks for new ideas or suggestions\n"
            "   - True if the user wants to try something different\n"
            "   - False if they specifically only want meals from their saved collection\n"
            "   - Default to True if unclear\n\n"
            "3. If the user only wants new meal suggestions and no saved meals:\n"
            "   - True if the user specifically asks for only new recipes\n"
            "   - True if the user says they want something they've never made before\n"
            "   - False if they seem open to both saved and new meals\n"
            "   - Default to False if unclear\n\n"
            "User Intent:\n{user_intent}\n\n"
            "{format_instructions}"
        )

    def analyze_user_preferences(self, user_intent: str) -> UserPreferences:
        """Analyze user intent to determine meal preferences"""
        format_instructions = self.preferences_parser.get_format_instructions()
        
        # Create prompt from template
        prompt = ChatPromptTemplate.from_template(self.preferences_prompt)
        formatted_prompt = prompt.format(
            user_intent=user_intent,
            format_instructions=format_instructions
        )
        
        try:
            response = self.chat.invoke(formatted_prompt)
            
            # Parse the preferences
            preferences = self.preferences_parser.parse(response.content)
            return preferences
            
        except Exception as e:
            print(f"Error in preferences analysis: {str(e)}")
            # Return default preferences
            return UserPreferences(
                restrict_to_inventory=True,
                open_to_new_meals=True,
                only_want_new_meals=False
            )

    def get_meal_options(self, preferences: UserPreferences, max_options: int = 7) -> List[MealSuggestion]:
        """Get meal options based on user preferences"""
        meal_options = []
        
        # Determine which meal sources to include
        include_saved_meals = not preferences.only_want_new_meals
        include_new_meals = preferences.open_to_new_meals
        
        if not include_saved_meals and not include_new_meals:
            # Default to including both if somehow neither is selected
            include_saved_meals = True
            include_new_meals = True
        
        # Get meals from appropriate sources
        if preferences.restrict_to_inventory:
            # Only include meals that can be made with current inventory
            if include_saved_meals:
                saved_in_stock = self.get_saved_meals_in_stock()
                meal_options.extend(saved_in_stock)
            
            if include_new_meals:
                new_in_stock = self.get_new_meals_in_stock()
                meal_options.extend(new_in_stock)
        else:
            # Include all meals regardless of inventory
            if include_saved_meals:
                saved_meals = self.get_saved_meals()
                meal_options.extend(saved_meals)
            
            if include_new_meals:
                new_meals = self.get_new_meals()
                meal_options.extend(new_meals)
        
        # Randomize the order of meal options
        random.shuffle(meal_options)
        
        # If we have more options than requested, clip to max_options
        if len(meal_options) > max_options:
            meal_options = meal_options[:max_options]
        
        return meal_options

    def get_saved_meals_in_stock(self) -> List[MealSuggestion]:
        """Get saved meals that can be made with current inventory"""
        result = []
        
        try:
            # Get IDs of saved meals that are in stock
            in_stock_ids = self.tables["saved_meals_instock_ids"].read()
            
            if not in_stock_ids:
                return result
                
            in_stock_id_list = [item['id'] for item in in_stock_ids]
            
            # Get details of these meals
            for meal_id in in_stock_id_list:
                meal_data = self.tables["saved_meals"].read(meal_id)
                if meal_data and len(meal_data) > 0:
                    meal = meal_data[0]
                    result.append(MealSuggestion(
                        meal_id=meal["id"],
                        name=meal["name"],
                        meal_type="saved",
                        prep_time=meal["prep_time_minutes"],
                        description=self.generate_description_from_recipe(meal["recipe"])
                    ))
        except Exception as e:
            print(f"Error getting saved meals in stock: {str(e)}")
            
        return result

    def get_new_meals_in_stock(self) -> List[MealSuggestion]:
        """Get new meal ideas that can be made with current inventory"""
        result = []
        
        try:
            # Get IDs of new meals that are in stock
            in_stock_ids = self.tables["new_meal_ideas_instock_ids"].read()
            
            if not in_stock_ids:
                return result
                
            in_stock_id_list = [item['id'] for item in in_stock_ids]
            
            # Get details of these meals
            for meal_id in in_stock_id_list:
                meal_data = self.tables["new_meal_ideas"].read(meal_id)
                if meal_data and len(meal_data) > 0:
                    meal = meal_data[0]
                    result.append(MealSuggestion(
                        meal_id=meal["id"],
                        name=meal["name"],
                        meal_type="new",
                        prep_time=meal["prep_time"],
                        description=self.generate_description_from_recipe(meal["recipe"])
                    ))
        except Exception as e:
            print(f"Error getting new meals in stock: {str(e)}")
            
        return result

    def get_saved_meals(self) -> List[MealSuggestion]:
        """Get all saved meals"""
        result = []
        
        try:
            # Get all saved meals
            saved_meals = self.tables["saved_meals"].read()
            
            if not saved_meals:
                return result
                
            for meal in saved_meals:
                result.append(MealSuggestion(
                    meal_id=meal["id"],
                    name=meal["name"],
                    meal_type="saved",
                    prep_time=meal["prep_time_minutes"],
                    description=self.generate_description_from_recipe(meal["recipe"])
                ))
        except Exception as e:
            print(f"Error getting saved meals: {str(e)}")
            
        return result

    def get_new_meals(self) -> List[MealSuggestion]:
        """Get all new meal ideas"""
        result = []
        
        try:
            # Get all new meal ideas
            new_meals = self.tables["new_meal_ideas"].read()
            
            if not new_meals:
                return result
                
            for meal in new_meals:
                result.append(MealSuggestion(
                    meal_id=meal["id"],
                    name=meal["name"],
                    meal_type="new",
                    prep_time=meal["prep_time"],
                    description=self.generate_description_from_recipe(meal["recipe"])
                ))
        except Exception as e:
            print(f"Error getting new meals: {str(e)}")
            
        return result

    def generate_description_from_recipe(self, recipe_text: str, max_length: int = 100) -> str:
        """Generate a brief description from recipe text"""
        if not recipe_text or len(recipe_text) < 10:
            return "No description available"
            
        # Try to extract the first sentence or first 100 characters
        first_sentence_end = recipe_text.find('.')
        if 10 < first_sentence_end < max_length:
            return recipe_text[:first_sentence_end + 1]
        else:
            # Just take the first max_length characters
            description = recipe_text[:max_length].strip()
            if len(recipe_text) > max_length:
                description += "..."
            return description

    def format_meal_suggestions(self, meal_suggestions: List[MealSuggestion]) -> str:
        """Format meal suggestions for display"""
        if not meal_suggestions:
            return "No meal suggestions found that match your preferences. Try adjusting your search criteria."
            
        output = "Here are some meal suggestions that match your preferences:\n\n"
        
        for i, meal in enumerate(meal_suggestions, 1):
            meal_type_display = "Saved Recipe" if meal.meal_type == "saved" else "New Meal Idea"
            output += f"MEAL #{i}: {meal.name}\n"
            output += f"Type: {meal_type_display}\n"
            output += f"Prep Time: {meal.prep_time} minutes\n"
            output += f"Description: {meal.description}\n"
            output += f"Meal ID: {meal.meal_id}\n\n"
            
        output += "Would you like to:\n"
        output += "1. See the full recipe for any of these options\n"
        output += "2. Get different meal suggestions\n"
        output += "3. Adjust your meal preferences"
            
        return output

    def build_context(self, user_intent: str, max_options: int = 7) -> str:
        """Main function to analyze user intent and build meal suggestion context"""
        # Analyze user preferences from intent
        preferences = self.analyze_user_preferences(user_intent)
        
        # Get meal options based on preferences
        meal_options = self.get_meal_options(preferences, max_options)
        
        # Format and return meal suggestions
        return self.format_meal_suggestions(meal_options) 