# db_functions.py

"""
This module contains and object for each database table that includes
a CRUD functions for each table as well as a format function that
returns a string explaining the format used to interact with the table.
"""

import os
import sqlite3
from dotenv import load_dotenv
from datetime import date, datetime
import json
import random

# Load environment variables
load_dotenv()

# Define the path for the SQLite database file
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "chefbyte.db")

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = None
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # self.connect() # Connect explicitly or ensure connection in execute_query

    def connect(self):
        """Establish connection to the SQLite database."""
        if self.conn is None:
            try:
                self.conn = sqlite3.connect(self.db_path)
                # Use Row factory for dictionary-like access (optional but convenient)
                self.conn.row_factory = sqlite3.Row 
                print(f"Connected to SQLite database at: {self.db_path}")
                return True
            except sqlite3.Error as e:
                print(f"SQLite connection error: {e}")
                self.conn = None # Ensure conn is None if connection failed
                return False
        return True # Already connected

    def disconnect(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            print("Disconnected from SQLite database.")

    def execute_query(self, query, params=None, fetch=False):
        """Execute a SQL query."""
        if not self.connect(): # Ensure connection exists
             print("Cannot execute query, no database connection.")
             return None
             
        try:
            cursor = self.conn.cursor()
            if params:
                 # Use '?' placeholder for SQLite
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            result = None
            last_id = None

            if fetch:
                result = cursor.fetchall()
            # For INSERT statements that generate an ID
            elif query.strip().upper().startswith("INSERT"):
                 last_id = cursor.lastrowid

            self.conn.commit()
            cursor.close()

            # Return last inserted ID if applicable, otherwise fetch result
            return last_id if last_id is not None else result
        
        except sqlite3.Error as e:
            # No need to rollback explicitly for basic errors, commit handles transactions.
            # For complex transactions, manual rollback might be needed.
            print(f"SQLite query execution error: {e}")
            # Attempt to close cursor even if error occurred
            try:
                cursor.close()
            except: # cursor might not be defined if connection failed earlier
                pass 
            return None


class Inventory:
    def __init__(self, db):
        self.db = db
        self.table_name = "inventory"
    
    def format(self):
        return "inventory [id(int), name(text), quantity(text), expiration(text), ingredient_food_id(int)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity TEXT NOT NULL,
            expiration TEXT,
            ingredient_food_id INTEGER, 
            FOREIGN KEY (ingredient_food_id) REFERENCES ingredients_foods(id)
        )
        """
        # Ensure ingredients_foods table exists first (or handle potential error)
        # Might be better handled by init_tables ensuring order
        return self.db.execute_query(query)
    
    def create(self, name, quantity, expiration=None, ingredient_food_id=None):
        expiration_str = expiration.strftime('%Y-%m-%d') if isinstance(expiration, date) else expiration
        query = """
        INSERT INTO inventory (name, quantity, expiration, ingredient_food_id)
        VALUES (?, ?, ?, ?)
        """
        return self.db.execute_query(query, (name, quantity, expiration_str, ingredient_food_id))
    
    def read(self, item_id=None):
        if item_id:
            query = "SELECT * FROM inventory WHERE id = ?"
            return self.db.execute_query(query, (item_id,), fetch=True)
        else:
            query = "SELECT * FROM inventory"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, item_id, name=None, quantity=None, expiration=None, ingredient_food_id=None):
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if quantity is not None:
            updates.append("quantity = ?")
            params.append(quantity)
        
        if expiration is not None:
            updates.append("expiration = ?")
            expiration_str = expiration.strftime('%Y-%m-%d') if isinstance(expiration, date) else expiration
            params.append(expiration_str)
        
        if ingredient_food_id is not None:
            updates.append("ingredient_food_id = ?")
            params.append(ingredient_food_id)
        
        if not updates:
            return False
        
        query = f"UPDATE inventory SET {', '.join(updates)} WHERE id = ?"
        params.append(item_id)
        
        return self.db.execute_query(query, params)
    
    def delete(self, item_id):
        query = "DELETE FROM inventory WHERE id = ?"
        return self.db.execute_query(query, (item_id,))


class TasteProfile:
    def __init__(self, db):
        self.db = db
        self.table_name = "taste_profile"
    
    def format(self):
        return "taste_profile [profile(text)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS taste_profile (
            profile TEXT PRIMARY KEY
        )
        """
        return self.db.execute_query(query)
    
    def create(self, profile):
        query = """
        INSERT OR IGNORE INTO taste_profile (profile)
        VALUES (?)
        """
        return self.db.execute_query(query, (profile,))
    
    def read(self):
        query = "SELECT profile FROM taste_profile LIMIT 1"
        result = self.db.execute_query(query, fetch=True)
        return result[0]['profile'] if result else None
    
    def update(self, profile):
        query = """
        INSERT OR REPLACE INTO taste_profile (profile)
        VALUES (?)
        """
        return self.db.execute_query(query, (profile,))
    
    def delete(self):
        query = "DELETE FROM taste_profile"
        return self.db.execute_query(query)


