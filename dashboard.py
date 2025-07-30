import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any

# Configuration
MCP_SERVER_URL = "http://localhost:8000"  # Main aggregated MCP server
PULL_SERVER_URL = "http://localhost:8020"  # Pull tools server
PUSH_SERVER_URL = "http://localhost:8010"  # Push tools server

# Database table schemas for reference
TABLE_SCHEMAS = {
    "inventory": ["id", "name", "quantity", "expiration", "ingredient_food_id"],
    "taste_profile": ["profile"],
    "saved_meals": ["id", "name", "prep_time_minutes", "ingredients", "recipe"],
    "new_meal_ideas": ["id", "name", "prep_time", "ingredients", "recipe"],
    "daily_planner": ["day", "notes", "meal_ids"],
    "shopping_list": ["id", "amount"],
    "ingredients_foods": ["id", "name", "min_amount_to_buy", "walmart_link"],
    "saved_meals_instock_ids": ["id"],
    "new_meal_ideas_instock_ids": ["id"]
}

def call_mcp_tool(server_url: str, tool_name: str, params: Dict = None) -> Dict:
    """Call an MCP tool and return the response."""
    try:
        url = f"{server_url}/mcp"
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params or {}
            }
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                return result["result"]
            else:
                return {"error": result.get("error", "Unknown error")}
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}

def get_table_data(table_name: str) -> List[Dict]:
    """Get all data from a specific table using pull tools."""
    tool_name = f"pull_get_{table_name}_context"
    result = call_mcp_tool(PULL_SERVER_URL, tool_name)
    
    if "error" in result:
        st.error(f"Error fetching {table_name}: {result['error']}")
        return []
    
    # Parse the returned text to extract structured data
    # This is a simplified approach - in practice, you'd want to modify pull tools
    # to return structured JSON instead of formatted text
    return []

def update_table_data(table_name: str, action: str, data: Dict) -> str:
    """Update data in a table using push tools."""
    tool_name = f"push_update_{table_name}"
    
    # Convert data to natural language for the push tools
    if table_name == "inventory":
        if action == "add":
            user_input = f"add {data.get('quantity', '1')} {data.get('name', '')}"
        elif action == "remove":
            user_input = f"remove {data.get('quantity', '1')} {data.get('name', '')}"
        elif action == "update":
            user_input = f"update {data.get('name', '')} to {data.get('quantity', '')}"
    elif table_name == "saved_meals":
        user_input = f"save meal {data.get('name', '')}"
    elif table_name == "shopping_list":
        user_input = f"add {data.get('name', '')} to shopping list"
    else:
        user_input = json.dumps(data)
    
    result = call_mcp_tool(PUSH_SERVER_URL, tool_name, {"user_input": user_input})
    
    if "error" in result:
        return f"Error: {result['error']}"
    else:
        return result.get("content", "Update successful")

