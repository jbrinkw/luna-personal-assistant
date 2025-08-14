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
import traceback

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
    def __init__(self, db: Database, tables: dict, llm_model="gpt-4o-mini"):
        self.db = db
        self.tables = tables
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        
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
    def __init__(self, db: Database, tables: dict, llm_model="gpt-4o-mini"):
        self.db = db
        self.tables = tables
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
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
                notes = daily_entry[0]['notes'] or ""
                try:
                    # Load existing meal IDs, ensure it's a list
                    loaded_ids = json.loads(daily_entry[0]['meal_ids'] or '[]')
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
                notes = existing[0]['notes'] or ""
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
    def __init__(self, db: Database, tables: dict, llm_model="gpt-4o-mini"):
        self.db = db
        self.tables = tables
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = llm_model
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        self.router_prompt = (
            "You are a meal planning assistant that routes user requests to the appropriate layer. "
            "Analyze the **single user message provided** to determine the user's current intent within the meal planning flow.\n\n"
            "Determine the intent:\n"
            "1. **LAYER_1_INTENT_GENERATION:** If the user is asking to *start* planning, *modify* existing plans/intents, or asking *about* the plan for specific dates (e.g., 'plan my week', 'change Wednesday', 'what is the plan for Friday?'). This is the default if unsure. \n"
            "2. **LAYER_2_MEAL_SELECTION:** If the user's message clearly indicates they want to proceed with selecting *specific meals* based on previously presented intents (e.g., contains keywords like 'select meals', 'choose meals', 'proceed', 'go ahead', 'pick recipes', 'use those intents'). \n"
            "3. **GENERAL_CHAT:** If the message is unrelated to planning or selecting meals (e.g., 'hello', 'thank you').\n\n"
            "User Message:\n{user_message}\n\n"
            "Output: Respond ONLY with 'LAYER_1_INTENT_GENERATION', 'LAYER_2_MEAL_SELECTION', or 'GENERAL_CHAT'."
        )

    def determine_intent(self, message_history: List[Union[AIMessage, HumanMessage, SystemMessage]]) -> str:
        # Extract the single user message from the (minimal) history
        user_message = ""
        if message_history and isinstance(message_history[-1], HumanMessage):
            user_message = message_history[-1].content
        else:
            # Fallback or handle error if no user message found
            print("[WARN MealPlanningRouter] No user message found in history.")
            return "GENERAL_CHAT" 
            
        prompt = ChatPromptTemplate.from_template(self.router_prompt)
        # Pass only the single message to the prompt
        formatted_prompt = prompt.format(user_message=user_message) 
        response = self.chat.invoke(formatted_prompt)
        intent = response.content.strip()
        # Simplify intent checking
        if "LAYER_1" in intent:
            return "LAYER_1_INTENT_GENERATION"
        elif "LAYER_2" in intent:
            return "LAYER_2_MEAL_SELECTION"
        else:
            return "GENERAL_CHAT"