def generate_unique_id(db, table_name, min_range, max_range):
    """Generate a unique random ID within the specified range"""
    while True:
        new_id = random.randint(min_range, max_range)
        # Check if ID exists in the table
        query = f"SELECT 1 FROM {table_name} WHERE id = ?"
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
        return "saved_meals [id(int), name(text), prep_time_minutes(int), ingredients(text), recipe(text)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS saved_meals (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            prep_time_minutes INTEGER NOT NULL,
            ingredients TEXT NOT NULL,
            recipe TEXT NOT NULL
        )
        """
        return self.db.execute_query(query)
    
    def create(self, name, prep_time_minutes, ingredients, recipe):
        # Convert ingredients list/tuple to JSON string if needed
        ingredients_json = json.dumps(ingredients) if isinstance(ingredients, (list, tuple)) else ingredients

        # Generate unique ID using existing function
        meal_id = generate_unique_id(self.db, self.table_name, self.id_min_range, self.id_max_range)

        # Use '?' placeholder, remove RETURNING id
        query = """
        INSERT INTO saved_meals (id, name, prep_time_minutes, ingredients, recipe)
        VALUES (?, ?, ?, ?, ?)
        """
        # Return the generated meal_id on success (execute_query returns None for successful non-fetch)
        success = self.db.execute_query(query, (meal_id, name, prep_time_minutes, ingredients_json, recipe))
        # We need to return the ID we generated if the insert was successful (None is returned by execute_query on success)
        # A better check would be needed if execute_query could return False on failure, but currently returns None for success or error.
        # Assuming None means success for non-fetch execute_query here.
        # A more robust check would involve trying to read the inserted ID or modifying execute_query.
        # For now, just return the ID we intended to insert.
        return meal_id # Assuming success if execute_query didn't raise/return error printout
    
    def read(self, meal_id=None):
        if meal_id:
            query = "SELECT * FROM saved_meals WHERE id = ?"
            return self.db.execute_query(query, (meal_id,), fetch=True)
        else:
            query = "SELECT * FROM saved_meals"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, meal_id, name=None, prep_time_minutes=None, ingredients=None, recipe=None):
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if prep_time_minutes is not None:
            updates.append("prep_time_minutes = ?")
            params.append(prep_time_minutes)
        
        if ingredients is not None:
            if isinstance(ingredients, list):
                ingredients = json.dumps(ingredients)
            updates.append("ingredients = ?")
            params.append(ingredients)
        
        if recipe is not None:
            updates.append("recipe = ?")
            params.append(recipe)
        
        if not updates:
            return False
        
        query = f"UPDATE saved_meals SET {', '.join(updates)} WHERE id = ?"
        params.append(meal_id)
        
        return self.db.execute_query(query, params)
    
    def delete(self, meal_id):
        query = "DELETE FROM saved_meals WHERE id = ?"
        return self.db.execute_query(query, (meal_id,))


class NewMealIdeas:
    def __init__(self, db):
        self.db = db
        self.table_name = "new_meal_ideas"
        # New meal ideas will use IDs in range 20000-29999
        self.id_min_range = 20000
        self.id_max_range = 29999
    
    def format(self):
        return "new_meal_ideas [id(int), name(text), prep_time(int), ingredients(text), recipe(text)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS new_meal_ideas (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            prep_time INTEGER NOT NULL,
            ingredients TEXT NOT NULL,
            recipe TEXT NOT NULL
        )
        """
        return self.db.execute_query(query)
    
    def create(self, name, prep_time, ingredients, recipe):
        # Convert ingredients list/tuple to JSON string
        ingredients_json = json.dumps(ingredients) if isinstance(ingredients, (list, tuple)) else ingredients

        # Generate unique ID
        meal_id = generate_unique_id(self.db, self.table_name, self.id_min_range, self.id_max_range)

        # Use '?' placeholder
        query = """
        INSERT INTO new_meal_ideas (id, name, prep_time, ingredients, recipe)
        VALUES (?, ?, ?, ?, ?)
        """
        # Return the generated ID assuming success
        self.db.execute_query(query, (meal_id, name, prep_time, ingredients_json, recipe))
        return meal_id # Assuming success
    
    def read(self, meal_id=None):
        if meal_id:
            query = "SELECT * FROM new_meal_ideas WHERE id = ?"
            return self.db.execute_query(query, (meal_id,), fetch=True)
        else:
            query = "SELECT * FROM new_meal_ideas"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, meal_id, name=None, prep_time=None, ingredients=None, recipe=None):
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if prep_time is not None:
            updates.append("prep_time = ?")
            params.append(prep_time)
        
        if ingredients is not None:
            if isinstance(ingredients, list):
                ingredients = json.dumps(ingredients)
            updates.append("ingredients = ?")
            params.append(ingredients)
        
        if recipe is not None:
            updates.append("recipe = ?")
            params.append(recipe)
        
        if not updates:
            return False
        
        query = f"UPDATE new_meal_ideas SET {', '.join(updates)} WHERE id = ?"
        params.append(meal_id)
        
        return self.db.execute_query(query, params)
    
    def delete(self, meal_id):
        query = "DELETE FROM new_meal_ideas WHERE id = ?"
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
        INSERT OR IGNORE INTO saved_meals_instock_ids (id)
        VALUES (?)
        """
        return self.db.execute_query(query, (meal_id,))
    
    def read(self, meal_id=None):
        if meal_id:
            query = "SELECT * FROM saved_meals_instock_ids WHERE id = ?"
            return self.db.execute_query(query, (meal_id,), fetch=True)
        else:
            query = "SELECT * FROM saved_meals_instock_ids"
            return self.db.execute_query(query, fetch=True)
    
    def delete(self, meal_id):
        query = "DELETE FROM saved_meals_instock_ids WHERE id = ?"
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
        INSERT OR IGNORE INTO new_meal_ideas_instock_ids (id)
        VALUES (?)
        """
        return self.db.execute_query(query, (meal_id,))
    
    def read(self, meal_id=None):
        if meal_id:
            query = "SELECT * FROM new_meal_ideas_instock_ids WHERE id = ?"
            return self.db.execute_query(query, (meal_id,), fetch=True)
        else:
            query = "SELECT * FROM new_meal_ideas_instock_ids"
            return self.db.execute_query(query, fetch=True)
    
    def delete(self, meal_id):
        query = "DELETE FROM new_meal_ideas_instock_ids WHERE id = ?"
        return self.db.execute_query(query, (meal_id,))


