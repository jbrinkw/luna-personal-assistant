from app.db_functions import get_daily_notes_range
from meal_planning.meal_plan_in_stock_checker import MealPlanInStockChecker
from datetime import datetime

# Initialize checker and get current date
checker = MealPlanInStockChecker()
current_date = datetime.now().strftime('%Y-%m-%d')

# Get notes for today
notes_for_day = get_daily_notes_range(current_date, current_date)
missing_ingredients = set()

# Process today's note if it exists
if notes_for_day and notes_for_day[0]:
    _, _, note_content = notes_for_day[0]
    missing_ingredients.update(checker.get_missing_ingredients(note_content))

# Display results
print("\nShopping List Generated Successfully!")
print("\nMissing Ingredients:")
if missing_ingredients:
    for ingredient in sorted(missing_ingredients):
        print(f"- {ingredient}")
else:
    print("No missing ingredients found.")