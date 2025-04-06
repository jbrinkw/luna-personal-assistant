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
import re
from helpers.meal_suggestion_context_builder import MealSuggestionContextBuilder, MealSuggestion

# Load environment variables
load_dotenv()

# --- Classes imported from pig.py ---
class DateRangeExtraction(BaseModel):
    start_date: date = Field(..., description="The start date of the meal planning period")
    days_count: int = Field(..., description="The number of days in the meal planning period")

class MealIntent(BaseModel):
    breakfast: str = Field(..., description="Intent for breakfast")
    lunch: str = Field(..., description="Intent for lunch")
    dinner: str = Field(..., description="Intent for dinner")

class OriginalGenerator:
    def __init__(self, llm_model="gpt-4o-mini"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        
        # Initialize database and tables
        self.db, self.tables = init_tables()
        
        # Initialize the Pydantic output parsers
        self.date_range_parser = PydanticOutputParser(pydantic_object=DateRangeExtraction)
        self.meal_intent_parser = PydanticOutputParser(pydantic_object=MealIntent)
        
        # Date range extraction prompt template
        self.date_range_prompt = (
            "You are an AI assistant that extracts date ranges from user messages about meal planning.\n"
            "The current date is {current_date} ({current_day_of_week}).\n\n"
            "Based on the user's message, determine:\n"
            "1. The start date for meal planning (likely today or a future date)\n"
            "2. The number of days in the planning period\n\n"
            "Examples:\n"
            "- 'Plan meals for the next week' → start: today, days: 7\n"
            "- 'I need meals for Monday through Friday' → start: next Monday, days: 5\n"
            "- 'Plan my meals for tomorrow' → start: tomorrow, days: 1\n\n"
            "For dates that mention days of the week, use the next occurrence of that day.\n"
            "If no specific dates are mentioned, assume the user wants to start planning from today.\n\n"
            "User message: {user_message}\n\n"
            "{format_instructions}"
        )
        
        # Meal intent generation prompt template
        self.meal_intent_prompt = (
            "You are a helpful meal planning assistant.\n"
            "Based on the user's message, generate suitable intents for each meal of the day.\n\n"
            "User's message: {user_message}\n\n"
            "For {planning_date} ({day_of_week}), generate intents for:\n"
            "- Breakfast\n"
            "- Lunch\n"
            "- Dinner\n\n"
            "Each intent should be a short phrase capturing dietary preferences, time constraints, or flavor preferences.\n"
            "Examples:\n"
            "- 'quick and easy'\n"
            "- 'healthy vegetarian'\n"
            "- 'high protein'\n"
            "- 'comfort food'\n"
            "- 'kid-friendly'\n"
            "- 'using leftovers'\n\n"
            "Consider the overall context and any specific requirements mentioned by the user.\n"
            "Also consider that preferences might change based on the day of the week (workdays vs. weekends).\n\n"
            "{format_instructions}"
        )

    def extract_date_range(self, user_message: str) -> DateRangeExtraction:
        """Extract date range from user message"""
        # Get current date and day of week
        current_date = date(2025, 3, 29)  # Using the specified date in the instructions
        current_day_of_week = current_date.strftime("%A")
        
        format_instructions = self.date_range_parser.get_format_instructions()
        
        # Create prompt from template
        prompt = ChatPromptTemplate.from_template(self.date_range_prompt)
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
            
            # Parse the date range
            date_range = self.date_range_parser.parse(response.content)
            return date_range
            
        except Exception as e:
            print(f"Error in date range extraction: {str(e)}")
            # Return default date range (today to 3 days from now)
            return DateRangeExtraction(
                start_date=current_date,
                days_count=3
            )

    def generate_meal_intent(self, user_message: str, planning_date: date) -> MealIntent:
        """Generate meal intents for a specific day"""
        day_of_week = planning_date.strftime("%A")
        format_instructions = self.meal_intent_parser.get_format_instructions()
        
        # Create prompt from template
        prompt = ChatPromptTemplate.from_template(self.meal_intent_prompt)
        formatted_prompt = prompt.format(
            user_message=user_message,
            planning_date=planning_date.strftime("%Y-%m-%d"),
            day_of_week=day_of_week,
            format_instructions=format_instructions
        )
        
        try:
            response = self.chat.invoke(formatted_prompt)
            print(f"\n=== MEAL INTENT FOR {planning_date.strftime('%Y-%m-%d')} ===")
            print(response.content.strip())
            print(f"=== END MEAL INTENT FOR {planning_date.strftime('%Y-%m-%d')} ===\n")
            
            # Parse the meal intent
            meal_intent = self.meal_intent_parser.parse(response.content)
            return meal_intent
            
        except Exception as e:
            print(f"Error in meal intent generation: {str(e)}")
            # Return default meal intent
            return MealIntent(
                breakfast="quick and easy",
                lunch="simple and filling",
                dinner="balanced and nutritious"
            )

    def clear_date_range(self, start_date: date, days_count: int):
        """Clear daily planner entries for a date range plus a week before and after"""
        # Calculate the end date
        end_date = start_date + timedelta(days=days_count - 1)
        
        # Calculate the extended range (a week before and after)
        extended_start = start_date - timedelta(days=7)
        extended_end = end_date + timedelta(days=7)
        
        current_date = extended_start
        while current_date <= extended_end:
            # Check if there's an entry for this date
            existing = self.tables["daily_planner"].read(current_date)
            if existing:
                # Clear the entry
                self.tables["daily_planner"].update(
                    day=current_date,
                    notes="",
                    meal_ids=json.dumps([])
                )
                print(f"Cleared daily planner entry for {current_date.strftime('%Y-%m-%d')}")
            current_date += timedelta(days=1)
        
        print(f"Cleared date range from {extended_start.strftime('%Y-%m-%d')} to {extended_end.strftime('%Y-%m-%d')}")

    def save_meal_intent_to_db(self, planning_date: date, meal_intent: MealIntent):
        """Save the meal intent to the database"""
        # Check if there's an existing entry for this date
        existing = self.tables["daily_planner"].read(planning_date)
        
        # Format the notes
        notes = f"Breakfast: {meal_intent.breakfast}\nLunch: {meal_intent.lunch}\nDinner: {meal_intent.dinner}"
        
        if existing:
            # Update the existing entry
            self.tables["daily_planner"].update(
                day=planning_date,
                notes=notes,
                meal_ids=json.dumps([])  # Clear any existing meal IDs
            )
        else:
            # Create a new entry
            self.tables["daily_planner"].create(
                day=planning_date,
                notes=notes,
                meal_ids=json.dumps([])
            )
        
        print(f"Saved meal intent for {planning_date.strftime('%Y-%m-%d')}")

# --- Classes imported from pig2.py ---
class SelectedMeal(BaseModel):
    meal_id: int = Field(..., description="The ID of the selected meal that best fits the intent")
    reasoning: Optional[str] = Field(None, description="Brief reasoning for selecting this meal")

class MealPlannerSelector:
    def __init__(self, llm_model="gpt-4o-mini"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        self.db, self.tables = init_tables()
        self.context_builder = MealSuggestionContextBuilder(llm_model=llm_model)
        self.meal_selector_parser = PydanticOutputParser(pydantic_object=SelectedMeal)

        self.meal_selector_prompt_template = (
            "You are an AI assistant helping select a specific meal based on a user's intent and a list of suggestions.\n"
            "Analyze the user's meal intent and the provided meal suggestions.\n"
            "Choose the *single best* meal ID from the suggestions that most closely matches the user's intent.\n\n"
            "User's Meal Intent: {meal_intent}\n\n"
            "Available Meal Suggestions:\n"
            "{meal_suggestions_text}\n\n"
            "Consider factors like 'quick and easy', 'healthy', 'using leftovers', 'vegetarian', 'comfort food', 'new', 'saved', etc., mentioned in the intent.\n"
            "Prioritize meals that directly address the core aspects of the intent.\n"
            "If multiple meals fit well, make a reasonable choice.\n\n"
            "Output your selection in the following JSON format:\n"
            "{format_instructions}"
        )

    def parse_daily_notes(self, notes: str) -> Dict[str, str]:
        """Parse the daily planner notes into meal intents."""
        intents = {"breakfast": "default", "lunch": "default", "dinner": "default"}
        if not notes:
            return intents

        # Use regex to find intents - improved robustness
        breakfast_match = re.search(r"Breakfast:\s*(.*)", notes, re.IGNORECASE)
        lunch_match = re.search(r"Lunch:\s*(.*)", notes, re.IGNORECASE)
        dinner_match = re.search(r"Dinner:\s*(.*)", notes, re.IGNORECASE)

        if breakfast_match:
            intents["breakfast"] = breakfast_match.group(1).strip()
        if lunch_match:
            intents["lunch"] = lunch_match.group(1).strip()
        if dinner_match:
            intents["dinner"] = dinner_match.group(1).strip()

        # Handle cases where matches might overlap or capture subsequent lines
        if intents["lunch"] != "default" and intents["breakfast"] != "default":
             intents["breakfast"] = intents["breakfast"].replace(f"Lunch: {intents['lunch']}", "").replace(f"Dinner: {intents['dinner']}", "").strip()
        if intents["dinner"] != "default" and intents["lunch"] != "default":
             intents["lunch"] = intents["lunch"].replace(f"Dinner: {intents['dinner']}", "").strip()

        # If specific intents aren't found, use the whole note as a general intent,
        # but prioritize found ones.
        if all(v == "default" for v in intents.values()) and notes:
             intents = {"breakfast": notes, "lunch": notes, "dinner": notes}

        return intents

    def select_meal_for_intent(self, meal_intent: str, meal_suggestions: List[MealSuggestion]) -> Optional[int]:
        """Uses LLM to select the best meal ID from suggestions based on intent."""
        if not meal_suggestions:
            print(f"No meal suggestions provided for intent: '{meal_intent}'. Cannot select.")
            return None

        # Format detailed suggestions for the LLM prompt
        suggestions_text_detailed = ""
        for i, meal in enumerate(meal_suggestions):
            suggestions_text_detailed += f"Suggestion {i+1}:\n"
            suggestions_text_detailed += f"  ID: {meal.meal_id}\n"
            suggestions_text_detailed += f"  Name: {meal.name}\n"
            suggestions_text_detailed += f"  Type: {meal.meal_type}\n"
            suggestions_text_detailed += f"  Prep Time: {meal.prep_time} minutes\n"
            suggestions_text_detailed += f"  Description: {meal.description}\n\n"
            
        # Format simplified suggestions for debug printing
        suggestions_text_simplified = ""
        for i, meal in enumerate(meal_suggestions):
            suggestions_text_simplified += f"Suggestion {i+1}: {meal.name} ({meal.prep_time} mins)\n"

        format_instructions = self.meal_selector_parser.get_format_instructions()
        prompt = ChatPromptTemplate.from_template(self.meal_selector_prompt_template)
        formatted_prompt = prompt.format(
            meal_intent=meal_intent,
            meal_suggestions_text=suggestions_text_detailed.strip(), # Use detailed text for LLM
            format_instructions=format_instructions
        )

        try:
            print(f"\n--- Selecting meal for intent: '{meal_intent}' ---")
            print(f"--- Suggestions provided (for debugging): --- \n{suggestions_text_simplified.strip()}") # Use simplified text for printing
            response = self.chat.invoke(formatted_prompt)
            print(f"--- LLM Selection Response: ---\n{response.content.strip()}")
            selected_meal_info = self.meal_selector_parser.parse(response.content)
            print(f"--- Parsed Selection: ID={selected_meal_info.meal_id}, Reason={selected_meal_info.reasoning} ---")

            # Validate the selected ID exists in the suggestions
            if any(suggestion.meal_id == selected_meal_info.meal_id for suggestion in meal_suggestions):
                 return selected_meal_info.meal_id
            else:
                 print(f"[ERROR] LLM selected meal ID {selected_meal_info.meal_id} which was not in the suggestion list.")
                 # Fallback: pick the first suggestion
                 if meal_suggestions:
                      print(f"[FALLBACK] Selecting the first suggestion: ID={meal_suggestions[0].meal_id}")
                      return meal_suggestions[0].meal_id
                 else:
                      return None
        except Exception as e:
            print(f"Error during meal selection for intent '{meal_intent}': {str(e)}")
            # Fallback: pick the first suggestion if LLM fails
            if meal_suggestions:
                 print(f"[FALLBACK] Selecting the first suggestion due to error: ID={meal_suggestions[0].meal_id}")
                 return meal_suggestions[0].meal_id
            else:
                 return None

    def plan_meals_for_range(self, start_date: date, days_count: int):
        """Selects meals for each day and mealtime in the range based on stored intents."""
        print(f"\n=== Starting Meal Planning Selection for {days_count} days from {start_date.strftime('%Y-%m-%d')} ===")
        end_date = start_date + timedelta(days=days_count - 1)
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            print(f"\n--- Planning for Date: {date_str} ({current_date.strftime('%A')}) ---")

            # 1. Fetch daily notes
            daily_entry = self.tables["daily_planner"].read(current_date)
            notes = ""
            current_meal_ids = []
            if daily_entry and len(daily_entry) > 0:
                notes = daily_entry[0][1] or ""
                try:
                    # Load existing meal IDs, ensure it's a list
                    loaded_ids = json.loads(daily_entry[0][2] or '[]')
                    if isinstance(loaded_ids, list):
                        current_meal_ids = loaded_ids
                    else:
                        print(f"[WARN] Meal IDs for {date_str} was not a list: {loaded_ids}. Resetting.")
                        current_meal_ids = []
                except json.JSONDecodeError:
                    print(f"[WARN] Could not decode meal IDs for {date_str}. Resetting.")
                    current_meal_ids = []
            else:
                print(f"No daily planner entry found for {date_str}. Skipping planning for this day.")
                current_date += timedelta(days=1)
                continue # Skip to next day if no entry

            if not notes:
                print(f"No meal intents (notes) found for {date_str}. Skipping planning for this day.")
                current_date += timedelta(days=1)
                continue # Skip to next day if no notes

            print(f"Intents Note: {notes}")

            # 2. Parse notes into intents
            meal_intents = self.parse_daily_notes(notes)
            print(f"Parsed Intents: {meal_intents}")

            selected_ids_for_day = {}

            # 3. & 4. & 5. Get suggestions, Select Meal for Breakfast, Lunch, Dinner
            for meal_type in ["breakfast", "lunch", "dinner"]:
                intent = meal_intents.get(meal_type, "")
                if not intent or intent == "default":
                    print(f"No specific intent found for {meal_type} on {date_str}. Skipping.")
                    continue

                # Get preferences (needed by get_meal_options)
                # We'll assume the context builder analyzes the *specific* meal intent string
                # to get appropriate preferences for that meal.
                preferences = self.context_builder.analyze_user_preferences(intent)
                print(f"Preferences for {meal_type} ('{intent}'): {preferences}")

                # Get meal options using the context builder's method
                # Pass the analyzed preferences for this specific meal intent
                meal_options = self.context_builder.get_meal_options(preferences)

                # Select the best meal ID
                selected_id = self.select_meal_for_intent(intent, meal_options)

                if selected_id:
                    selected_ids_for_day[meal_type] = selected_id
                else:
                     print(f"Could not select a meal for {meal_type} on {date_str}.")

            # 6. Update Database with selected IDs for the day
            # Combine newly selected IDs with any potentially existing ones (though usually planner is cleared before)
            final_meal_ids = current_meal_ids # Start with existing
            newly_selected = [selected_ids_for_day[mt] for mt in ["breakfast", "lunch", "dinner"] if mt in selected_ids_for_day]
            
            # Avoid duplicates if re-running
            for new_id in newly_selected:
                if new_id not in final_meal_ids:
                    final_meal_ids.append(new_id)

            print(f"Updating {date_str} with Meal IDs: {final_meal_ids}")
            self.tables["daily_planner"].update(
                day=current_date,
                notes=notes,  # Keep original notes
                meal_ids=json.dumps(final_meal_ids)
            )

            current_date += timedelta(days=1)

        print("\n=== Meal Planning Selection Complete ===")

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
