# db_functions.py

"""
This module contains and object for each database table that includes
a CRUD functions for each table as well as a format function that
returns a string explaining the format used to interact with the table.
"""

import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from datetime import date, datetime
import json
import random

# Load environment variables
load_dotenv()

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT")
            )
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        if self.conn:
            self.conn.close()
    
    def execute_query(self, query, params=None, fetch=False):
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            
            result = None
            if fetch:
                result = cursor.fetchall()
            
            self.conn.commit()
            cursor.close()
            return result
        except Exception as e:
            self.conn.rollback()
            print(f"Query execution error: {e}")
            return None


class Inventory:
    def __init__(self, db):
        self.db = db
        self.table_name = "inventory"
    
    def format(self):
        return "inventory [id(int), name(string), quantity(string), expiration(date)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            quantity VARCHAR(100) NOT NULL,
            expiration DATE
        )
        """
        return self.db.execute_query(query)
    
    def create(self, name, quantity, expiration=None):
        query = """
        INSERT INTO inventory (name, quantity, expiration)
        VALUES (%s, %s, %s) RETURNING id
        """
        result = self.db.execute_query(query, (name, quantity, expiration), fetch=True)
        return result[0][0] if result else None
    
    def read(self, item_id=None):
        if item_id:
            query = "SELECT * FROM inventory WHERE id = %s"
            return self.db.execute_query(query, (item_id,), fetch=True)
        else:
            query = "SELECT * FROM inventory"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, item_id, name=None, quantity=None, expiration=None):
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        
        if quantity is not None:
            updates.append("quantity = %s")
            params.append(quantity)
        
        if expiration is not None:
            updates.append("expiration = %s")
            params.append(expiration)
        
        if not updates:
            return False
        
        query = f"UPDATE inventory SET {', '.join(updates)} WHERE id = %s"
        params.append(item_id)
        
        return self.db.execute_query(query, params)
    
    def delete(self, item_id):
        query = "DELETE FROM inventory WHERE id = %s"
        return self.db.execute_query(query, (item_id,))


class TasteProfile:
    def __init__(self, db):
        self.db = db
        self.table_name = "taste_profile"
    
    def format(self):
        return "taste_profile [profile(string)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS taste_profile (
            profile TEXT PRIMARY KEY
        )
        """
        return self.db.execute_query(query)
    
    def create(self, profile):
        query = """
        INSERT INTO taste_profile (profile)
        VALUES (%s) ON CONFLICT (profile) DO NOTHING
        """
        return self.db.execute_query(query, (profile,))
    
    def read(self):
        query = "SELECT profile FROM taste_profile LIMIT 1"
        return self.db.execute_query(query, fetch=True)
    
    def update(self, profile):
        # First delete any existing profile
        self.delete()
        # Then insert the new profile
        return self.create(profile)
    
    def delete(self):
        query = "DELETE FROM taste_profile"
        return self.db.execute_query(query)


def generate_unique_id(db, table_name, min_range, max_range):
    """Generate a unique random ID within the specified range"""
    while True:
        new_id = random.randint(min_range, max_range)
        # Check if ID exists in the table
        query = f"SELECT 1 FROM {table_name} WHERE id = %s"
        result = db.execute_query(query, (new_id,), fetch=True)
        if not result:
            return new_id


