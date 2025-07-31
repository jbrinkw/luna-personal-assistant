import streamlit as st
import sqlite3
import pandas as pd
import json
import requests
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any
import os

# Configuration
DB_PATH = "data/chefbyte.db"
PUSH_SERVER_URL = "http://localhost:8010"  # Push tools server for updates

@st.cache_resource
def get_db_connection():
    """Get a cached connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable dictionary-like access
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

@st.cache_data(ttl=5)
def get_table_data(table_name: str) -> List[Dict]:
    """Get all data from a specific table directly from the database."""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        data = [dict(row) for row in rows]

        return data
    except Exception as e:
        st.error(f"Error fetching {table_name}: {e}")
        return []

def call_push_tool(tool_name: str, user_input: str) -> str:
    """Call a push tool to update data."""
    try:
        url = f"{PUSH_SERVER_URL}/mcp"
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {"user_input": user_input}
            }
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if "result" in result and "content" in result["result"]:
                return result["result"]["content"]
            else:
                return "Update successful"
        else:
            return f"Error: HTTP {response.status_code}"
    except Exception as e:
        return f"Connection error: {str(e)}"

def display_inventory():
    """Display and manage inventory."""
    st.header("🏠 Inventory Management")
    
    # Auto-refresh
    if st.button("🔄 Refresh Inventory") or st.session_state.get('auto_refresh', False):
        st.session_state['auto_refresh'] = True
        time.sleep(0.1)
    
    # Get inventory data
    inventory_data = get_table_data("inventory")
    
    if inventory_data:
        df = pd.DataFrame(inventory_data)
        
        # Format the dataframe for better display
        if 'expiration' in df.columns:
            df['expiration'] = pd.to_datetime(df['expiration'], errors='coerce')
            df['days_until_expiry'] = (df['expiration'] - pd.Timestamp.now()).dt.days
        
        # Color code expiring items
        def color_expiring(val):
            if pd.isna(val) or val > 7:
                return 'background-color: white'
            elif val > 3:
                return 'background-color: yellow'
            else:
                return 'background-color: red'
        
        if 'days_until_expiry' in df.columns:
            styled_df = df.style.applymap(color_expiring, subset=['days_until_expiry'])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No inventory data available")
    
    # Add new item form
    with st.expander("➕ Add New Item"):
        with st.form("add_inventory_item"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Item Name")
                quantity = st.text_input("Quantity")
            
            with col2:
                expiration = st.date_input("Expiration Date", min_value=datetime.now().date())
                ingredient_food_id = st.number_input("Ingredient Food ID (optional)", min_value=0, value=0)
            
            if st.form_submit_button("Add Item"):
                if name and quantity:
                    # Direct database insert for immediate feedback
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO inventory (name, quantity, expiration, ingredient_food_id) VALUES (?, ?, ?, ?)",
                                (name, quantity, expiration.strftime('%Y-%m-%d'), ingredient_food_id if ingredient_food_id > 0 else None)
                            )
                            conn.commit()
                            get_table_data.clear()
                            st.success(f"Added {quantity} {name} to inventory")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database error: {e}")

def display_saved_meals():
    """Display and manage saved meals."""
    st.header("🍽️ Saved Meals")
    
    if st.button("🔄 Refresh Meals"):
        st.rerun()
    
    meals_data = get_table_data("saved_meals")
    
    if meals_data:
        df = pd.DataFrame(meals_data)
        
        # Parse ingredients JSON for better display
        if 'ingredients' in df.columns:
            df['ingredients_parsed'] = df['ingredients'].apply(
                lambda x: json.loads(x) if x and x != 'null' else []
            )
            df['ingredient_count'] = df['ingredients_parsed'].apply(len)
        
        # Display with better formatting
        for _, meal in df.iterrows():
            with st.expander(f"🍽️ {meal['name']} ({meal['prep_time_minutes']} min)"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write("**Recipe:**")
                    st.text_area("Recipe", meal['recipe'], height=150, key=f"recipe_{meal['id']}", disabled=True)
                
                with col2:
                    st.write("**Ingredients:**")
                    if 'ingredients_parsed' in meal and meal['ingredients_parsed']:
                        for ingredient in meal['ingredients_parsed']:
                            if isinstance(ingredient, list) and len(ingredient) >= 3:
                                st.write(f"• {ingredient[2]} {ingredient[1]}")
                    else:
                        st.write("No ingredients listed")
                
                # Delete button
                if st.button(f"🗑️ Delete {meal['name']}", key=f"delete_{meal['id']}"):
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM saved_meals WHERE id = ?", (meal['id'],))
                            conn.commit()
                            get_table_data.clear()
                            st.success(f"Deleted {meal['name']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting meal: {e}")
    else:
        st.info("No saved meals available")
    
    # Add new meal form
    with st.expander("➕ Add New Meal"):
        with st.form("add_meal"):
            name = st.text_input("Meal Name")
            prep_time = st.number_input("Prep Time (minutes)", min_value=1, value=30)
            ingredients = st.text_area("Ingredients (JSON format: [food_id, name, qty])")
            recipe = st.text_area("Recipe Instructions")
            
            if st.form_submit_button("Save Meal"):
                if name and recipe:
                    # Use push tool for consistency
                    result = call_push_tool("push_update_saved_meals", f"save meal {name}")
                    st.success(result)
                    st.rerun()

def display_shopping_list():
    """Display and manage shopping list."""
    st.header("🛒 Shopping List")
    
    if st.button("🔄 Refresh Shopping List"):
        st.rerun()
    
    shopping_data = get_table_data("shopping_list")
    ingredients_data = get_table_data("ingredients_foods")
    
    if shopping_data and ingredients_data:
        # Join shopping list with ingredients info
        ingredients_dict = {ing['id']: ing for ing in ingredients_data}
        
        shopping_with_names = []
        for item in shopping_data:
            ingredient_info = ingredients_dict.get(item['id'])
            if ingredient_info:
                shopping_with_names.append({
                    'id': item['id'],
                    'name': ingredient_info['name'],
                    'amount': item['amount'],
                    'min_amount': ingredient_info['min_amount_to_buy'],
                    'walmart_link': ingredient_info.get('walmart_link', '')
                })
        
        if shopping_with_names:
            df = pd.DataFrame(shopping_with_names)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Shopping list is empty")
    else:
        st.info("Shopping list is empty")
    
    # Add item to shopping list
    with st.expander("➕ Add to Shopping List"):
        with st.form("add_shopping_item"):
            # Get available ingredients
            ingredients_data = get_table_data("ingredients_foods")
            ingredient_options = {ing['name']: ing['id'] for ing in ingredients_data}
            
            if ingredient_options:
                selected_ingredient = st.selectbox("Select Ingredient", list(ingredient_options.keys()))
                amount = st.number_input("Amount", min_value=0.1, step=0.1, value=1.0)
                
                if st.form_submit_button("Add to List"):
                    ingredient_id = ingredient_options[selected_ingredient]
                    
                    # Direct database insert
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT OR REPLACE INTO shopping_list (id, amount) VALUES (?, ?)",
                                (ingredient_id, amount)
                            )
                            conn.commit()
                            get_table_data.clear()
                            st.success(f"Added {amount} {selected_ingredient} to shopping list")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database error: {e}")
            else:
                st.warning("No ingredients available in database")

def display_daily_planner():
    """Display and manage daily planner."""
    st.header("📅 Daily Planner")
    
    if st.button("🔄 Refresh Planner"):
        st.rerun()
    
    planner_data = get_table_data("daily_planner")
    
    if planner_data:
        # Sort by date
        df = pd.DataFrame(planner_data)
        df['day'] = pd.to_datetime(df['day'])
        df = df.sort_values('day')
        
        # Display in a calendar-like format
        for _, entry in df.iterrows():
            with st.expander(f"📅 {entry['day'].strftime('%Y-%m-%d')}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if entry['notes']:
                        st.write("**Notes:**")
                        st.write(entry['notes'])
                    
                    if entry['meal_ids']:
                        st.write("**Meal IDs:**")
                        try:
                            meal_ids = json.loads(entry['meal_ids'])
                            st.write(f"Planned meals: {', '.join(map(str, meal_ids))}")
                        except:
                            st.write(entry['meal_ids'])
                
                with col2:
                    if st.button(f"🗑️ Delete Entry", key=f"delete_planner_{entry['day']}"):
                        conn = get_db_connection()
                        if conn:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM daily_planner WHERE day = ?", (entry['day'].strftime('%Y-%m-%d'),))
                                conn.commit()
                                get_table_data.clear()
                                st.success(f"Deleted planner entry for {entry['day'].strftime('%Y-%m-%d')}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting entry: {e}")
    else:
        st.info("No daily planner entries")
    
    # Add planner entry
    with st.expander("➕ Add Planner Entry"):
        with st.form("add_planner_entry"):
            day = st.date_input("Date", min_value=datetime.now().date())
            notes = st.text_area("Notes")
            meal_ids = st.text_input("Meal IDs (comma separated)")
            
            if st.form_submit_button("Add Entry"):
                if day:
                    # Convert meal_ids to JSON
                    meal_ids_list = []
                    if meal_ids:
                        try:
                            meal_ids_list = [int(x.strip()) for x in meal_ids.split(',')]
                        except:
                            st.error("Invalid meal IDs format")
                            return
                    
                    # Direct database insert
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT OR REPLACE INTO daily_planner (day, notes, meal_ids) VALUES (?, ?, ?)",
                                (day.strftime('%Y-%m-%d'), notes, json.dumps(meal_ids_list))
                            )
                            conn.commit()
                            get_table_data.clear()
                            st.success(f"Added planner entry for {day.strftime('%Y-%m-%d')}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database error: {e}")

def display_taste_profile():
    """Display and manage taste profile."""
    st.header("👅 Taste Profile")
    
    if st.button("🔄 Refresh Profile"):
        st.rerun()
    
    profile_data = get_table_data("taste_profile")
    
    if profile_data:
        profile = profile_data[0]['profile']
        st.write("**Current Taste Profile:**")
        st.text_area("Profile", profile, height=200, disabled=True)
    else:
        st.info("No taste profile set")
    
    # Update taste profile
    with st.expander("✏️ Update Taste Profile"):
        with st.form("update_taste_profile"):
            profile = st.text_area("Taste Profile (likes, dislikes, dietary restrictions)")
            
            if st.form_submit_button("Update Profile"):
                if profile:
                    result = call_push_tool("push_update_taste_profile", profile)
                    st.success(result)
                    st.rerun()

def display_meal_ideas():
    """Display new meal ideas."""
    st.header("💡 New Meal Ideas")
    
    if st.button("🔄 Refresh Ideas"):
        st.rerun()
    
    ideas_data = get_table_data("new_meal_ideas")
    
    if ideas_data:
        for _, idea in pd.DataFrame(ideas_data).iterrows():
            with st.expander(f"💡 {idea['name']} ({idea['prep_time']} min)"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write("**Recipe:**")
                    st.text_area("Recipe", idea['recipe'], height=150, key=f"idea_recipe_{idea['id']}", disabled=True)
                
                with col2:
                    st.write("**Ingredients:**")
                    try:
                        ingredients = json.loads(idea['ingredients'])
                        for ingredient in ingredients:
                            if isinstance(ingredient, list) and len(ingredient) >= 3:
                                st.write(f"• {ingredient[2]} {ingredient[1]}")
                    except:
                        st.write("No ingredients listed")
                
                # Save to saved meals
                if st.button(f"💾 Save to Saved Meals", key=f"save_idea_{idea['id']}"):
                    # Use action tool to save
                    result = call_push_tool("push_update_saved_meals", f"save meal {idea['name']}")
                    st.success(result)
                    st.rerun()
    else:
        st.info("No new meal ideas available")

def display_ingredients_foods():
    """Display and manage ingredients foods."""
    st.header("🥕 Ingredients Foods")
    
    if st.button("🔄 Refresh Ingredients"):
        st.rerun()
    
    ingredients_data = get_table_data("ingredients_foods")
    
    if ingredients_data:
        df = pd.DataFrame(ingredients_data)
        
        # Display with better formatting
        for _, ingredient in df.iterrows():
            with st.expander(f"🥕 {ingredient['name']} (ID: {ingredient['id']})"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Min Amount to Buy:** {ingredient['min_amount_to_buy']}")
                    if ingredient.get('walmart_link'):
                        st.write(f"**Walmart Link:** [View on Walmart]({ingredient['walmart_link']})")
                
                with col2:
                    if st.button(f"🗑️ Delete {ingredient['name']}", key=f"delete_ingredient_{ingredient['id']}"):
                        conn = get_db_connection()
                        if conn:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM ingredients_foods WHERE id = ?", (ingredient['id'],))
                                conn.commit()
                                get_table_data.clear()
                                st.success(f"Deleted {ingredient['name']}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting ingredient: {e}")
        
        # Also show as a table for quick overview
        st.subheader("📋 Ingredients Overview")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No ingredients available")
    
    # Add new ingredient form
    with st.expander("➕ Add New Ingredient"):
        with st.form("add_ingredient"):
            name = st.text_input("Ingredient Name")
            min_amount = st.number_input("Min Amount to Buy", min_value=0.1, step=0.1, value=1.0)
            walmart_link = st.text_input("Walmart Link (optional)")
            
            if st.form_submit_button("Add Ingredient"):
                if name:
                    # Direct database insert
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO ingredients_foods (name, min_amount_to_buy, walmart_link) VALUES (?, ?, ?)",
                                (name, min_amount, walmart_link if walmart_link else None)
                            )
                            conn.commit()
                            get_table_data.clear()
                            st.success(f"Added {name} to ingredients")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Database error: {e}")

def display_instock_meals():
    """Display meals that can be cooked with current inventory."""
    st.header("✅ In-Stock Meals")
    
    if st.button("🔄 Refresh In-Stock Meals"):
        st.rerun()
    
    # Get all instock data
    saved_instock_data = get_table_data("saved_meals_instock_ids")
    new_ideas_instock_data = get_table_data("new_meal_ideas_instock_ids")
    saved_meals_data = get_table_data("saved_meals")
    new_meal_ideas_data = get_table_data("new_meal_ideas")
    
    # Create lookups for meal names and details
    saved_meals_dict = {meal['id']: meal for meal in saved_meals_data}
    new_ideas_dict = {idea['id']: idea for idea in new_meal_ideas_data}
    
    # Display Saved Meals that are in stock
    if saved_instock_data:
        st.subheader("🍽️ Saved Meals In Stock")
        for instock_meal in saved_instock_data:
            meal_id = instock_meal['id']
            meal_info = saved_meals_dict.get(meal_id)
            
            if meal_info:
                with st.expander(f"✅ {meal_info['name']} ({meal_info['prep_time_minutes']} min)"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write("**Recipe:**")
                        st.text_area("Recipe", meal_info['recipe'], height=100, key=f"saved_instock_recipe_{meal_id}", disabled=True)
                        
                        # Show ingredients if available
                        if meal_info.get('ingredients'):
                            st.write("**Ingredients:**")
                            try:
                                ingredients = json.loads(meal_info['ingredients'])
                                for ingredient in ingredients:
                                    if isinstance(ingredient, list) and len(ingredient) >= 3:
                                        st.write(f"• {ingredient[2]} {ingredient[1]}")
                            except:
                                st.write("Ingredients not available")
                    
                    with col2:
                        if st.button(f"🗑️ Remove from In-Stock", key=f"remove_saved_instock_{meal_id}"):
                            conn = get_db_connection()
                            if conn:
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM saved_meals_instock_ids WHERE id = ?", (meal_id,))
                                    conn.commit()
                                    get_table_data.clear()
                                    st.success(f"Removed {meal_info['name']} from in-stock list")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error removing meal: {e}")
            else:
                st.write(f"• Saved Meal ID {meal_id} (details not found)")
    else:
        st.info("No saved meals currently in stock")
    
    # Display New Meal Ideas that are in stock
    if new_ideas_instock_data:
        st.subheader("💡 New Meal Ideas In Stock")
        for instock_idea in new_ideas_instock_data:
            idea_id = instock_idea['id']
            idea_info = new_ideas_dict.get(idea_id)
            
            if idea_info:
                with st.expander(f"💡 {idea_info['name']} ({idea_info['prep_time']} min)"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write("**Recipe:**")
                        st.text_area("Recipe", idea_info['recipe'], height=100, key=f"idea_instock_recipe_{idea_id}", disabled=True)
                        
                        # Show ingredients if available
                        if idea_info.get('ingredients'):
                            st.write("**Ingredients:**")
                            try:
                                ingredients = json.loads(idea_info['ingredients'])
                                for ingredient in ingredients:
                                    if isinstance(ingredient, list) and len(ingredient) >= 3:
                                        st.write(f"• {ingredient[2]} {ingredient[1]}")
                            except:
                                st.write("Ingredients not available")
                    
                    with col2:
                        # Save to saved meals option
                        if st.button(f"💾 Save to Saved Meals", key=f"save_instock_idea_{idea_id}"):
                            result = call_push_tool("push_update_saved_meals", f"save meal {idea_info['name']}")
                            st.success(result)
                            st.rerun()
                        
                        # Remove from in-stock list
                        if st.button(f"🗑️ Remove from In-Stock", key=f"remove_idea_instock_{idea_id}"):
                            conn = get_db_connection()
                            if conn:
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM new_meal_ideas_instock_ids WHERE id = ?", (idea_id,))
                                    conn.commit()
                                    get_table_data.clear()
                                    st.success(f"Removed {idea_info['name']} from in-stock list")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error removing idea: {e}")
            else:
                st.write(f"• New Meal Idea ID {idea_id} (details not found)")
    else:
        st.info("No new meal ideas currently in stock")
    
    # Summary statistics
    if saved_instock_data or new_ideas_instock_data:
        st.subheader("📊 In-Stock Summary")
        col1, col2 = st.columns(2)
        col1.metric("Saved Meals In Stock", len(saved_instock_data))
        col2.metric("New Ideas In Stock", len(new_ideas_instock_data))

def display_database_stats():
    """Display database statistics."""
    st.header("📊 Database Statistics")
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Get table row counts
        tables = [
            "inventory", "taste_profile", "saved_meals", "new_meal_ideas",
            "daily_planner", "shopping_list", "ingredients_foods",
            "saved_meals_instock_ids", "new_meal_ideas_instock_ids"
        ]
        
        col1, col2, col3 = st.columns(3)
        
        for i, table in enumerate(tables):
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            if i % 3 == 0:
                col = col1
            elif i % 3 == 1:
                col = col2
            else:
                col = col3
            
            col.metric(table.replace('_', ' ').title(), count)
    
    except Exception as e:
        st.error(f"Error getting statistics: {e}")

def main():
    st.set_page_config(
        page_title="ChefByte Dashboard",
        page_icon="🍳",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🍳 ChefByte Dashboard")
    st.markdown("Real-time database viewer and manager")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    pages = [
        "📊 Database Stats",
        "🏠 Inventory",
        "🥕 Ingredients Foods",
        "🍽️ Saved Meals",
        "🛒 Shopping List",
        "📅 Daily Planner",
        "👅 Taste Profile",
        "💡 Meal Ideas",
        "✅ In-Stock Meals",
    ]
    page = st.sidebar.radio("Jump to section:", pages,
                            index=pages.index(st.session_state.get('current_page', pages[0])))
    st.session_state['current_page'] = page
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.session_state['auto_refresh'] = True
        time.sleep(30)
        st.rerun()
    
    # Connection status
    st.sidebar.markdown("---")
    st.sidebar.subheader("Connection Status")
    
    # Test database connection
    conn = get_db_connection()
    db_status = "🟢 Connected" if conn else "🔴 Disconnected"
    st.sidebar.write(f"Database: {db_status}")
    
    # Test push tools connection
    try:
        response = requests.get(f"{PUSH_SERVER_URL}/health", timeout=5)
        push_status = "🟢 Connected" if response.status_code == 200 else "🔴 Disconnected"
    except:
        push_status = "🔴 Disconnected"
    
    st.sidebar.write(f"Push Tools: {push_status}")
    
    # Display selected page
    if page == "📊 Database Stats":
        display_database_stats()
    elif page == "🏠 Inventory":
        display_inventory()
    elif page == "🥕 Ingredients Foods":
        display_ingredients_foods()
    elif page == "🍽️ Saved Meals":
        display_saved_meals()
    elif page == "🛒 Shopping List":
        display_shopping_list()
    elif page == "📅 Daily Planner":
        display_daily_planner()
    elif page == "👅 Taste Profile":
        display_taste_profile()
    elif page == "💡 Meal Ideas":
        display_meal_ideas()
    elif page == "✅ In-Stock Meals":
        display_instock_meals()

if __name__ == "__main__":
    main()