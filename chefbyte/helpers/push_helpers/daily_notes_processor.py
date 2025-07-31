"""
This module handles daily planner updates from natural language inputs.
It allows users to set, update, or clear plans for specific days.
"""

import os
import json
import re
from typing import List, Optional, Tuple, Dict, Any
from datetime import date, datetime, timedelta
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from db.db_functions import Database, DailyPlanner, SavedMeals
from dotenv import load_dotenv
import traceback # For detailed error logging

# Load environment variables
load_dotenv()

# Define models for extraction
class DailyPlanItem(BaseModel):
    """Model representing a daily plan update"""
    operation: str = Field(..., description="CRUD operation: add, update, clear, remove")
    target_date: str = Field(..., description="Date in YYYY-MM-DD format or relative reference like 'today', 'tomorrow', 'next monday'")
    notes: Optional[str] = Field(None, description="Notes for the day")
    meal_ids: Optional[List[int]] = Field(None, description="List of meal IDs to plan for this day")
    meal_names: Optional[List[str]] = Field(None, description="List of meal names to lookup and plan for this day")

class DailyPlanItems(BaseModel):
    """Collection of daily plan updates"""
    items: List[DailyPlanItem] = Field(..., description="List of daily plan items to be processed")

class DailyNotesProcessor:
    def __init__(self, daily_planner_table: DailyPlanner, saved_meals_table: SavedMeals, db: Database):
        """Initialize processor with shared table objects and DB connection."""
        self.daily_planner_table = daily_planner_table # Store passed object
        self.saved_meals_table = saved_meals_table # Store passed object
        self.db = db # Store passed DB connection
        
        # Initialize language model
        self.api_key = os.getenv("OPENAI_API_KEY") # Still needed for LLM call
        self.llm_model = "gpt-4o-mini" 
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, api_key=self.api_key)
        
        # Initialize the output parser
        self.output_parser = PydanticOutputParser(pydantic_object=DailyPlanItems)
        self.format_instructions = self.output_parser.get_format_instructions()
        
        # Extraction prompt template
        self.extraction_prompt_template = """
You are a helpful assistant that extracts information about daily meal plans from natural language inputs.

Extract all changes to a daily planner that the user wants to make, including:
1. The operation (add, update, remove, clear)
2. Target date (in ISO format YYYY-MM-DD)
3. Notes to add to the day
4. Meal IDs if explicitly mentioned
5. Meal names if mentioned

TODAY'S DATE IS: {current_date}
CURRENT DAY OF WEEK: {current_weekday}

IMPORTANT INSTRUCTIONS FOR DATE HANDLING:
- Always interpret dates relative to TODAY ({current_date}).
- For any weekday references, always use the UPCOMING occurrence (if today is {current_weekday} and the user mentions "{current_weekday}", that means TODAY).
- If the user doesn't specify "next" before a day name, assume they mean the closest future occurrence.
- Return ALL dates in ISO format (YYYY-MM-DD).
- For date ranges, extract each date in the range as a separate item.

Current daily plans:
{current_plans}

Available saved meals:
{available_meals}

User input: {user_input}

{format_instructions}
"""

        # Test functionality
        self.test_cases = {
            "clear_test": "Clear my plans for tomorrow",
            "add_test": "Add chicken curry to Wednesday's dinner",
            "update_test": "Change my meal for Friday to include lasagna",
            "remove_test": "Remove pizza from my Saturday plan",
            "notes_test": "Add a note to Sunday's plan: buy fresh ingredients"
        }

    def get_current_date_info(self):
        """Get information about the current date"""
        today = date.today()
        current_weekday = today.strftime("%A")
        formatted_today = today.strftime("%A, %B %d, %Y")
        
        return {
            "today": today.strftime("%Y-%m-%d"),
            "current_weekday": current_weekday,
            "formatted_today": formatted_today,
            "today_date_obj": today
        }

    def get_plans_and_meals_info(self):
        """Get current plans and available meals using shared objects."""
        # Use self.daily_planner_table and self.saved_meals_table
        daily_planner = self.daily_planner_table
        saved_meals = self.saved_meals_table
        try:
            date_info = self.get_current_date_info()
            today = date_info["today_date_obj"]
            end_date = today + timedelta(days=7)

            plans_text = "No current plans found."
            # Only fetch entries within the upcoming week
            all_entries = daily_planner.read(start_date=today, end_date=end_date)
            
            if all_entries:
                formatted_entries = []
                for entry in all_entries:
                    entry_date_str = entry['day']
                    try:
                        entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        continue 
                    
                    if today <= entry_date <= end_date:
                        notes = entry['notes'] or "No notes"
                        meal_ids_json = entry['meal_ids']
                        meal_names = []
                        try:
                            meal_ids = json.loads(meal_ids_json) if meal_ids_json and isinstance(meal_ids_json, str) else []
                            if isinstance(meal_ids, list):
                                for mid in meal_ids:
                                    try:
                                        meal_id_int = int(mid)
                                        meal_result = saved_meals.read(meal_id_int)
                                        if meal_result and meal_result[0]:
                                            meal_names.append(meal_result[0]['name'])
                                        else:
                                            meal_names.append(f"Unknown (ID:{meal_id_int})")
                                    except (ValueError, TypeError):
                                        meal_names.append(f"Invalid ID ({mid})")
                            else:
                                meal_names.append("[Invalid meal data]")
                        except (json.JSONDecodeError, TypeError):
                            meal_names.append("[Error parsing meal data]")
                            
                        meal_text = ", ".join(meal_names) if meal_names else "No meals"
                        formatted_date = entry_date.strftime("%A, %B %d")
                        formatted_entries.append(f"{formatted_date}: {meal_text} (Notes: {notes})")
                
                if formatted_entries:
                    plans_text = "\n".join(formatted_entries)
            
            meals_text = "No saved meals found."
            all_meals = saved_meals.read()
            if all_meals:
                formatted_meals = [f"ID {meal['id']}: {meal['name']}" for meal in all_meals]
                if formatted_meals:
                    meals_text = "\n".join(formatted_meals)
            
            return plans_text, meals_text
        except Exception as e:
             print(f"[ERROR] Failed to get plans and meals info in processor: {e}")
             return "Error retrieving plans.", "Error retrieving meals."
        # No disconnect

    def parse_relative_date(self, date_reference):
        """Parse a relative date reference like 'tomorrow' or 'next Monday'"""
        if not date_reference:
            return date.today()
            
        # Get today's date
        today = date.today()
        
        # Handle ISO format date strings (YYYY-MM-DD)
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_reference):
            try:
                parsed_date = datetime.strptime(date_reference, "%Y-%m-%d").date()
                return parsed_date
            except ValueError:
                pass  # If parse fails, continue with other methods
        
        # Convert to lowercase for easier matching
        date_reference = date_reference.lower().strip()
        
        # Simple relative dates
        if date_reference == 'today':
            return today
        elif date_reference == 'tomorrow':
            return today + timedelta(days=1)
        elif date_reference == 'yesterday':
            return today - timedelta(days=1)
            
        # Handle "X days from now" or "X days from today"
        days_match = re.match(r'(\d+)\s+days?\s+from\s+(now|today)', date_reference)
        if days_match:
            days = int(days_match.group(1))
            return today + timedelta(days=days)
            
        # Handle weekday names
        weekday_map = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2, 'weds': 2,
            'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }
        
        # First try to match "next weekday" pattern
        next_weekday_match = re.match(r'next\s+(\w+)', date_reference)
        if next_weekday_match:
            weekday = next_weekday_match.group(1).lower()
            if weekday in weekday_map:
                weekday_num = weekday_map[weekday]
                days_ahead = weekday_num - today.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                return today + timedelta(days=days_ahead)
                
        # Then try to match "this weekday" pattern
        this_weekday_match = re.match(r'this\s+(\w+)', date_reference)
        if this_weekday_match:
            weekday = this_weekday_match.group(1).lower()
            if weekday in weekday_map:
                weekday_num = weekday_map[weekday]
                days_ahead = weekday_num - today.weekday()
                if days_ahead < 0:  # Target day already happened this week
                    days_ahead += 7
                return today + timedelta(days=days_ahead)
                
        # Handle just the weekday name
        if date_reference in weekday_map:
            weekday = date_reference
            weekday_num = weekday_map[weekday]
            days_ahead = weekday_num - today.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        
        # If no match found, default to today
        return today

    def extract_daily_plan_items(self, user_input: str) -> DailyPlanItems:
        """Extract daily plan items from user input using LLM."""
        # Get context needed for the prompt
        current_plans, available_meals = self.get_plans_and_meals_info()
        date_info = self.get_current_date_info()
        
        prompt = ChatPromptTemplate.from_template(template=self.extraction_prompt_template)
        messages = prompt.format_messages(
            user_input=user_input,
            current_date=date_info["today"],
            current_weekday=date_info["current_weekday"],
            current_plans=current_plans,
            available_meals=available_meals,
            format_instructions=self.format_instructions
        )
        response = self.chat.invoke(messages)
        print(f"[DEBUG] Daily Plan Extractor LLM raw output (truncated): '{response.content[:300]}...'")
        
        try:
            extracted_items = self.output_parser.parse(response.content)
            return extracted_items
        except Exception as e:
            print(f"[ERROR] Failed to parse Daily Plan extractor output: {e}")
            return DailyPlanItems(items=[]) # Return empty list on failure

    def find_meal_by_name(self, meal_name: str) -> Optional[int]:
        """Find a saved meal ID by name using the shared saved_meals_table."""
        if not meal_name:
            return None
        
        # Use self.saved_meals_table
        saved_meals = self.saved_meals_table
        try:
            all_meals = saved_meals.read()
            if not all_meals:
                return None
                
            # Exact match
            for meal in all_meals:
                if meal['name'].lower() == meal_name.lower():
                    return meal['id']
                    
            # Partial match
            for meal in all_meals:
                if meal_name.lower() in meal['name'].lower():
                    return meal['id']
                    
            return None
        except Exception as e:
             print(f"[ERROR] Failed to find meal by name '{meal_name}' in daily notes processor: {e}")
             return None

    def get_meal_name(self, meal_id: int) -> str:
        """Get the name of a saved meal by its ID using the shared saved_meals_table."""
        # Use self.saved_meals_table
        saved_meals = self.saved_meals_table
        try:
            meal_result = saved_meals.read(meal_id) 
            if meal_result and meal_result[0]:
                return meal_result[0]['name']
            return f"Unknown meal (ID: {meal_id})"
        except Exception as e:
             print(f"[ERROR] Failed to get meal name for ID {meal_id} in daily notes processor: {e}")
             return f"Unknown meal (ID: {meal_id})"

    def process_daily_notes_changes(self, user_input: str) -> Tuple[bool, str]:
        """
        Process daily plan changes using shared table objects.
        """
        # Use self.daily_planner_table and self.saved_meals_table
        daily_planner = self.daily_planner_table
        saved_meals = self.saved_meals_table 
        
        changes_made = False
        confirmation_messages = []
        items_processed = 0
        
        try:
            # Extract plan items (uses shared objects via get_plans_and_meals_info)
            plan_items = self.extract_daily_plan_items(user_input)
            
            # Process each item
            for item in plan_items.items:
                target_date_obj = self.parse_relative_date(item.target_date)
                if not target_date_obj:
                    print(f"[WARN] Could not parse target date: {item.target_date}")
                    continue
                
                target_date_str = target_date_obj.strftime("%Y-%m-%d")
                
                meal_ids_to_process = item.meal_ids if item.meal_ids else []
                if item.meal_names:
                    for name in item.meal_names:
                        found_id = self.find_meal_by_name(name)
                        if found_id:
                            if found_id not in meal_ids_to_process:
                                meal_ids_to_process.append(found_id)
                        else:
                            print(f"[WARN] Could not find saved meal by name: {name}")
                
                # --- Handle Operations --- 
                op = item.operation.lower()
                
                if op == "clear":
                    delete_result = daily_planner.delete(target_date_str)
                    change_msg = f"Cleared plan for {target_date_str}"
                    confirmation_messages.append(change_msg)
                    changes_made = True
                    items_processed += 1

                elif op == "add" or op == "update":
                    existing_plan_result = daily_planner.read(target_date_str)
                    existing_notes = None
                    existing_meal_ids = []
                    if existing_plan_result and existing_plan_result[0]:
                        existing_plan = existing_plan_result[0]
                        existing_notes = existing_plan['notes']
                        try:
                            meal_ids_json = existing_plan['meal_ids']
                            existing_meal_ids = json.loads(meal_ids_json) if meal_ids_json and isinstance(meal_ids_json, str) else []
                            if not isinstance(existing_meal_ids, list):
                                existing_meal_ids = []
                        except (json.JSONDecodeError, TypeError):
                            existing_meal_ids = [] 
                    
                    final_notes = item.notes if item.notes is not None else existing_notes
                    final_meal_ids = list(existing_meal_ids)
                    
                    for meal_id in meal_ids_to_process:
                        if meal_id not in final_meal_ids:
                            final_meal_ids.append(meal_id)
                            
                    create_update_result = daily_planner.create(target_date_str, final_notes, final_meal_ids)
                    
                    meal_names_str = ", ".join([self.get_meal_name(mid) for mid in final_meal_ids]) or "No meals"
                    notes_str = f" | Notes: {final_notes}" if final_notes else ""
                    op_verb = "Updated" if existing_plan_result else "Added"
                    change_msg = f"{op_verb} plan for {target_date_str}: Meals=[{meal_names_str}]{notes_str}"
                    confirmation_messages.append(change_msg)
                    changes_made = True
                    items_processed += 1
                
                elif op == "remove":
                    existing_plan_result = daily_planner.read(target_date_str)
                    if existing_plan_result and existing_plan_result[0]:
                        existing_plan = existing_plan_result[0]
                        existing_notes = existing_plan['notes']
                        try:
                            meal_ids_json = existing_plan['meal_ids']
                            existing_meal_ids = json.loads(meal_ids_json) if meal_ids_json and isinstance(meal_ids_json, str) else []
                            if not isinstance(existing_meal_ids, list):
                                existing_meal_ids = []
                        except (json.JSONDecodeError, TypeError):
                             existing_meal_ids = []
                             
                        removed_meal_names = []
                        final_meal_ids = list(existing_meal_ids) # Start with current list
                        ids_actually_removed = []

                        for mid_to_remove in meal_ids_to_process:
                            if mid_to_remove in final_meal_ids:
                                final_meal_ids.remove(mid_to_remove)
                                removed_meal_names.append(self.get_meal_name(mid_to_remove))
                                ids_actually_removed.append(mid_to_remove)
                        
                        # Only proceed if something was actually removed
                        if ids_actually_removed:
                            if not final_meal_ids and not existing_notes:
                                daily_planner.delete(target_date_str)
                                change_msg = f"Removed meals ({', '.join(removed_meal_names)}) from {target_date_str}, clearing the day."
                            else:
                                daily_planner.update(target_date_str, notes=existing_notes, meal_ids=final_meal_ids)
                                change_msg = f"Removed meals ({', '.join(removed_meal_names)}) from {target_date_str}"
                                
                            confirmation_messages.append(change_msg)
                            changes_made = True
                            items_processed += 1
                        else:
                            print(f"[INFO] No specified meals to remove were found in plan for {target_date_str}")
                    else:
                        print(f"[WARN] No plan found for {target_date_str} to remove meals from.")
            
            # Construct final confirmation message
            if items_processed > 0:
                final_confirmation = f"DAILY PLAN UPDATE CONFIRMATION ({items_processed} operation(s))\n-------------------------------------\n" + "\n".join(confirmation_messages)
            else:
                final_confirmation = "No changes were detected or applied to the daily plan."
                
            return changes_made, final_confirmation
        except Exception as e:
            print(f"[ERROR] Daily notes processor error: {e}")
            import traceback
            print(traceback.format_exc())
            return False, f"Failed to process daily plan changes: {e}"
        # No disconnect