class SavedMeals:
    def __init__(self, db):
        self.db = db
        self.table_name = "saved_meals"
        # Saved meals will use IDs in range 10000-19999
        self.id_min_range = 10000
        self.id_max_range = 19999
    
    def format(self):
        return "saved_meals [id(int), name(string), prep_time_minutes(int), ingredients(json), recipe(string)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS saved_meals (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            prep_time_minutes INTEGER NOT NULL,
            ingredients JSONB NOT NULL,
            recipe TEXT NOT NULL
        )
        """
        return self.db.execute_query(query)
    
    def create(self, name, prep_time_minutes, ingredients, recipe):
        # Convert ingredients tuple to JSON
        if isinstance(ingredients, list):
            ingredients_json = json.dumps(ingredients)
        else:
            ingredients_json = ingredients
        
        # Generate unique ID in saved meals range
        meal_id = generate_unique_id(self.db, self.table_name, self.id_min_range, self.id_max_range)
            
        query = """
        INSERT INTO saved_meals (id, name, prep_time_minutes, ingredients, recipe)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
        """
        result = self.db.execute_query(query, (meal_id, name, prep_time_minutes, ingredients_json, recipe), fetch=True)
        return result[0][0] if result else None
    
    def read(self, meal_id=None):
        if meal_id:
            query = "SELECT * FROM saved_meals WHERE id = %s"
            return self.db.execute_query(query, (meal_id,), fetch=True)
        else:
            query = "SELECT * FROM saved_meals"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, meal_id, name=None, prep_time_minutes=None, ingredients=None, recipe=None):
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        
        if prep_time_minutes is not None:
            updates.append("prep_time_minutes = %s")
            params.append(prep_time_minutes)
        
        if ingredients is not None:
            if isinstance(ingredients, list):
                ingredients = json.dumps(ingredients)
            updates.append("ingredients = %s")
            params.append(ingredients)
        
        if recipe is not None:
            updates.append("recipe = %s")
            params.append(recipe)
        
        if not updates:
            return False
        
        query = f"UPDATE saved_meals SET {', '.join(updates)} WHERE id = %s"
        params.append(meal_id)
        
        return self.db.execute_query(query, params)
    
    def delete(self, meal_id):
        query = "DELETE FROM saved_meals WHERE id = %s"
        return self.db.execute_query(query, (meal_id,))


class NewMealIdeas:
    def __init__(self, db):
        self.db = db
        self.table_name = "new_meal_ideas"
        # New meal ideas will use IDs in range 20000-29999
        self.id_min_range = 20000
        self.id_max_range = 29999
    
    def format(self):
        return "new_meal_ideas [id(int), name(string), prep_time(int), ingredients(json), recipe(string)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS new_meal_ideas (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            prep_time INTEGER NOT NULL,
            ingredients JSONB NOT NULL,
            recipe TEXT NOT NULL
        )
        """
        return self.db.execute_query(query)
    
    def create(self, name, prep_time, ingredients, recipe):
        # Convert ingredients tuple to JSON
        if isinstance(ingredients, list):
            ingredients_json = json.dumps(ingredients)
        else:
            ingredients_json = ingredients
        
        # Generate unique ID in new meal ideas range
        meal_id = generate_unique_id(self.db, self.table_name, self.id_min_range, self.id_max_range)
            
        query = """
        INSERT INTO new_meal_ideas (id, name, prep_time, ingredients, recipe)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
        """
        result = self.db.execute_query(query, (meal_id, name, prep_time, ingredients_json, recipe), fetch=True)
        return result[0][0] if result else None
    
    def read(self, meal_id=None):
        if meal_id:
            query = "SELECT * FROM new_meal_ideas WHERE id = %s"
            return self.db.execute_query(query, (meal_id,), fetch=True)
        else:
            query = "SELECT * FROM new_meal_ideas"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, meal_id, name=None, prep_time=None, ingredients=None, recipe=None):
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        
        if prep_time is not None:
            updates.append("prep_time = %s")
            params.append(prep_time)
        
        if ingredients is not None:
            if isinstance(ingredients, list):
                ingredients = json.dumps(ingredients)
            updates.append("ingredients = %s")
            params.append(ingredients)
        
        if recipe is not None:
            updates.append("recipe = %s")
            params.append(recipe)
        
        if not updates:
            return False
        
        query = f"UPDATE new_meal_ideas SET {', '.join(updates)} WHERE id = %s"
        params.append(meal_id)
        
        return self.db.execute_query(query, params)
    
    def delete(self, meal_id):
        query = "DELETE FROM new_meal_ideas WHERE id = %s"
        return self.db.execute_query(query, (meal_id,))


class SavedMealsInStockIds:
    def __init__(self, db):
        self.db = db
        self.table_name = "saved_meals_instock_ids"
    
    def format(self):
        return "saved_meals_instock_ids [id(int)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS saved_meals_instock_ids (
            id INTEGER PRIMARY KEY
        )
        """
        return self.db.execute_query(query)
    
    def create(self, meal_id):
        query = """
        INSERT INTO saved_meals_instock_ids (id)
        VALUES (%s) ON CONFLICT DO NOTHING
        """
        return self.db.execute_query(query, (meal_id,))
    
    def read(self, meal_id=None):
        if meal_id:
            query = "SELECT * FROM saved_meals_instock_ids WHERE id = %s"
            return self.db.execute_query(query, (meal_id,), fetch=True)
        else:
            query = "SELECT * FROM saved_meals_instock_ids"
            return self.db.execute_query(query, fetch=True)
    
    def delete(self, meal_id):
        query = "DELETE FROM saved_meals_instock_ids WHERE id = %s"
        return self.db.execute_query(query, (meal_id,))


class NewMealIdeasInStockIds:
    def __init__(self, db):
        self.db = db
        self.table_name = "new_meal_ideas_instock_ids"
    
    def format(self):
        return "new_meal_ideas_instock_ids [id(int)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS new_meal_ideas_instock_ids (
            id INTEGER PRIMARY KEY
        )
        """
        return self.db.execute_query(query)
    
    def create(self, meal_id):
        query = """
        INSERT INTO new_meal_ideas_instock_ids (id)
        VALUES (%s) ON CONFLICT DO NOTHING
        """
        return self.db.execute_query(query, (meal_id,))
    
    def read(self, meal_id=None):
        if meal_id:
            query = "SELECT * FROM new_meal_ideas_instock_ids WHERE id = %s"
            return self.db.execute_query(query, (meal_id,), fetch=True)
        else:
            query = "SELECT * FROM new_meal_ideas_instock_ids"
            return self.db.execute_query(query, fetch=True)
    
    def delete(self, meal_id):
        query = "DELETE FROM new_meal_ideas_instock_ids WHERE id = %s"
        return self.db.execute_query(query, (meal_id,))


