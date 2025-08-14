"""
PostgreSQL database helpers and table accessors for ChefByte.

All ChefByte data now lives in the same PostgreSQL server used by CoachByte.
Connection settings are centralized in the repo root `db_config.py` and can be
switched between prod/test via DB_ENV=prod|test.
"""

from __future__ import annotations

import os
import json
import random
from datetime import date, datetime, timedelta

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# Import unified DB config from core.shared, ensuring repo root is on sys.path
try:
    from core.shared.db_config import get_connection, get_db_schema
except ModuleNotFoundError:
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..', '..')))
    from core.shared.db_config import get_connection, get_db_schema

# Load environment variables
load_dotenv()


class Database:
    def __init__(self):
        self.conn = None

    def connect(self, verbose: bool = True) -> bool:
        """Establish a PostgreSQL connection (if not already connected).

        Ensures the configured schema exists and sets search_path accordingly.
        """
        if self.conn is not None:
            return True
        try:
            self.conn = get_connection(autocommit=False)
            # Ensure schema exists if configured
            schema = get_db_schema()
            if schema:
                with self.conn.cursor() as cur:
                    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            if verbose:
                print("Connected to PostgreSQL database.")
            return True
        except Exception as e:
            if verbose:
                print(f"PostgreSQL connection error: {e}")
            self.conn = None
            return False

    def disconnect(self, verbose: bool = True) -> None:
        if self.conn:
            try:
                self.conn.close()
            finally:
                self.conn = None
            if verbose:
                print("Disconnected from PostgreSQL database.")

    def execute_query(self, query: str, params=None, fetch: bool = False):
        """Execute a SQL query against PostgreSQL.

        - Uses RealDictCursor so fetched rows are dicts
        - If `fetch=True`, returns a list of dicts
        - If the query contains `RETURNING`, returns the first row (dict) or
          single scalar value when appropriate
        - Otherwise returns True on success, None on failure
        """
        if not self.connect(verbose=False):
            print("Cannot execute query, no database connection.")
            return None

        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params or ())

            if fetch:
                rows = cursor.fetchall()
                self.conn.commit()
                cursor.close()
                return [dict(r) for r in rows]

            # Handle RETURNING automatically
            if "returning" in query.lower():
                one = cursor.fetchone()
                self.conn.commit()
                cursor.close()
                if one is None:
                    return None
                # If single column, return its value, else the dict row
                if len(one.keys()) == 1:
                    return list(one.values())[0]
                return dict(one)

            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"PostgreSQL query execution error: {e}")
            try:
                self.conn.rollback()
            except Exception:
                pass
            try:
                cursor.close()
            except Exception:
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
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            quantity TEXT NOT NULL,
            expiration TEXT,
            ingredient_food_id INTEGER REFERENCES ingredients_foods(id)
        )
        """
        # Ensure ingredients_foods table exists first (or handle potential error)
        # Might be better handled by init_tables ensuring order
        return self.db.execute_query(query)
    
    def create(self, name, quantity, expiration=None, ingredient_food_id=None):
        expiration_str = expiration.strftime('%Y-%m-%d') if isinstance(expiration, date) else expiration
        query = """
        INSERT INTO inventory (name, quantity, expiration, ingredient_food_id)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """
        return self.db.execute_query(query, (name, quantity, expiration_str, ingredient_food_id))
    
    def read(self, item_id=None):
        if item_id:
            query = "SELECT * FROM inventory WHERE id = %s"
            return self.db.execute_query(query, (item_id,), fetch=True)
        else:
            query = "SELECT * FROM inventory"
            return self.db.execute_query(query, fetch=True)
    
    def update(self, item_id, name=None, quantity=None, expiration=None, ingredient_food_id=None):
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
            expiration_str = expiration.strftime('%Y-%m-%d') if isinstance(expiration, date) else expiration
            params.append(expiration_str)
        
        if ingredient_food_id is not None:
            updates.append("ingredient_food_id = %s")
            params.append(ingredient_food_id)
        
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
        INSERT INTO taste_profile (profile)
        VALUES (%s)
        ON CONFLICT (profile) DO NOTHING
        """
        return self.db.execute_query(query, (profile,))
    
    def read(self):
        query = "SELECT profile FROM taste_profile LIMIT 1"
        result = self.db.execute_query(query, fetch=True)
        return result[0]['profile'] if result else None
    
    def update(self, profile):
        query = """
        INSERT INTO taste_profile (profile)
        VALUES (%s)
        ON CONFLICT (profile) DO UPDATE SET profile = EXCLUDED.profile
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
        VALUES (%s, %s, %s, %s, %s)
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
        VALUES (%s, %s, %s, %s, %s)
        """
        # Return the generated ID assuming success
        self.db.execute_query(query, (meal_id, name, prep_time, ingredients_json, recipe))
        return meal_id # Assuming success
    
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
        VALUES (%s)
        ON CONFLICT (id) DO NOTHING
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
        VALUES (%s)
        ON CONFLICT (id) DO NOTHING
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
        VALUES (%s, %s, %s)
        ON CONFLICT (day) DO UPDATE SET notes = EXCLUDED.notes, meal_ids = EXCLUDED.meal_ids
        """
        return self.db.execute_query(query, (day_str, notes, meal_ids_json))
    
    def read(self, day=None, start_date=None, end_date=None):
        """Read planner entries.

        Args:
            day: Specific day to fetch.
            start_date: Beginning of range (inclusive). Defaults to today when
                no date parameters are supplied.
            end_date: End of range (inclusive). Defaults to one week from
                ``start_date``.

        Returns:
            List of row dictionaries matching the query.
        """
        if day is not None:
            day_str = day.strftime('%Y-%m-%d') if isinstance(day, date) else day
            query = "SELECT * FROM daily_planner WHERE day = %s"
            return self.db.execute_query(query, (day_str,), fetch=True)

        today = date.today()

        if start_date is None and end_date is None:
            start_date = today
            end_date = start_date + timedelta(days=7)
        elif start_date is None:
            end_date = (
                datetime.strptime(end_date, '%Y-%m-%d').date()
                if isinstance(end_date, str)
                else end_date
            )
            start_date = end_date - timedelta(days=7)
        elif end_date is None:
            start_date = (
                datetime.strptime(start_date, '%Y-%m-%d').date()
                if isinstance(start_date, str)
                else start_date
            )
            end_date = start_date + timedelta(days=7)

        # Normalize any string inputs after default handling
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        query = "SELECT * FROM daily_planner WHERE day BETWEEN %s AND %s ORDER BY day"
        return self.db.execute_query(query, (start_str, end_str), fetch=True)
    
    def update(self, day, notes=None, meal_ids=None):
        updates = []
        params = []
        
        # Format date as string
        day_str = day.strftime('%Y-%m-%d') if isinstance(day, date) else day

        if notes is not None:
            updates.append("notes = %s")
            params.append(notes)
        
        if meal_ids is not None:
            meal_ids_json = json.dumps(meal_ids) if isinstance(meal_ids, (list, tuple)) else meal_ids
            updates.append("meal_ids = %s")
            params.append(meal_ids_json)
        
        if not updates:
            return False
        
        query = f"UPDATE daily_planner SET {', '.join(updates)} WHERE day = %s"
        params.append(day_str)
        
        return self.db.execute_query(query, params)
    
    def delete(self, day):
        # Format date as string
        day_str = day.strftime('%Y-%m-%d') if isinstance(day, date) else day
        query = "DELETE FROM daily_planner WHERE day = %s"
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
        VALUES (%s, %s)
        ON CONFLICT (id) DO UPDATE SET amount = EXCLUDED.amount
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
        return "ingredients_foods [id(int), name(text), min_amount_to_buy(int), walmart_link(text)]"
    
    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS ingredients_foods (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            min_amount_to_buy INTEGER NOT NULL,
            walmart_link TEXT
        )
        """
        return self.db.execute_query(query)
    
    def create(self, name, min_amount_to_buy, walmart_link=None):
        query = """
        INSERT INTO ingredients_foods (name, min_amount_to_buy, walmart_link)
        VALUES (%s, %s, %s)
        RETURNING id
        """
        return self.db.execute_query(query, (name, min_amount_to_buy, walmart_link))
    
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
def init_tables(verbose=True):
    # The Database class now handles the path and directory creation
    db = Database()
    # Connect silently within init_tables if verbose is False for the overall init
    if not db.connect(verbose=verbose): # Pass the verbose flag to connect
         print("Failed to connect to the database during initialization.")
         return None, None # Return None if connection fails
         
    tables = {}
    
    # Define table order based on potential dependencies (e.g., foreign keys)
    table_creation_order = [
        ("ingredients_foods", IngredientsFood),
        ("inventory", Inventory), # Depends on ingredients_foods
        ("taste_profile", TasteProfile),
        ("saved_meals", SavedMeals),
        ("new_meal_ideas", NewMealIdeas),
        ("saved_meals_instock_ids", SavedMealsInStockIds), # Depends on saved_meals
        ("new_meal_ideas_instock_ids", NewMealIdeasInStockIds), # Depends on new_meal_ideas
        ("daily_planner", DailyPlanner), # Depends on saved_meals, new_meal_ideas implicitly via usage
        ("shopping_list", ShoppingList) # Depends on ingredients_foods
    ]
    
    if verbose:
        print("Initializing database tables in specific order...")
        
    for name, table_class in table_creation_order:
        try:
            if verbose: print(f"Creating table: {name}...")
            table_instance = table_class(db)
            table_instance.create_table()
            tables[name] = table_instance
        except Exception as e:
            print(f"Error creating table {name}: {e}")
            # Decide if failure is critical - maybe disconnect and return None?
            # db.disconnect()
            # return None, None
            # For now, let's just print the error and continue, maybe some tables can still be used
    
    if verbose:
        print("Database table initialization complete.")
        
    # Keep connection open for potential immediate use, caller should disconnect
    # db.disconnect() # Remove explicit disconnect here
    
    return db, tables


def with_db(func):
    """Decorator to provide a temporary database connection and tables.

    The wrapped function should accept ``db`` and ``tables`` as its first two
    parameters. ``with_db`` handles connecting, initializing tables, and
    disconnecting automatically. Any exception raised by the wrapped function
    will be propagated after cleanup.
    """

    from functools import wraps
    from inspect import Signature, Parameter, signature

    @wraps(func)
    def wrapper(*args, **kwargs):
        db = None
        try:
            db, tables = init_tables(verbose=False)
            if not db or not tables:
                raise ConnectionError("DB init failed.")
            return func(db, tables, *args, **kwargs)
        finally:
            if db and db.conn:
                db.disconnect(verbose=False)
    # Adjust signature to hide db and tables parameters
    sig = signature(func)
    params = list(sig.parameters.values())[2:]
    wrapper.__signature__ = Signature(parameters=params, return_annotation=sig.return_annotation)

    return wrapper