# --- Main Tool Class ---
class MealPlanningTool:
    def __init__(self, db: Database, tables: dict, llm_model="gpt-4o-mini"):
        """Initialize the MealPlanningTool with shared DB objects."""
        self.db = db
        self.tables = tables
        self.llm_model = llm_model
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.chat = ChatOpenAI(model=self.llm_model, openai_api_key=self.api_key)
        
        # Initialize internal components, passing db and tables
        self.router = MealPlanningRouter(db, tables, llm_model)
        self.intent_generator = OriginalGenerator(db, tables, llm_model) # Assuming this needs db/tables too
        self.meal_selector = MealPlannerSelector(db, tables, llm_model) # Assuming this needs db/tables too
        self.note_intent_generator = MealNoteIntentGenerator(db, tables, llm_model) # Assuming this needs db/tables too
        
        print("[MealPlanningTool] Initialized")

    # --- NEW HELPER METHOD ---
    def find_meal_by_name(self, name: str) -> Optional[int]:
        """Find a meal ID by name using the tool's saved_meals table access."""
        if not name or 'saved_meals' not in self.tables:
            return None
        
        saved_meals = self.tables['saved_meals']
        try:
            all_meals = saved_meals.read()
            if not all_meals:
                return None
                
            # Case-insensitive comparison
            name_lower = name.lower()
            
            # First try exact match
            for meal in all_meals:
                if meal['name'].lower() == name_lower:
                    return meal['id']
                    
            # Then try partial match (e.g., "tuna ramen" matches "Spicy Tuna Ramen")
            for meal in all_meals:
                if name_lower in meal['name'].lower():
                    return meal['id']
                    
            return None
        except Exception as e:
             print(f"[ERROR MealPlanningTool] Failed to find meal by name '{name}': {e}")
             return None
    # --- END NEW HELPER METHOD ---

    def execute(self, chat_history: List) -> str:
        """Execute the meal planning process based on conversation history."""
        # print("-- [MealPlanningTool] START execute --") # Log Start (Removed)
        try:
            # Determine the correct layer using the internal router
            # print("  Calling internal router...") # Log Router Call (Removed)
            layer_intent = self.router.determine_intent(chat_history)
            # print(f"  Internal router returned: {layer_intent}") # Log Router Result (Removed)
            
            # Get the latest user message from the history
            user_message = ""
            if chat_history and isinstance(chat_history[-1], HumanMessage):
                user_message = chat_history[-1].content
            # else:
                 # print("  [WARN] Could not extract latest user message from history.") # Log Warn (Removed)
                 # user_message = "" # Default to empty if not found

            response_content = ""
            
            # --- Layer 1: Generate Intents --- 
            if layer_intent == "LAYER_1_INTENT_GENERATION":
                # print("  Entering Layer 1: Generate Intents...") # Log Layer 1 (Removed)
                
                if not user_message:
                    # print("  [WARN] Empty user message for Layer 1.") # Log Warn Empty (Removed)
                    return "I couldn't understand your request for meal planning. Could you please provide more details?"
                
                # --- Check for Specific Meal Planning --- 
                # print("  Checking for specific meal name in request...") # Log Specific Check (Removed)
                specific_meal_match = re.search(r"plan\s+(?:an?|the)?\s*(.*?)\s+(?:for|on)\b", user_message, re.IGNORECASE)
                meal_name_to_plan = None
                meal_id_to_plan = None
                if specific_meal_match:
                    potential_meal_name = specific_meal_match.group(1).strip().replace("'", "") # Clean up name
                    # print(f"  Potential specific meal: '{potential_meal_name}'") # Log Potential Name (Removed)
                    found_id = self.find_meal_by_name(potential_meal_name) 
                    if found_id:
                        meal_id_to_plan = found_id
                        meal_data = self.tables['saved_meals'].read(found_id)
                        meal_name_to_plan = meal_data[0]['name'] if meal_data and meal_data[0] else potential_meal_name
                        # print(f"  Found Saved Meal ID: {meal_id_to_plan} ({meal_name_to_plan})") # Log Found ID (Removed)
                    # else:
                        # print(f"  Specific meal '{potential_meal_name}' not found in saved meals.") # Log Not Found (Removed)
                # --- END Specific Check ---
                    
                # Extract date range 
                # print("  Extracting date range...") # Log Date Extract (Removed)
                date_range = self.note_intent_generator.extract_date_range(user_message)
                
                if date_range is None or date_range.days_count == 0:
                    # print("  Date range extraction failed or returned 0 days.") # Log Date Fail (Removed)
                    return "I need a bit more information to plan your meals. Please specify for which day(s) or how long you'd like to plan (e.g., 'next 3 days', 'Monday to Wednesday')."
                    
                start_date = date_range.start_date
                days_count = date_range.days_count
                
                # print(f"  Date range extracted: Start={start_date}, Days={days_count}") # Log Date Success (Removed)

                # Clear existing meal IDs (preserving notes) for the range
                # print("  Clearing existing meal IDs for date range...") # Log Clear IDs (Removed)
                self.note_intent_generator.clear_date_range(start_date, days_count)
                # print("  Meal IDs cleared.") # Log Clear Done (Removed)
                
                # --- Plan Specific Meal or Generate Intents ---
                if meal_id_to_plan and days_count == 1: # Only plan specific meal if found and for a single day request
                    # print(f"  Attempting to plan specific meal ID {meal_id_to_plan} for {start_date}...") # Log Plan Specific (Removed)
                    # Update the database directly with the meal ID
                    self.tables["daily_planner"].update( # CHANGE: Use update instead of create
                        day=start_date,
                        notes=f"Planned: {meal_name_to_plan}", # Simple note
                        meal_ids=json.dumps([meal_id_to_plan])
                    )
                    response_content = f"Okay, I've planned **{meal_name_to_plan}** for {start_date.strftime('%A, %B %d')}."
                    # print("  Specific meal planned successfully.") # Log Plan Specific Done (Removed)
                else:
                    # Fallback to generating intents if no specific meal found or multi-day request
                    # if meal_id_to_plan: print("  Specific meal found, but multi-day request. Generating intents instead.") # Log Intent Fallback (Multi-day) (Removed)
                    # else: print("  No specific meal found in request. Generating intents...") # Log Intent Fallback (Not Found) (Removed)
                    
                    all_intents = []
                    current_planning_date = start_date
                    for i in range(days_count):
                        # print(f"    Generating intent for day {i+1} ({current_planning_date})...") # Log Intent Gen Loop (Removed)
                        meal_intent = self.note_intent_generator.generate_meal_intent(user_message, current_planning_date)
                        # print(f"    Intent generated for {current_planning_date}: B={intent.breakfast}, L={intent.lunch}, D={intent.dinner}") # Log Intent Gen Result (Removed)
                        # print(f"    Saving intent for {current_planning_date}...") # Log Intent Save (Removed)
                        self.note_intent_generator.save_meal_intent_to_db(current_planning_date, meal_intent)
                        all_intents.append((current_planning_date, meal_intent))
                        current_planning_date += timedelta(days=1)
                        
                    # Format response for the user
                    response_content = "Okay, I've created initial meal intents based on your request:\n\n"
                    for plan_date, intent in all_intents:
                        response_content += f"**{plan_date.strftime('%Y-%m-%d, %A')}**:\n"
                        response_content += f"  - Breakfast: {intent.breakfast}\n"
                        response_content += f"  - Lunch: {intent.lunch}\n"
                        response_content += f"  - Dinner: {intent.dinner}\n"
                    response_content += "\nWould you like me to select specific meals based on these intents?"
                    # print("  Intent generation and response formatting complete.") # Log Intent Done (Removed)
            
            # --- Layer 2: Select Specific Meals --- 
            elif layer_intent == "LAYER_2_MEAL_SELECTION":
                # print("  Entering Layer 2: Select Meals...") # Log Layer 2 (Removed)
                
                # Find the message where Layer 1 likely generated intents
                relevant_user_message_for_range = user_message # Default to current
                
                # print("  Attempting to re-extract date range for Layer 2 (may be inaccurate without full history)... ") # Log L2 Date Extract (Removed)
                date_range = self.note_intent_generator.extract_date_range(relevant_user_message_for_range) 
                
                if date_range is None or date_range.days_count == 0:
                     # print("  [WARN] Could not determine date range for Layer 2 selection.") # Log Warn (Removed)
                     return "I couldn't determine the date range for which to select meals. Please specify the dates again."
                     
                start_date = date_range.start_date
                days_count = date_range.days_count
                # print(f"  Layer 2 using date range: Start={start_date}, Days={days_count}") # Log L2 Date Range (Removed)

                # Select meals based on existing intents in the DB
                # print("  Calling meal_selector.plan_meals_for_range...") # Log Meal Select Call (Removed)
                self.meal_selector.plan_meals_for_range(start_date, days_count)
                # print("  meal_selector.plan_meals_for_range finished.") # Log Meal Select Done (Removed)
                
                # Fetch the updated plan to show the user
                # print("  Fetching updated plan for response...") # Log Fetch Plan (Removed)
                response_content = "Okay, I've selected specific meals based on the planned intents:\n\n"
                end_date = start_date + timedelta(days=days_count - 1)
                current_check_date = start_date
                meals_found = False
                while current_check_date <= end_date:
                    daily_plan = self.tables['daily_planner'].read(current_check_date)
                    if daily_plan and daily_plan[0]:
                        day_data = daily_plan[0]
                        meal_ids = []
                        try:
                            loaded_ids = json.loads(day_data['meal_ids'] or '[]')
                            if isinstance(loaded_ids, list):
                                meal_ids = loaded_ids
                        except json.JSONDecodeError:
                            pass
                            
                        notes_text = day_data['notes'] or "No specific intents."
                        
                        response_content += f"**{current_check_date.strftime('%Y-%m-%d, %A')}**:\n"
                        if meal_ids:
                             meals_found = True
                             meal_names = []
                             for meal_id in meal_ids:
                                 saved_meal = self.tables['saved_meals'].read(meal_id)
                                 if saved_meal and saved_meal[0]:
                                     meal_names.append(f"{saved_meal[0]['name']} (Saved Meal)")
                                     continue
                                 new_idea = self.tables['new_meal_ideas'].read(meal_id)
                                 if new_idea and new_idea[0]:
                                      meal_names.append(f"{new_idea[0]['name']} (New Idea)")
                                      continue
                                 meal_names.append(f"Meal ID {meal_id}") 
                             response_content += f"  Meals: { ', '.join(meal_names) }\n"
                        else:
                            response_content += f"  Meals: None selected\n"
                    current_check_date += timedelta(days=1)
                    
                if not meals_found:
                    response_content = "I finished the selection process, but no specific meals were assigned based on the intents and available suggestions. You might need to add more recipes or adjust the intents."
                else:
                     response_content += "\nYour daily planner has been updated."
                # print("  Layer 2 response generation complete.") # Log L2 Done (Removed)
            
            # --- General Chat (Tool shouldn't have been called) --- 
            else: # GENERAL_CHAT or unexpected value
                # print("  [WARN] MealPlanningTool execute called for GENERAL_CHAT intent.") # Log General Chat (Removed)
                response_content = "I'm ready to help with meal planning. What period would you like to plan for, or would you like me to select meals based on existing intents?"

            # print("-- [MealPlanningTool] END execute (returning response) --") # Log Return (Removed)
            return response_content

        except Exception as e:
            # print(f"[FATAL ERROR] MealPlanningTool execution failed: {e}") # Log Fatal Error (Removed)
            print(traceback.format_exc()) # Keep actual error traceback
            # print("-- [MealPlanningTool] END execute (with error) --") # Log Error End (Removed)
            return "Sorry, I encountered an error during meal planning."

# --- Main function called by tool_router.py --- 

def handle_meal_planning_request(message_history: List) -> str:
    """Processes a meal planning request based on the conversation history."""
    # Create an instance of the meal planning tool
    # In a real application, this might manage state across turns, but here we create a fresh one
    planner = MealPlanningTool(init_tables()[0], init_tables()[1])
    
    # The tool router has already decided this is a meal planning request.
    # Now, use the internal router to decide between Layer 1 and Layer 2.
    intent = planner.router.determine_intent(message_history)
    print(f"[INFO - Meal Planner Tool] Determined internal intent: {intent}")
    
    if intent == "LAYER_1_INTENT_GENERATION":
        response_content = planner.execute(message_history)
    elif intent == "LAYER_2_MEAL_SELECTION":
        response_content = planner.execute(message_history)
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