class DailyPlanner:
    def __init__(self, db):
        self.db = db
        self.table_name = "daily_planner"
    
    def format(self):
        return "daily_planner [day(date), notes(string), meal_ids(json)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS daily_planner (
            day DATE PRIMARY KEY,
            notes TEXT,
            meal_ids JSONB
        )
        """
        return self.db.execute_query(query)
    
    def create(self, day, notes=None, meal_ids=None):
        if isinstance(meal_ids, list):
            meal_ids = json.dumps(meal_ids)
            
        query = """
        INSERT INTO daily_planner (day, notes, meal_ids)
        VALUES (%s, %s, %s) ON CONFLICT (day) DO UPDATE
        SET notes = EXCLUDED.notes, meal_ids = EXCLUDED.meal_ids
        """
        return self.db.execute_query(query, (day, notes, meal_ids))
    
    def read(self, day=None):
        if day:
            query = "SELECT * FROM daily_planner WHERE day = %s"
            return self.db.execute_query(query, (day,), fetch=True)
        else:
            query = "SELECT * FROM daily_planner ORDER BY day"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, day, notes=None, meal_ids=None):
        updates = []
        params = []
        
        if notes is not None:
            updates.append("notes = %s")
            params.append(notes)
        
        if meal_ids is not None:
            if isinstance(meal_ids, list):
                meal_ids = json.dumps(meal_ids)
            updates.append("meal_ids = %s")
            params.append(meal_ids)
        
        if not updates:
            return False
        
        query = f"UPDATE daily_planner SET {', '.join(updates)} WHERE day = %s"
        params.append(day)
        
        return self.db.execute_query(query, params)
    
    def delete(self, day):
        query = "DELETE FROM daily_planner WHERE day = %s"
        return self.db.execute_query(query, (day,))


class ShoppingList:
    def __init__(self, db):
        self.db = db
        self.table_name = "shopping_list"
    
    def format(self):
        return "shopping_list [id(int), amount(float)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY,
            amount FLOAT NOT NULL
        )
        """
        return self.db.execute_query(query)
    
    def create(self, item_id, amount):
        query = """
        INSERT INTO shopping_list (id, amount)
        VALUES (%s, %s) ON CONFLICT (id) DO UPDATE
        SET amount = EXCLUDED.amount
        """
        return self.db.execute_query(query, (item_id, amount))
    
    def read(self, item_id=None):
        if item_id:
            query = "SELECT * FROM shopping_list WHERE id = %s"
            return self.db.execute_query(query, (item_id,), fetch=True)
        else:
            query = "SELECT * FROM shopping_list"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, item_id, amount):
        query = "UPDATE shopping_list SET amount = %s WHERE id = %s"
        return self.db.execute_query(query, (amount, item_id))
    
    def delete(self, item_id):
        query = "DELETE FROM shopping_list WHERE id = %s"
        return self.db.execute_query(query, (item_id,))


class IngredientsFood:
    def __init__(self, db):
        self.db = db
        self.table_name = "ingredients_foods"
    
    def format(self):
        return "ingredients_foods [id(int), name(string), min_amount_to_buy(int), walmart_link(string)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS ingredients_foods (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            min_amount_to_buy INTEGER NOT NULL,
            walmart_link VARCHAR(255)
        )
        """
        return self.db.execute_query(query)
    
    def create(self, name, min_amount_to_buy, walmart_link=None):
        query = """
        INSERT INTO ingredients_foods (name, min_amount_to_buy, walmart_link)
        VALUES (%s, %s, %s) RETURNING id
        """
        result = self.db.execute_query(query, (name, min_amount_to_buy, walmart_link), fetch=True)
        return result[0][0] if result else None
    
    def read(self, food_id=None):
        if food_id:
            query = "SELECT * FROM ingredients_foods WHERE id = %s"
            return self.db.execute_query(query, (food_id,), fetch=True)
        else:
            query = "SELECT * FROM ingredients_foods"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, food_id, name=None, min_amount_to_buy=None, walmart_link=None):
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        
        if min_amount_to_buy is not None:
            updates.append("min_amount_to_buy = %s")
            params.append(min_amount_to_buy)
        
        if walmart_link is not None:
            updates.append("walmart_link = %s")
            params.append(walmart_link)
        
        if not updates:
            return False
        
        query = f"UPDATE ingredients_foods SET {', '.join(updates)} WHERE id = %s"
        params.append(food_id)
        
        return self.db.execute_query(query, params)
    
    def delete(self, food_id):
        query = "DELETE FROM ingredients_foods WHERE id = %s"
        return self.db.execute_query(query, (food_id,))


# Initialize all tables
def init_tables():
    db = Database()
    
    tables = {
        "inventory": Inventory(db),
        "taste_profile": TasteProfile(db),
        "saved_meals": SavedMeals(db),
        "new_meal_ideas": NewMealIdeas(db),
        "saved_meals_instock_ids": SavedMealsInStockIds(db),
        "new_meal_ideas_instock_ids": NewMealIdeasInStockIds(db),
        "daily_planner": DailyPlanner(db),
        "shopping_list": ShoppingList(db),
        "ingredients_foods": IngredientsFood(db)
    }
    
    # Create all tables
    for name, table_obj in tables.items():
        table_obj.create_table()
    
    return db, tables