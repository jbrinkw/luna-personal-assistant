#!/usr/bin/env python
import psycopg2
import config

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASS,
            host=config.DB_HOST,
            port=config.DB_PORT
        )
        return conn
    except Exception as e:
        print("Database connection error:", e)
        return None

def run_query(query, params=None, commit=False):
    """
    Executes a SQL query.
    - If commit=True, commits the transaction and returns True on success.
    - Otherwise, returns the fetched results.
    """
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit:
            conn.commit()
            result = True
        else:
            result = cur.fetchall()
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print("Database query error:", e)
        try:
            conn.rollback()
        except Exception as rollback_err:
            print("Rollback error:", rollback_err)
        cur.close()
        conn.close()
        return None

def create_table(query):
    """Helper to create a table using the provided query."""
    return run_query(query, commit=True)

def execute_select(query, params=None) -> list:
    """
    Helper function to execute a select query.
    Returns a list of results, or an empty list if an error occurs.
    """
    conn = get_db_connection()
    if not conn:
        return []
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return rows
    except Exception as e:
        print("Error executing select query:", e)
        return []
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception as e:
                print("Error closing cursor:", e)
        conn.close()

def get_inventory():
    """
    Retrieves the current inventory from the database and returns a formatted string.
    Each item is formatted as:
      "name: quantity (Expiration: expiration_date)"
    If no expiration date exists, displays "N/A".
    """
    query = "SELECT name, quantity, expiration FROM inventory ORDER BY name ASC, expiration ASC"
    inventory = execute_select(query)
    if not inventory:
        return "Inventory is empty."
    lines = []
    for name, quantity, expiration in inventory:
        exp_str = expiration.strftime("%Y-%m-%d") if expiration is not None else "N/A"
        lines.append(f"{name}: {quantity} (Expiration: {exp_str})")
    return "\n".join(lines)

def get_taste_profile():
    """
    Retrieves the most recent taste profile from the database.
    Returns the profile text if available, otherwise an empty string.
    """
    query = "SELECT profile FROM taste_profile ORDER BY id DESC LIMIT 1"
    result = execute_select(query)
    if result:
        return result[0][0]
    return ""

def clear_table(table_name: str) -> bool:
    """
    Clears all rows from the specified table.
    Returns True if successful, otherwise False.
    """
    query = f"DELETE FROM {table_name}"
    result = run_query(query, commit=True)
    if result is True:
        print(f"Table '{table_name}' cleared successfully.")
        return True
    else:
        print(f"Error clearing table '{table_name}'.")
        return False

def get_all_table_names() -> list:
    """
    Retrieves all table names from the public schema of the database.
    Returns a list of table names.
    """
    query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    rows = execute_select(query)
    return [row[0] for row in rows]

def get_saved_meals() -> list:
    """
    Retrieves all saved meals from the database.
    Each meal is returned as a tuple: (id, name, prep_time, ingredients, recipe).
    Returns an empty list if no meals are found or on error.
    """
    query = "SELECT id, name, prep_time, ingredients, recipe FROM meals ORDER BY id"
    return execute_select(query)

def get_meal_ideas() -> list:
    """
    Retrieves all meal ideas from the database.
    Each meal idea is returned as a tuple: (id, name, prep_time, ingredients, recipe).
    Returns an empty list if no meal ideas are found or on error.
    """
    query = "SELECT id, name, prep_time, ingredients, recipe FROM new_meal_ideas ORDER BY id"
    return execute_select(query)

def get_meal_ideas_in_stock() -> list:
    """
    Retrieves meal ideas that are in stock from the database.
    Returns a list of meal IDs.
    """
    query = "SELECT id FROM meal_ideas_in_stock ORDER BY id"
    rows = execute_select(query)
    return [row[0] for row in rows]

def get_saved_meals_in_stock() -> list:
    """
    Retrieves saved meals that are in stock from the database.
    Returns a list of meal IDs.
    """
    query = "SELECT id FROM saved_meals_in_stock ORDER BY id"
    rows = execute_select(query)
    return [row[0] for row in rows]

def get_daily_notes_range(start_date: str, end_date: str) -> list:
    """
    Retrieves daily notes within a specified date range.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
    
    Returns:
        list: List of tuples containing (date string, day of week string, notes string)
              Empty list if no notes found or on error
              Notes will be 'No notes' if the entry exists but notes are NULL
    """
    query = """
    SELECT 
        TO_CHAR(date, 'YYYY-MM-DD'),
        TO_CHAR(date, 'Day'),
        COALESCE(notes, 'No notes')
    FROM daily_notes 
    WHERE date BETWEEN %s AND %s 
    ORDER BY date
    """
    
    try:
        rows = execute_select(query, (start_date, end_date))
        return [(date.strip(), day.strip(), notes) for date, day, notes in rows]
    except Exception as e:
        print(f"Error retrieving daily notes: {e}")
        return []


if __name__ == "__main__":
    if clear_table("meals"):
        print("Successfully cleared the 'meals' table.")
    else:
        print("Error clearing the 'meals' table.")
