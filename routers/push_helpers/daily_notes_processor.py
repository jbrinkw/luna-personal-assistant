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
    def __init__(self):
        # Initialize language model
        self.chat = ChatOpenAI(temperature=0)
        
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

    def get_plans_and_meals_info(self, db):
        """Get current plans and available meals for context"""
        # Initialize database classes
        daily_planner = DailyPlanner(db)
        saved_meals = SavedMeals(db)
        
        # Get current date info
        date_info = self.get_current_date_info()
        today = date_info["today_date_obj"]
        
        # Get plans for the next 7 days
        plans_text = "No current plans found."
        
        # Calculate date range (next 7 days)
        end_date = today + timedelta(days=7)
        
        # Get all daily planner entries
        all_entries = daily_planner.read()
        
        if all_entries:
            # Format entries
            formatted_entries = []
            
            for entry in all_entries:
                entry_date = entry[0]
                
                # Only include entries in the next 7 days
                if today <= entry_date <= end_date:
                    notes = entry[1] or "No notes"
                    
                    # Safely parse meal IDs
                    try:
                        if entry[2]:
                            if isinstance(entry[2], str):
                                meal_ids = json.loads(entry[2])
                            else:
                                # It might already be a Python object
                                meal_ids = entry[2]
                        else:
                            meal_ids = []
                    except Exception as e:
                        print(f"[WARNING] Error parsing meal IDs in get_plans_and_meals_info: {e}")
                        meal_ids = []
                    
                    meal_names = []
                    for mid in meal_ids:
                        meal = saved_meals.read(mid)
                        if meal and meal[0]:
                            meal_names.append(meal[0][1])
                        else:
                            meal_names.append(f"Unknown meal (ID: {mid})")
                    
                    meal_text = ", ".join(meal_names) if meal_names else "No meals"
                    
                    formatted_date = entry_date.strftime("%A, %B %d, %Y")
                    formatted_entries.append(f"{formatted_date}: {meal_text} (Notes: {notes})")
            
            if formatted_entries:
                plans_text = "\n".join(formatted_entries)
        
        # Get available meals
        meals_text = "No saved meals found."
        
        all_meals = saved_meals.read()
        if all_meals:
            formatted_meals = []
            
            for meal in all_meals:
                meal_id = meal[0]
                name = meal[1]
                formatted_meals.append(f"ID {meal_id}: {name}")
            
            if formatted_meals:
                meals_text = "\n".join(formatted_meals)
        
        return plans_text, meals_text

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
        """Extract daily plan items from natural language input"""
        # Prepare date information for context
        date_info = self.get_current_date_info()
        
        # Get current plans and available meals
        db = Database()
        plans_text, meals_text = self.get_plans_and_meals_info(db)
        db.disconnect()
        
        # Create prompt with current context
        prompt = ChatPromptTemplate.from_template(template=self.extraction_prompt_template)
        messages = prompt.format_messages(
            user_input=user_input,
            format_instructions=self.format_instructions,
            current_date=date_info["today"],
            current_weekday=date_info["current_weekday"],
            current_plans=plans_text,
            available_meals=meals_text
        )
        
        # Get response from LLM
        response = self.chat.invoke(messages)
        # print(f"[DEBUG] Extractor LLM raw output (truncated): '{response.content[:300]}...'")
        
        # Implement a fallback mechanism in case parsing fails
        try:
            extracted_items = self.output_parser.parse(response.content)
            
            # Normalize dates for any items with relative date references
            for i, item in enumerate(extracted_items.items):
                # If the target date is not already in YYYY-MM-DD format, parse it
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', item.target_date):
                    try:
                        # Convert the relative date to an actual date
                        actual_date = self.parse_relative_date(item.target_date)
                        # Update the target_date with the ISO format
                        item.target_date = actual_date.strftime('%Y-%m-%d')
                    except Exception as e:
                        print(f"[WARNING] Failed to normalize date '{item.target_date}': {e}")
                        # Keep the original date reference if parsing fails
            
            return extracted_items
        except Exception as e:
            print(f"[ERROR] Failed to parse extractor output: {e}")
            # Create a minimal valid output to allow the process to continue
            return DailyPlanItems(items=[])

    def find_meal_by_name(self, meal_name: str, db) -> Optional[int]:
        """Find a meal ID by name (case-insensitive)"""
        if not meal_name:
            return None
            
        saved_meals = SavedMeals(db)
        all_meals = saved_meals.read()
        if not all_meals:
            return None
            
        # First try exact match
        for meal in all_meals:
            if meal[1].lower() == meal_name.lower():
                return meal[0]
                
        # Then try partial match
        for meal in all_meals:
            if meal_name.lower() in meal[1].lower():
                return meal[0]
                
        return None

    def get_meal_name(self, meal_id: int, db) -> str:
        """Get the name of a meal by its ID"""
        saved_meals = SavedMeals(db)
        meal = saved_meals.read(meal_id)
        if meal and meal[0]:
            return meal[0][1]
        return f"Unknown meal (ID: {meal_id})"

    def process_daily_notes_changes(self, user_input: str) -> Tuple[bool, str]:
        """
        Process daily notes changes based on natural language input.
        Returns a tuple of (bool, str):
        - bool: True if any changes were made, False otherwise
        - str: Confirmation message with details of all changes made
        """
        # Initialize database connection
        db = Database()
        daily_planner = DailyPlanner(db)
        
        # Track all changes made
        changes_made = False
        confirmation_messages = []
        items_processed = 0
        
        try:
            # Extract daily plan items from natural language input
            plan_items = self.extract_daily_plan_items(user_input)
            
            # Process each item based on the operation determined by the LLM
            for i, item in enumerate(plan_items.items):
                # Convert relative date to actual date
                target_date = self.parse_relative_date(item.target_date)
                
                # Format the date for confirmation messages
                formatted_date = target_date.strftime("%A, %B %d, %Y")
                
                if item.operation.lower() == "add" or item.operation.lower() == "update":
                    # Determine the meal IDs to use
                    meal_ids = []
                    
                    # Use explicit meal IDs if provided
                    if item.meal_ids:
                        meal_ids = item.meal_ids
                    
                    # Look up meal names if provided
                    if item.meal_names:
                        for meal_name in item.meal_names:
                            meal_id = self.find_meal_by_name(meal_name, db)
                            if meal_id:
                                meal_ids.append(meal_id)
                    
                    # Check if this is an update to an existing entry
                    existing_plan = daily_planner.read(target_date)
                    
                    if existing_plan and existing_plan[0]:
                        # If updating an existing entry, preserve existing data if not specified
                        existing_notes = existing_plan[0][1]
                        
                        # Safely parse the existing meal IDs
                        try:
                            if existing_plan[0][2]:
                                if isinstance(existing_plan[0][2], str):
                                    existing_meal_ids = json.loads(existing_plan[0][2])
                                else:
                                    # It might already be a Python object
                                    existing_meal_ids = existing_plan[0][2]
                            else:
                                existing_meal_ids = []
                        except Exception as e:
                            print(f"[WARNING] Error parsing existing meal IDs: {e}")
                            existing_meal_ids = []
                        
                        # Use existing notes if new notes not specified
                        notes = item.notes if item.notes is not None else existing_notes
                        
                        # Use existing meal IDs if not replacing them
                        if not (item.meal_ids or item.meal_names):
                            meal_ids = existing_meal_ids
                        
                        # Convert meal_ids to JSON string if it's a list or keep as is if already a string
                        meal_ids_json = json.dumps(meal_ids) if meal_ids is not None else None
                        
                        # Update the plan
                        daily_planner.update(target_date, notes, meal_ids_json)
                        
                        # Create confirmation message
                        meal_names = [self.get_meal_name(mid, db) for mid in meal_ids]
                        meal_text = ", ".join(meal_names) if meal_names else "No meals"
                        
                        confirmation_messages.append(f"Updated plan for {formatted_date}:\nMeals: {meal_text}\nNotes: {notes}")
                        
                        changes_made = True
                        items_processed += 1
                    else:
                        # Create a new plan entry
                        notes = item.notes or ""
                        
                        # Convert meal_ids to JSON string if it's a list
                        meal_ids_json = json.dumps(meal_ids) if meal_ids else None
                        
                        daily_planner.create(target_date, notes, meal_ids_json)
                        
                        # Create confirmation message
                        meal_names = [self.get_meal_name(mid, db) for mid in meal_ids]
                        meal_text = ", ".join(meal_names) if meal_names else "No meals"
                        
                        confirmation_messages.append(f"Added new plan for {formatted_date}:\nMeals: {meal_text}\nNotes: {notes}")
                        
                        changes_made = True
                        items_processed += 1
                
                elif item.operation.lower() == "clear":
                    # Check if the entry exists
                    existing_plan = daily_planner.read(target_date)
                    
                    if existing_plan and existing_plan[0]:
                        # Delete the plan for this day
                        daily_planner.delete(target_date)
                        
                        confirmation_messages.append(f"Cleared all plans for {formatted_date}")
                        
                        changes_made = True
                        items_processed += 1
                    else:
                        confirmation_messages.append(f"No plans found for {formatted_date} to clear")
                
                elif item.operation.lower() == "remove":
                    # Check if the entry exists
                    existing_plan = daily_planner.read(target_date)
                    
                    if existing_plan and existing_plan[0]:
                        existing_notes = existing_plan[0][1]
                        
                        # Safely parse the existing meal IDs
                        try:
                            if existing_plan[0][2]:
                                if isinstance(existing_plan[0][2], str):
                                    existing_meal_ids = json.loads(existing_plan[0][2])
                                else:
                                    # It might already be a Python object
                                    existing_meal_ids = existing_plan[0][2]
                            else:
                                existing_meal_ids = []
                        except Exception as e:
                            print(f"[WARNING] Error parsing existing meal IDs for remove: {e}")
                            existing_meal_ids = []
                        
                        meals_to_remove = []
                        
                        # Use explicit meal IDs if provided
                        if item.meal_ids:
                            meals_to_remove = item.meal_ids
                        
                        # Look up meal names if provided
                        if item.meal_names:
                            for meal_name in item.meal_names:
                                meal_id = self.find_meal_by_name(meal_name, db)
                                if meal_id:
                                    meals_to_remove.append(meal_id)
                        
                        # Remove the specified meals from the existing list
                        new_meal_ids = [mid for mid in existing_meal_ids if mid not in meals_to_remove]
                        
                        # Convert to JSON string
                        new_meal_ids_json = json.dumps(new_meal_ids) if new_meal_ids else None
                        
                        # Update the plan with the filtered meal list
                        daily_planner.update(target_date, existing_notes, new_meal_ids_json)
                        
                        # Create confirmation message
                        removed_meal_names = [self.get_meal_name(mid, db) for mid in meals_to_remove]
                        removed_text = ", ".join(removed_meal_names) if removed_meal_names else "No meals"
                        
                        confirmation_messages.append(f"Removed meals from {formatted_date}: {removed_text}")
                        
                        changes_made = True
                        items_processed += 1
                    else:
                        confirmation_messages.append(f"No plans found for {formatted_date} to modify")
            
            # print(f"[DEBUG] Processed {items_processed} daily plan items. Changes: {confirmation_messages}")
            
            # Prepare confirmation message
            if confirmation_messages:
                confirmation = "DAILY PLAN CHANGES:\n"
                confirmation += "\n\n".join(confirmation_messages)
                
                return changes_made, confirmation
            else:
                return changes_made, "No changes were made to the daily plans."
                
        except Exception as e:
            print(f"[ERROR] Daily notes processor error: {e}")
            return False, f"Error processing daily plan changes: {e}"
        finally:
            # Disconnect from database
            db.disconnect()


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