class DailyPlanner:
    def __init__(self, db):
        self.db = db
        self.table_name = "daily_planner"
    
    def format(self):
        return "daily_planner [day(text), notes(text), meal_ids(text)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS daily_planner (
            day TEXT PRIMARY KEY,
            notes TEXT,
            meal_ids TEXT
        )
        """
        return self.db.execute_query(query)
    
    def create(self, day, notes=None, meal_ids=None):
        # Convert meal_ids list/tuple to JSON string
        meal_ids_json = json.dumps(meal_ids) if isinstance(meal_ids, (list, tuple)) else meal_ids
        # Format date as string YYYY-MM-DD
        day_str = day.strftime('%Y-%m-%d') if isinstance(day, date) else day

        query = """
        INSERT INTO daily_planner (day, notes, meal_ids)
        VALUES (?, ?, ?) ON CONFLICT (day) DO UPDATE
        SET notes = excluded.notes, meal_ids = excluded.meal_ids
        """
        return self.db.execute_query(query, (day_str, notes, meal_ids_json))
    
    def read(self, day=None):
        if day:
            # Format date as string
            day_str = day.strftime('%Y-%m-%d') if isinstance(day, date) else day
            query = "SELECT * FROM daily_planner WHERE day = ?"
            return self.db.execute_query(query, (day_str,), fetch=True)
        else:
            query = "SELECT * FROM daily_planner ORDER BY day"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, day, notes=None, meal_ids=None):
        updates = []
        params = []
        
        # Format date as string
        day_str = day.strftime('%Y-%m-%d') if isinstance(day, date) else day

        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        
        if meal_ids is not None:
            meal_ids_json = json.dumps(meal_ids) if isinstance(meal_ids, (list, tuple)) else meal_ids
            updates.append("meal_ids = ?")
            params.append(meal_ids_json)
        
        if not updates:
            return False
        
        query = f"UPDATE daily_planner SET {', '.join(updates)} WHERE day = ?"
        params.append(day_str)
        
        return self.db.execute_query(query, params)
    
    def delete(self, day):
        # Format date as string
        day_str = day.strftime('%Y-%m-%d') if isinstance(day, date) else day
        query = "DELETE FROM daily_planner WHERE day = ?"
        return self.db.execute_query(query, (day_str,))


class ShoppingList:
    def __init__(self, db):
        self.db = db
        self.table_name = "shopping_list"
    
    def format(self):
        return "shopping_list [id(int), amount(real)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY,
            amount REAL NOT NULL
        )
        """
        return self.db.execute_query(query)
    
    def create(self, item_id, amount):
        query = """
        INSERT INTO shopping_list (id, amount)
        VALUES (?, ?) ON CONFLICT (id) DO UPDATE
        SET amount = excluded.amount
        """
        return self.db.execute_query(query, (item_id, amount))
    
    def read(self, item_id=None):
        if item_id:
            query = "SELECT * FROM shopping_list WHERE id = ?"
            return self.db.execute_query(query, (item_id,), fetch=True)
        else:
            query = "SELECT * FROM shopping_list"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, item_id, amount):
        query = "UPDATE shopping_list SET amount = ? WHERE id = ?"
        return self.db.execute_query(query, (amount, item_id))
    
    def delete(self, item_id):
        query = "DELETE FROM shopping_list WHERE id = ?"
        return self.db.execute_query(query, (item_id,))