def display_inventory():
    """Display and manage inventory."""
    st.header("🏠 Inventory Management")
    
    # Auto-refresh every 30 seconds
    if st.button("🔄 Refresh Inventory") or st.session_state.get('auto_refresh', False):
        st.session_state['auto_refresh'] = True
        time.sleep(0.1)  # Small delay to show refresh
    
    # Get inventory data
    inventory_data = get_table_data("inventory")
    
    if inventory_data:
        df = pd.DataFrame(inventory_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No inventory data available")
    
    # Add new item form
    with st.expander("➕ Add New Item"):
        with st.form("add_inventory_item"):
            name = st.text_input("Item Name")
            quantity = st.text_input("Quantity")
            expiration = st.date_input("Expiration Date", min_value=datetime.now().date())
            
            if st.form_submit_button("Add Item"):
                if name and quantity:
                    result = update_table_data("inventory", "add", {
                        "name": name,
                        "quantity": quantity,
                        "expiration": expiration.strftime('%Y-%m-%d')
                    })
                    st.success(result)
                    st.rerun()

def display_saved_meals():
    """Display and manage saved meals."""
    st.header("🍽️ Saved Meals")
    
    if st.button("🔄 Refresh Meals"):
        st.rerun()
    
    meals_data = get_table_data("saved_meals")
    
    if meals_data:
        df = pd.DataFrame(meals_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No saved meals available")
    
    # Add new meal form
    with st.expander("➕ Add New Meal"):
        with st.form("add_meal"):
            name = st.text_input("Meal Name")
            prep_time = st.number_input("Prep Time (minutes)", min_value=1)
            ingredients = st.text_area("Ingredients (JSON format)")
            recipe = st.text_area("Recipe Instructions")
            
            if st.form_submit_button("Save Meal"):
                if name and recipe:
                    result = update_table_data("saved_meals", "add", {
                        "name": name,
                        "prep_time_minutes": prep_time,
                        "ingredients": ingredients,
                        "recipe": recipe
                    })
                    st.success(result)
                    st.rerun()

def display_shopping_list():
    """Display and manage shopping list."""
    st.header("🛒 Shopping List")
    
    if st.button("🔄 Refresh Shopping List"):
        st.rerun()
    
    shopping_data = get_table_data("shopping_list")
    
    if shopping_data:
        df = pd.DataFrame(shopping_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Shopping list is empty")
    
    # Add item to shopping list
    with st.expander("➕ Add to Shopping List"):
        with st.form("add_shopping_item"):
            name = st.text_input("Item Name")
            amount = st.number_input("Amount", min_value=0.1, step=0.1)
            
            if st.form_submit_button("Add to List"):
                if name:
                    result = update_table_data("shopping_list", "add", {
                        "name": name,
                        "amount": amount
                    })
                    st.success(result)
                    st.rerun()

def display_daily_planner():
    """Display and manage daily planner."""
    st.header("📅 Daily Planner")
    
    if st.button("🔄 Refresh Planner"):
        st.rerun()
    
    planner_data = get_table_data("daily_planner")
    
    if planner_data:
        df = pd.DataFrame(planner_data)
        st.dataframe(df, use_container_width=True)
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
                    result = update_table_data("daily_planner", "add", {
                        "day": day.strftime('%Y-%m-%d'),
                        "notes": notes,
                        "meal_ids": meal_ids
                    })
                    st.success(result)
                    st.rerun()

def display_taste_profile():
    """Display and manage taste profile."""
    st.header("👅 Taste Profile")
    
    if st.button("🔄 Refresh Profile"):
        st.rerun()
    
    profile_data = get_table_data("taste_profile")
    
    if profile_data:
        st.json(profile_data)
    else:
        st.info("No taste profile set")
    
    # Update taste profile
    with st.expander("✏️ Update Taste Profile"):
        with st.form("update_taste_profile"):
            profile = st.text_area("Taste Profile (likes, dislikes, dietary restrictions)")
            
            if st.form_submit_button("Update Profile"):
                if profile:
                    result = update_table_data("taste_profile", "update", {
                        "profile": profile
                    })
                    st.success(result)
                    st.rerun()

def display_meal_ideas():
    """Display new meal ideas."""
    st.header("💡 New Meal Ideas")
    
    if st.button("🔄 Refresh Ideas"):
        st.rerun()
    
    ideas_data = get_table_data("new_meal_ideas")
    
    if ideas_data:
        df = pd.DataFrame(ideas_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No new meal ideas available")

def display_instock_meals():
    """Display meals that can be cooked with current inventory."""
    st.header("✅ In-Stock Meals")
    
    if st.button("🔄 Refresh In-Stock Meals"):
        st.rerun()
    
    instock_data = get_table_data("saved_meals_instock_ids")
    
    if instock_data:
        st.write("Meals you can cook with current inventory:")
        for meal in instock_data:
            st.write(f"- {meal.get('name', 'Unknown meal')}")
    else:
        st.info("No meals available with current inventory")

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
    page = st.sidebar.selectbox(
        "Choose a section:",
        [
            "🏠 Inventory",
            "🍽️ Saved Meals", 
            "🛒 Shopping List",
            "📅 Daily Planner",
            "👅 Taste Profile",
            "💡 Meal Ideas",
            "✅ In-Stock Meals"
        ]
    )
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.session_state['auto_refresh'] = True
        time.sleep(30)
        st.rerun()
    
    # Connection status
    st.sidebar.markdown("---")
    st.sidebar.subheader("Connection Status")
    
    # Test connections
    pull_status = "🟢 Connected" if call_mcp_tool(PULL_SERVER_URL, "pull_get_inventory_context") else "🔴 Disconnected"
    push_status = "🟢 Connected" if call_mcp_tool(PUSH_SERVER_URL, "push_update_inventory", {"user_input": "test"}) else "🔴 Disconnected"
    
    st.sidebar.write(f"Pull Tools: {pull_status}")
    st.sidebar.write(f"Push Tools: {push_status}")
    
    # Display selected page
    if page == "🏠 Inventory":
        display_inventory()
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