from datetime import datetime, timedelta
from app.db_functions import get_daily_notes_range, get_db_connection, run_query
from meal_suggestions.adhoc_meal_recs import MealPlanner

class MealPlanningSystem:
    def __init__(self, days_to_plan: int = 3):
        self.days_to_plan = days_to_plan
        self.planner = MealPlanner()
        self.start_date = datetime.now()
        
    def get_inventory_restriction(self, current_date: datetime, planning_date: datetime) -> str:
        days_ahead = (planning_date - current_date).days
        if days_ahead <= 1:
            return "\nPlease only suggest meals that can be made with ingredients currently in stock."
        return "\nYou may suggest meals requiring ingredients not currently in stock."

    def append_daily_notes(self, date_str: str, new_content: str) -> bool:
        query = "SELECT COALESCE(notes, '') FROM daily_notes WHERE date = %s"
        existing_notes = run_query(query, (date_str,))
        
        if existing_notes:
            current_notes = existing_notes[0][0]
            updated_notes = current_notes + new_content
            update_query = "UPDATE daily_notes SET notes = %s WHERE date = %s"
            return run_query(update_query, (updated_notes, date_str), commit=True)
        else:
            insert_query = "INSERT INTO daily_notes (date, notes) VALUES (%s, %s)"
            return run_query(insert_query, (date_str, new_content), commit=True)

    def generate_meal_suggestions_prompt(self, current_date=None):
        if current_date is None:
            current_date = self.start_date
        
        actual_current_date = self.start_date
        week_ago = current_date - timedelta(days=6)
        current_date_str = current_date.strftime('%Y-%m-%d')
        week_ago_str = week_ago.strftime('%Y-%m-%d')
        
        daily_notes = get_daily_notes_range(week_ago_str, current_date_str)
        inventory_restriction = self.get_inventory_restriction(actual_current_date, current_date)
        
        prompt = f"""Based on the following meal history for the past 7 days, suggest meals for today ({current_date_str}).
Please avoid repeating recent meal patterns unless specifically noted in today's preferences.{inventory_restriction}

Previous meals:
{daily_notes}
include an estimate of the calories,macros, and ingrediants for each meal
include a quantity along with each ingredient
dont suggest new meal ideas
just output the meals in an ordered list
Please suggest 3 meals for today considering variety and any preferences mentioned in today's notes."""
        
        return prompt

    def plan_meals(self) -> bool:
        """
        Generate and store meal plans for specified number of days into the future.
        
        Returns:
            bool: True if successful, False if any errors occurred
        """
        try:
            print(f"Planning meals for the next {self.days_to_plan} days...")
            print("=" * 60)
            
            for day_offset in range(self.days_to_plan):
                target_date = self.start_date + timedelta(days=day_offset)
                prompt = self.generate_meal_suggestions_prompt(target_date)
                meal_suggestions = self.planner.generate_meal_plan(prompt)
                date_str = target_date.strftime('%Y-%m-%d')
                
                print(f"\nDay {day_offset + 1}: Planning meals for {date_str}")
                print("-" * 60)
                print("\nMeal Suggestions:")
                print(meal_suggestions)
                print("-" * 60)
                
                meal_note = f"\nPlanned meals for {date_str}:\n{meal_suggestions}"
                    
                if not self.append_daily_notes(date_str, meal_note):
                    print(f"Error saving meal plan for {date_str} to the database.")
                    return False
                    
                print(f"Meal plan for {date_str} has been saved to the database.")
            
            print("\nMeal planning completed successfully!")
            return True
            
        except Exception as e:
            print(f"\nError during meal planning: {str(e)}")
            return False

if __name__ == "__main__":
    planner = MealPlanningSystem(days_to_plan=3)
    success = planner.plan_meals()
    if success:
        print("Meal planning system executed successfully!")
    else:
        print("Meal planning system encountered errors.")