class IngredientsFood:
    def __init__(self, db):
        self.db = db
        self.table_name = "ingredients_foods"
    
    def format(self):
        return "ingredients_foods [id(int), name(text), min_amount_to_buy(int), walmart_link(text)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS ingredients_foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            min_amount_to_buy INTEGER NOT NULL,
            walmart_link TEXT
        )
        """
        return self.db.execute_query(query)
    
    def create(self, name, min_amount_to_buy, walmart_link=None):
        query = """
        INSERT INTO ingredients_foods (name, min_amount_to_buy, walmart_link)
        VALUES (?, ?, ?)
        """
        return self.db.execute_query(query, (name, min_amount_to_buy, walmart_link))
    
    def read(self, food_id=None):
        if food_id:
            query = "SELECT * FROM ingredients_foods WHERE id = ?"
            return self.db.execute_query(query, (food_id,), fetch=True)
        else:
            query = "SELECT * FROM ingredients_foods"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, food_id, name=None, min_amount_to_buy=None, walmart_link=None):
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if min_amount_to_buy is not None:
            updates.append("min_amount_to_buy = ?")
            params.append(min_amount_to_buy)
        
        if walmart_link is not None:
            updates.append("walmart_link = ?")
            params.append(walmart_link)
        
        if not updates:
            return False
        
        query = f"UPDATE ingredients_foods SET {', '.join(updates)} WHERE id = ?"
        params.append(food_id)
        
        return self.db.execute_query(query, params)
    
    def delete(self, food_id):
        query = "DELETE FROM ingredients_foods WHERE id = ?"
        return self.db.execute_query(query, (food_id,))


# Initialize all tables
def init_tables():
    # The Database class now handles the path and directory creation
    db = Database() 
    # Ensure connection is attempted before creating tables
    if not db.connect():
        print("Failed to connect to database. Aborting table initialization.")
        return None, None # Return None if connection fails

    # Define table classes in a dictionary for easy access
    table_classes = {
        "inventory": Inventory,
        "taste_profile": TasteProfile,
        "saved_meals": SavedMeals,
        "new_meal_ideas": NewMealIdeas,
        "saved_meals_instock_ids": SavedMealsInStockIds,
        "new_meal_ideas_instock_ids": NewMealIdeasInStockIds,
        "daily_planner": DailyPlanner,
        "shopping_list": ShoppingList,
        "ingredients_foods": IngredientsFood
    }
    
    # Define the explicit creation order
    # ingredients_foods must be created before inventory
    creation_order = [
        "ingredients_foods", 
        "inventory", # Depends on ingredients_foods
        "taste_profile", 
        "saved_meals", 
        "new_meal_ideas", 
        "saved_meals_instock_ids", # Technically depends on saved_meals
        "new_meal_ideas_instock_ids", # Technically depends on new_meal_ideas
        "daily_planner", 
        "shopping_list" # Technically depends on ingredients_foods for FK (though not enforced in schema)
    ]

    tables = {}
    print("Initializing database tables in specific order...")
    all_created = True
    for name in creation_order:
        if name in table_classes:
            print(f"Creating table: {name}...")
            table_obj = table_classes[name](db)
            tables[name] = table_obj
            # Check result of create_table (though it currently doesn't return specific success/fail)
            table_obj.create_table() 
            # We could add more robust checks here if needed (e.g., check if table exists after creation)
        else:
             print(f"[WARN] Table '{name}' defined in creation_order but not found in table_classes.")
             all_created = False
        
    # Check if any tables defined in classes were missed in the order
    for name in table_classes:
        if name not in creation_order:
             print(f"[WARN] Table '{name}' found in table_classes but not in creation_order. It was not created.")
             all_created = False
             
    if all_created:
        print("Database table initialization complete.")
    else:
        print("[ERROR] Database table initialization incomplete due to warnings.")
        
    # db.disconnect() # Optional: Disconnect after init if not needed immediately
    return db, tables