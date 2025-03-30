# tools/meal_planner.py

"""
This tool handles structured meal planning requests, including:
- Layer 1: Generating meal intents for specific dates based on user input.
- Layer 2: Selecting specific meals based on previously generated intents.

It maintains its own internal router to manage the state between Layer 1 and Layer 2.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from db.db_functions import Database, init_tables
from datetime import date, datetime, timedelta
import json
from typing import List, Optional, Dict, Tuple, Any, Union

# Import the generators/selectors needed from other files
from pig import MealNoteIntentGenerator as OriginalGenerator, DateRangeExtraction, MealIntent
from pig2 import MealPlannerSelector

# Load environment variables
load_dotenv()

# --- Re-implement necessary classes/functions from pig3.py --- 

# Subclass the original generator to override the clear_date_range method
class MealNoteIntentGenerator(OriginalGenerator):
    def clear_date_range(self, start_date: date, days_count: int):
        """Clear only meal_ids for the date range while preserving notes."""
        end_date = start_date + timedelta(days=days_count - 1)
        extended_start = start_date - timedelta(days=7)
        extended_end = end_date + timedelta(days=7)
        
        current_date = extended_start
        while current_date <= extended_end:
            existing = self.tables["daily_planner"].read(current_date)
            if existing:
                notes = existing[0][1] or ""
                self.tables["daily_planner"].update(
                    day=current_date,
                    notes=notes,
                    meal_ids=json.dumps([])
                )
            current_date += timedelta(days=1)
        print(f"Cleared meal IDs for date range from {extended_start.strftime('%Y-%m-%d')} to {extended_end.strftime('%Y-%m-%d')}")

    def extract_date_range(self, user_message: str) -> Optional[DateRangeExtraction]:
        """Extract date range from user message with improved error handling"""
        current_date = date(2025, 3, 29) # Using a fixed date for consistency
        current_day_of_week = current_date.strftime("%A")
        format_instructions = self.date_range_parser.get_format_instructions()
        
        prompt = ChatPromptTemplate.from_template(
            self.date_range_prompt + 
            "\n\nIMPORTANT: The days_count must be a valid positive integer value. " +
            "If the user message does not contain enough information to determine a specific date range, " +
            "still use the required format but set days_count to 0 to indicate more information is needed."
        )
        formatted_prompt = prompt.format(
            current_date=current_date.strftime("%Y-%m-%d"),
            current_day_of_week=current_day_of_week,
            user_message=user_message,
            format_instructions=format_instructions
        )
        
        try:
            response = self.chat.invoke(formatted_prompt)
            print("\n=== DATE RANGE EXTRACTION ===")
            print(response.content.strip())
            print("=== END DATE RANGE EXTRACTION ===\n")
            date_range = self.date_range_parser.parse(response.content)
            if date_range.days_count == 0:
                print("[INFO] LLM indicated insufficient information (days_count=0)")
                return None
            if not isinstance(date_range.days_count, int) or date_range.days_count < 1:
                print(f"[ERROR] Invalid days_count: {date_range.days_count}. Must be a positive integer.")
                return None
            return date_range
        except Exception as e:
            print(f"[ERROR] Failed to extract date range: {str(e)}")
            return None

class MealPlanningRouter:
    """Internal router for the meal planner tool."""
    def __init__(self, llm_model="gpt-4o-mini"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        self.router_prompt = (
            "You are a meal planning assistant that routes user requests to the appropriate layer based on conversation history.\n\n"
            "Determine the user's intent based on the flow of the conversation:\n"
            "1. Is the user initiating meal planning or asking to update meal *intents* (preferences, time constraints, etc.) for specific dates? → LAYER_1_INTENT_GENERATION\n"
            "2. Did the assistant *just* present meal intents (e.g., 'Breakfast: quick and easy...') AND is the user now asking to select *actual meals* based on those intents? → LAYER_2_MEAL_SELECTION\n"
            "3. Is the user making a general chat request unrelated to these two steps? → GENERAL_CHAT\n\n"
            "CRITICAL CONTEXT: Layer 1 is the default for starting or modifying the *plan* itself. Layer 2 ONLY happens *after* Layer 1 has shown the generated intents, and the user confirms they want to proceed with *selecting the specific meals*.\n"
            "Pay close attention to the *most recent* assistant message and the user's reply to determine if the transition to Layer 2 is appropriate.\n\n"
            "Input: Recent conversation history\n{message_history}\n\n"
            "Output: Respond ONLY with 'LAYER_1_INTENT_GENERATION', 'LAYER_2_MEAL_SELECTION', or 'GENERAL_CHAT'."
        )

    def determine_intent(self, message_history: List[Union[AIMessage, HumanMessage, SystemMessage]]) -> str:
        formatted_history = "\n".join([
            f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
            for msg in message_history[-10:]
        ])
        prompt = ChatPromptTemplate.from_template(self.router_prompt)
        formatted_prompt = prompt.format(message_history=formatted_history)
        response = self.chat.invoke(formatted_prompt)
        intent = response.content.strip()
        if "LAYER_1" in intent:
            return "LAYER_1_INTENT_GENERATION"
        elif "LAYER_2" in intent:
            return "LAYER_2_MEAL_SELECTION"
        else:
            return "GENERAL_CHAT"

class MealPlanningTool:
    """Handles the meal planning process, routing between Layer 1 and Layer 2."""
    def __init__(self):
        self.planning_router = MealPlanningRouter()
        self.meal_intent_generator = MealNoteIntentGenerator()
        self.meal_selector = MealPlannerSelector()
        # Use a simple in-memory store for chat history for this tool instance
        self.chat_history: List[Union[AIMessage, HumanMessage, SystemMessage]] = [] 

    def _get_full_message_history_str(self, current_history) -> str:
        conversation = ""
        for message in current_history:
            if isinstance(message, HumanMessage):
                conversation += f"User: {message.content}\n"
            elif isinstance(message, AIMessage):
                conversation += f"Assistant: {message.content}\n"
        return conversation
    
    def _format_intent_generation_response(self, result: Dict[str, Any]) -> str:
        response = "I've updated your meal plan with the following intents:\n\n"
        for day in result["days"]:
            date_obj = datetime.strptime(day["date"], "%Y-%m-%d")
            day_name = date_obj.strftime("%A")
            response += f"**{day_name}, {day['date']}**\n"
            response += f"- Breakfast: {day['meal_intent']['breakfast']}\n"
            response += f"- Lunch: {day['meal_intent']['lunch']}\n"
            response += f"- Dinner: {day['meal_intent']['dinner']}\n\n"
        response += "These intents have been saved to your meal planner. Would you like to:\n"
        response += "1. Make changes to these meal intents\n"
        response += "2. Proceed with selecting actual meals based on these intents"
        return response

    def _process_meal_planning_without_clearing(self, user_message: str, date_range: DateRangeExtraction) -> Dict[str, Any]:
        """Re-implementation of the logic from pig3.py"""
        end_date = date_range.start_date + timedelta(days=date_range.days_count - 1)
        message_lower = user_message.lower()
        single_day_terms = ["tomorrow", "today", "saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday"]
        
        for day_term in single_day_terms:
            if day_term in message_lower and "everything for " + day_term in message_lower:
                print(f"[INFO] Detected specific request for day: {day_term}")
                specific_date = date_range.start_date # Default
                if day_term == "tomorrow":
                    if specific_date == date(2025, 3, 29): # Today's date
                        specific_date += timedelta(days=1)
                elif day_term == "today":
                    specific_date = date(2025, 3, 29)
                else:
                    day_of_week_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
                    if day_term in day_of_week_map:
                        target_weekday = day_of_week_map[day_term]
                        days_ahead = (target_weekday - specific_date.weekday() + 7) % 7
                        specific_date = specific_date + timedelta(days=days_ahead)
                
                results = {"date_range": {"start_date": specific_date.strftime("%Y-%m-%d"), "end_date": specific_date.strftime("%Y-%m-%d"), "days_count": 1}, "days": []}
                meal_intent = self.meal_intent_generator.generate_meal_intent(user_message, specific_date)
                self.meal_intent_generator.save_meal_intent_to_db(specific_date, meal_intent)
                results["days"].append({"date": specific_date.strftime("%Y-%m-%d"), "day_of_week": specific_date.strftime("%A"), "meal_intent": meal_intent.dict()})
                return results

        # Process full date range if no specific day found
        results = {"date_range": {"start_date": date_range.start_date.strftime("%Y-%m-%d"), "end_date": end_date.strftime("%Y-%m-%d"), "days_count": date_range.days_count}, "days": []}
        current_date = date_range.start_date
        for _ in range(date_range.days_count):
            meal_intent = self.meal_intent_generator.generate_meal_intent(user_message, current_date)
            self.meal_intent_generator.save_meal_intent_to_db(current_date, meal_intent)
            results["days"].append({"date": current_date.strftime("%Y-%m-%d"), "day_of_week": current_date.strftime("%A"), "meal_intent": meal_intent.dict()})
            current_date += timedelta(days=1)
        return results

    def handle_intent_generation(self, message_history: List) -> str:
        """Handle Layer 1: Meal Intent Generation."""
        full_history_str = self._get_full_message_history_str(message_history)
        date_range = self.meal_intent_generator.extract_date_range(full_history_str)
        if not date_range:
            return "I need more information about when you want to plan meals for. Please specify a time period, like 'for the next 3 days' or 'this weekend'."
        result = self._process_meal_planning_without_clearing(full_history_str, date_range)
        response = self._format_intent_generation_response(result)
        return response

    def handle_meal_selection(self, message_history: List) -> str:
        """Handle Layer 2: Meal Selection based on intents."""
        try:
            full_history_str = self._get_full_message_history_str(message_history)
            date_range = self.meal_intent_generator.extract_date_range(full_history_str)
            if not date_range:
                return "I couldn't determine which days to select meals for. Please specify a date range like 'next 3 days' or 'this weekend'."

            start_date = date_range.start_date
            days_count = date_range.days_count
            end_date = start_date + timedelta(days=days_count - 1)
            db, tables = init_tables()
            current_date = start_date
            while current_date <= end_date:
                entry = tables["daily_planner"].read(current_date)
                if entry:
                    notes = entry[0][1] or ""
                    tables["daily_planner"].update(day=current_date, notes=notes, meal_ids=json.dumps([]))
                current_date += timedelta(days=1)

            self.meal_selector.plan_meals_for_range(start_date, days_count)
            
            response = f"I've selected meals for {days_count} days based on your meal intents. Here's what I picked:\n\n"
            current_date = start_date
            while current_date <= end_date:
                formatted_date = current_date.strftime("%A, %B %d, %Y")
                entry = tables["daily_planner"].read(current_date)
                if entry and entry[0]:
                    # Parse meal IDs, handling cases where it might already be a list
                    meal_ids_data = entry[0][2]
                    meal_ids = []
                    try:
                        if isinstance(meal_ids_data, list): # Already a list?
                            meal_ids = meal_ids_data
                        elif isinstance(meal_ids_data, str): # String to be parsed?
                            meal_ids = json.loads(meal_ids_data or '[]')
                        # Ensure it's a list after processing
                        if not isinstance(meal_ids, list):
                            print(f"[WARN] meal_ids for {formatted_date} is not a list after processing: {type(meal_ids)}. Resetting.")
                            meal_ids = []
                    except json.JSONDecodeError:
                        print(f"[WARN] Could not decode meal IDs JSON for {formatted_date}. Resetting.")
                        meal_ids = []
                    except Exception as e:
                        print(f"[ERROR] Unexpected error processing meal IDs for {formatted_date}: {e}. Resetting.")
                        meal_ids = []
                    
                    meal_names = []
                    for meal_id in meal_ids:
                        meal = tables["saved_meals"].read(meal_id)
                        if meal and meal[0]:
                            meal_names.append(f"{meal[0][1]} (ID: {meal_id})")
                        else:
                            meal = tables["new_meal_ideas"].read(meal_id)
                            if meal and meal[0]:
                                meal_names.append(f"{meal[0][1]} (ID: {meal_id})")
                            else:
                                meal_names.append(f"Unknown meal (ID: {meal_id})")
                    response += f"**{formatted_date}**\n"
                    if meal_names:
                        response += "Selected meals:\n" + "\n".join([f"- {name}" for name in meal_names]) + "\n"
                    else:
                        response += "No meals selected for this day.\n"
                    response += "\n"
                current_date += timedelta(days=1)
            response += "These meals have been saved to your meal planner. Would you like to make any adjustments or regenerate these meal selections?"
            return response
        except ImportError as e:
            return f"I couldn't access the meal selection functionality. Error: {str(e)}"
        except Exception as e:
            return f"An error occurred while selecting meals: {str(e)}. Please try again later."

# --- Main function called by tool_router.py --- 

def handle_meal_planning_request(message_history: List) -> str:
    """Processes a meal planning request based on the conversation history."""
    # Create an instance of the meal planning tool
    # In a real application, this might manage state across turns, but here we create a fresh one
    planner = MealPlanningTool()
    
    # The tool router has already decided this is a meal planning request.
    # Now, use the internal router to decide between Layer 1 and Layer 2.
    intent = planner.planning_router.determine_intent(message_history)
    print(f"[INFO - Meal Planner Tool] Determined internal intent: {intent}")
    
    if intent == "LAYER_1_INTENT_GENERATION":
        response_content = planner.handle_intent_generation(message_history)
    elif intent == "LAYER_2_MEAL_SELECTION":
        response_content = planner.handle_meal_selection(message_history)
    else:
        # Should ideally not happen if tool_router routes correctly, but handle defensively
        response_content = "I seem to be confused about the meal planning step. Could you clarify what you'd like to do?"
        
    return response_content

# --- Optional: Add a simple test block for this tool file --- 
if __name__ == "__main__":
    print("Testing Meal Planning Tool directly...")
    test_history = [
        SystemMessage(content="System context..."), # Placeholder
        HumanMessage(content="I want to start meal planning"),
        AIMessage(content="I need more information about when you want to plan meals for..."),
        HumanMessage(content="ok for the next 2 days, keep it simple"),
    ]
    
    # Test Layer 1
    print("\n--- Testing Layer 1 --- ")
    response1 = handle_meal_planning_request(test_history)
    print(f"\nAssistant Response 1:\n{response1}")
    
    # Add Layer 1 response to history and simulate user asking for Layer 2
    test_history.append(AIMessage(content=response1))
    test_history.append(HumanMessage(content="Proceed with selecting actual meals based on these intents"))
    
    # Test Layer 2
    print("\n--- Testing Layer 2 --- ")
    response2 = handle_meal_planning_request(test_history)
    print(f"\nAssistant Response 2:\n{response2}")