# Test function
def test_daily_notes_processor():
    """Test the DailyNotesProcessor with various scenarios"""
    processor = DailyNotesProcessor()
    
    # Test cases
    test_cases = [
        {
            "name": "Add a plan for today",
            "input": "Add spaghetti to my meal plan for today"
        },
        {
            "name": "Add a plan for tomorrow with notes",
            "input": "Plan to cook chicken curry tomorrow with notes to buy fresh ingredients"
        },
        {
            "name": "Update plans for a specific day",
            "input": "Update my meal plan for next Monday to include lasagna and garlic bread"
        },
        {
            "name": "Remove a specific meal",
            "input": "Remove spaghetti from today's meal plan"
        },
        {
            "name": "Clear plans for a day",
            "input": "Clear my plans for tomorrow"
        },
        {
            "name": "Add multiple meals for a day",
            "input": "Add pancakes for breakfast and steak for dinner on Saturday"
        }
    ]
    
    # Run tests in sequence
    for test in test_cases:
        print(f"\n--- TEST: {test['name']} ---")
        print(f"Input: {test['input']}")
        
        # Process the input
        result, message = processor.process_daily_notes_changes(test['input'])
        
        # Print results
        print(f"Success: {result}")
        print(f"Message: {message}")
        print("-" * 50)

if __name__ == "__main__":
    # Run the tests
    test_daily_notes_processor() 