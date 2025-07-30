"""
helpers/pull_helper.py

Contains the PullHelper class responsible for fetching and formatting 
context data from various database tables for the agents.
"""

import os
import json
import traceback
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any

# Assuming db_functions is accessible from this path
# Adjust import path if necessary based on project structure
try:
    from db.db_functions import (
        Database, Inventory, TasteProfile, SavedMeals, ShoppingList, 
        IngredientsFood, DailyPlanner, NewMealIdeas, 
        SavedMealsInStockIds, NewMealIdeasInStockIds
    )
except ImportError:
    print("[ERROR] Could not import DB functions in pull_helper.py. Context fetching will fail.")
    # Define dummy classes or raise error if needed
    class Database: pass
    class Inventory: pass
    class TasteProfile: pass
    class SavedMeals: pass
    class ShoppingList: pass
    class IngredientsFood: pass
    class DailyPlanner: pass
    class NewMealIdeas: pass
    class SavedMealsInStockIds: pass
    class NewMealIdeasInStockIds: pass

class PullHelper:
    def __init__(self, db: Database, tables: Dict[str, Any]):
        """Initialize PullHelper with shared database connection and table objects."""
        if not db or not tables:
            raise ValueError("Database connection and tables dictionary are required for PullHelper.")
        self.db = db
        self.tables = tables
        print("[PullHelper] Initialized.")

    def get_inventory_context(self) -> str:
        """Fetches the user's current kitchen inventory from the database."""
        try:
            inventory_table = self.tables.get('inventory')
            if not inventory_table: return "Error: Inventory table not available."

            current_items = inventory_table.read()
            if not current_items:
                return "Your inventory is currently empty."

            context = "CURRENT INVENTORY:\n"
            for item in current_items:
                try: name = item['name']
                except KeyError: name = 'N/A'
                try: quantity = item['quantity']
                except KeyError: quantity = 'N/A'
                try: expiration = item['expiration']
                except KeyError: expiration = None
                expiration = expiration or 'N/A'

                context += f"- {name}: {quantity} (Expires: {expiration})\n"
            return context.strip()
        except Exception as e:
            print(f"[ERROR] PullHelper failed to get inventory context: {e}\n{traceback.format_exc()}")
            return "Error retrieving inventory."

    def get_taste_profile_context(self) -> str:
        """Fetches the user's saved taste profile."""
        try:
            taste_profile_table = self.tables.get('taste_profile')
            if not taste_profile_table: return "Error: TasteProfile table not available."
            
            profile = taste_profile_table.read()
            return f"TASTE PROFILE:\n{profile}" if profile else "No taste profile set."
        except Exception as e:
            print(f"[ERROR] PullHelper failed to get taste profile context: {e}\n{traceback.format_exc()}")
            return "Error retrieving taste profile."

    def get_saved_meals_context(self) -> str:
        """Fetches the list of saved meals."""
        try:
            saved_meals_table = self.tables.get('saved_meals')
            if not saved_meals_table: return "Error: SavedMeals table not available."

            all_meals = saved_meals_table.read()
            if not all_meals:
                return "No saved meals found."
            
            context = "SAVED MEALS:\n"
            for meal in all_meals:
                try: meal_id = meal['id']
                except KeyError: meal_id = 'N/A'
                try: name = meal['name']
                except KeyError: name = 'N/A'
                try: prep_time = meal['prep_time_minutes']
                except KeyError: prep_time = 'N/A'
                try: ingredients_col = meal['ingredients']
                except KeyError: ingredients_col = '[]'
                
                ingredients_text = "[Ingredients Error]"
                try:
                    ingredients_list = json.loads(ingredients_col) if isinstance(ingredients_col, str) else ingredients_col
                    if isinstance(ingredients_list, list):
                        formatted_ings = [f"{ing_data[1]} ({ing_data[2]})" for ing_data in ingredients_list if isinstance(ing_data, list) and len(ing_data) >= 3]
                        ingredients_text = ", ".join(formatted_ings) if formatted_ings else "(No ingredients listed)"
                    else:
                         ingredients_text = "[Invalid Ingredients Structure]"
                except (json.JSONDecodeError, TypeError, IndexError) as e:
                    print(f"[WARN] Error parsing ingredients for context (meal ID {meal_id}): {e}")

                context += f"- ID: {meal_id}, Name: {name}, Prep: {prep_time} mins, Ingredients: {ingredients_text}\n"
            
            return context.strip()
        except Exception as e:
            print(f"[ERROR] PullHelper failed to get saved meals context: {e}\n{traceback.format_exc()}")
            return "Error retrieving saved meals."

    def get_shopping_list_context(self) -> str:
        """Fetches the user's current shopping list."""
        try:
            shopping_list_table = self.tables.get('shopping_list')
            ingredients_table = self.tables.get('ingredients_foods')
            if not shopping_list_table or not ingredients_table: 
                return "Error: ShoppingList or IngredientsFood table not available."

            shopping_items = shopping_list_table.read()
            if not shopping_items:
                return "Shopping list is empty."
            
            all_ingredients = ingredients_table.read() # Use the connection stored in self.db implicitly
            if not all_ingredients:
                food_dict = {}
            else:
                # Build the dictionary mapping food ID to name
                food_dict = {ing['id']: ing['name'] for ing in all_ingredients if 'id' in ing and 'name' in ing}
                if not food_dict:
                    print("  [PullHelper] Warning: Ingredients found but could not build food_dict (check ID/name keys).")

            context = "SHOPPING LIST:\\n"
            for item in shopping_items:
                try: item_id = item['id']
                except KeyError: item_id = None
                if item_id is None: continue
                try: amount = item['amount']
                except KeyError: amount = 'N/A'

                name = food_dict.get(item_id, f"Unknown (ID: {item_id})")
                amount_str = f"{amount:.2f}" if isinstance(amount, float) and amount % 1 != 0 else str(amount)
                context += f"- {name}: {amount_str}\n"
            return context.strip()
        except Exception as e:
            print(f"[ERROR] PullHelper failed to get shopping list context: {e}\n{traceback.format_exc()}")
            return "Error retrieving shopping list."

    def get_daily_notes_context(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> str:
        """Fetch the user's meal plan for the given range.

        Args:
            start_date: Beginning of the desired range. Defaults to today.
            end_date: End of the range (inclusive). Defaults to one week from
                ``start_date``.

        Returns:
            A formatted string describing plans in the requested window or a
            message if none exist.
        """
        try:
            daily_planner_table = self.tables.get('daily_planner')
            saved_meals_table = self.tables.get('saved_meals')
            if not daily_planner_table or not saved_meals_table:
                return "Error: DailyPlanner or SavedMeals table not available."

            # Determine range defaults
            today = date.today()

            if start_date is None and end_date is None:
                start_dt = today
                end_dt = start_dt + timedelta(days=7)
            else:
                start_dt = start_date
                end_dt = end_date
                if isinstance(start_dt, str):
                    start_dt = datetime.strptime(start_dt, "%Y-%m-%d").date()
                if isinstance(end_dt, str):
                    end_dt = datetime.strptime(end_dt, "%Y-%m-%d").date()
                if start_dt is None and end_dt is not None:
                    start_dt = end_dt - timedelta(days=7)
                elif start_dt is not None and end_dt is None:
                    end_dt = start_dt + timedelta(days=7)

            tomorrow = today + timedelta(days=1)

            # Fetch entries within requested range
            all_entries = daily_planner_table.read(start_date=start_dt, end_date=end_dt)
            if not all_entries:
                return "No meal plans found for the specified range."
                
            context = ""
            found_entries = False
            
            all_saved_meals = saved_meals_table.read()
            saved_meals_dict = {meal['id']: meal['name'] for meal in all_saved_meals if 'id' in meal and 'name' in meal} if all_saved_meals else {}

            for entry in all_entries:
                try: entry_date_str = entry['day']
                except KeyError: entry_date_str = None
                if not entry_date_str: continue
                try:
                    entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    continue

                if start_dt <= entry_date <= end_dt:
                    found_entries = True
                    try: notes = entry['notes']
                    except KeyError: notes = None
                    notes = notes or "No notes"

                    try: meal_ids_json = entry['meal_ids']
                    except KeyError: meal_ids_json = None

                    meal_names = []
                    try:
                        meal_ids = json.loads(meal_ids_json or '[]') if isinstance(meal_ids_json, str) else meal_ids_json or []
                        if isinstance(meal_ids, list):
                            for mid in meal_ids:
                                try:
                                    meal_id_int = int(mid)
                                    meal_name = saved_meals_dict.get(meal_id_int)
                                    meal_names.append(meal_name if meal_name else f"Unknown (ID:{meal_id_int})")
                                except (ValueError, TypeError):
                                    meal_names.append(f"Invalid ID ({mid})")
                        else:
                            meal_names.append("[Invalid meal data]")
                    except (json.JSONDecodeError, TypeError):
                        meal_names.append("[Error parsing meal data]")
                        
                    meal_text = ", ".join(meal_names) if meal_names else "No meals planned"
                    relative_prefix = "Today " if entry_date == today else "Tomorrow " if entry_date == tomorrow else ""
                    formatted_date = entry_date.strftime("%A, %B %d")
                    context += f"{relative_prefix}({formatted_date}): {meal_text} (Notes: {notes})\n"
            
            return (
                context.strip()
                if found_entries
                else "No meal plans found for the specified range."
            )
        except Exception as e:
            print(f"[ERROR] PullHelper failed to get daily notes context: {e}\n{traceback.format_exc()}")
            return "Error retrieving daily meal plans."

    def get_new_meal_ideas_context(self) -> str:
        """Fetches the list of new meal ideas."""
        try:
            new_ideas_table = self.tables.get('new_meal_ideas')
            if not new_ideas_table: return "Error: NewMealIdeas table not available."

            all_ideas = new_ideas_table.read()
            if not all_ideas:
                return "No new meal ideas found."
            
            context = "NEW MEAL IDEAS:\n"
            for idea in all_ideas:
                try: idea_id = idea['id']
                except KeyError: idea_id = 'N/A'
                try: idea_name = idea['name']
                except KeyError: idea_name = 'N/A'
                try: idea_prep = idea['prep_time']
                except KeyError: idea_prep = 'N/A'
                context += f"- ID: {idea_id}, Name: {idea_name}, Prep: {idea_prep}m\n"
            return context.strip()
        except Exception as e:
            print(f"[ERROR] PullHelper failed to get new meal ideas context: {e}\n{traceback.format_exc()}")
            return "Error retrieving new meal ideas."
            
    def get_instock_meals_context(self) -> str:
        """Fetches meals (saved and new) that can be made with current inventory."""
        try:
            saved_instock_table = self.tables.get('saved_meals_instock_ids')
            new_instock_table = self.tables.get('new_meal_ideas_instock_ids')
            saved_meals_table = self.tables.get('saved_meals')
            new_ideas_table = self.tables.get('new_meal_ideas')
            
            if not all([saved_instock_table, new_instock_table, saved_meals_table, new_ideas_table]):
                 return "Error: Required tables for in-stock meals not available."

            saved_ids = [row['id'] for row in saved_instock_table.read() or []]
            new_ids = [row['id'] for row in new_instock_table.read() or []]
            
            context = "MEALS YOU CAN MAKE NOW:\n"
            context += "Saved Meals You Can Make:\n"
            if saved_ids:
                 all_saved_meals = saved_meals_table.read()
                 saved_meals_dict = {meal['id']: meal for meal in all_saved_meals if 'id' in meal} if all_saved_meals else {}
                 for meal_id in saved_ids:
                     meal_result = saved_meals_dict.get(meal_id)
                     if meal_result:
                         meal_name = meal_result['name'] if 'name' in meal_result else 'N/A'
                         meal_prep = meal_result['prep_time_minutes'] if 'prep_time_minutes' in meal_result else 'N/A'
                         context += f"- ID {meal_id}: {meal_name} ({meal_prep} mins)\n"
                     else: context += f"- Unknown Saved Meal (ID: {meal_id})\n"
            else: context += "(None)\n"
                 
            context += "\nNew Meal Ideas You Can Make:\n"
            if new_ids:
                 all_new_ideas = new_ideas_table.read()
                 new_ideas_dict = {idea['id']: idea for idea in all_new_ideas if 'id' in idea} if all_new_ideas else {}
                 for idea_id in new_ids:
                     idea_result = new_ideas_dict.get(idea_id)
                     if idea_result:
                         idea_name = idea_result['name'] if 'name' in idea_result else 'N/A'
                         idea_prep = idea_result['prep_time'] if 'prep_time' in idea_result else 'N/A'
                         context += f"- ID {idea_id}: {idea_name} ({idea_prep} mins)\n"
                     else: context += f"- Unknown New Idea (ID: {idea_id})\n"
            else: context += "(None)\n"
                 
            return context.strip()
        except Exception as e:
            print(f"[ERROR] PullHelper failed to get in-stock meals context: {e}\n{traceback.format_exc()}")
            return "Error retrieving in-stock meals."
            
    def get_ingredients_info_context(self) -> str:
        """Fetches general information about known ingredients."""
        try:
            ingredients_table = self.tables.get('ingredients_foods')
            if not ingredients_table: return "Error: IngredientsFood table not available."

            all_ingredients = ingredients_table.read()
            if not all_ingredients:
                return "No ingredients information available."
            
            context = "INGREDIENTS INFORMATION:\n"
            for ingredient in all_ingredients:
                try: link = ingredient['walmart_link']
                except KeyError: link = None
                link_text = f" | Link: {link}" if link else ""

                try: ing_id = ingredient['id']
                except KeyError: ing_id = 'N/A'
                try: ing_name = ingredient['name']
                except KeyError: ing_name = 'N/A'
                try: ing_min_buy = ingredient['min_amount_to_buy']
                except KeyError: ing_min_buy = 'N/A'

                context += f"- ID: {ing_id}, Name: {ing_name}, Min Buy: {ing_min_buy}{link_text}\n"
            return context.strip()
        except Exception as e:
            print(f"[ERROR] PullHelper failed to get ingredients info context: {e}\n{traceback.format_exc()}")
            return "Error retrieving ingredients information." 