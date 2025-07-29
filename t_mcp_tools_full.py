warning: in the working copy of 'test_mcp_tools_full.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/test_mcp_tools_full.py b/test_mcp_tools_full.py[m
[1mindex f7b65f5..f1938b4 100644[m
[1m--- a/test_mcp_tools_full.py[m
[1m+++ b/test_mcp_tools_full.py[m
[36m@@ -13,7 +13,7 @@[m [mfrom debug.reset_db import reset_database[m
 from db.db_functions import Database, Inventory, TasteProfile, SavedMeals, ShoppingList, DailyPlanner, NewMealIdeas[m
 [m
 SERVER_SCRIPT = "mcp_server.py"[m
[31m-SERVER_URL = "http://localhost:8000/mcp"[m
[32m+[m[32mSERVER_URL = "http://localhost:8000/sse"[m
 [m
 class SimpleAgent:[m
     """Very basic agent that maps keyword phrases to MCP tools."""[m
[36m@@ -21,22 +21,22 @@[m [mclass SimpleAgent:[m
     def __init__(self, client: Client):[m
         self.client = client[m
         self.tool_map = {[m
[31m-            "inventory context": "get_inventory_context",[m
[31m-            "taste profile": "get_taste_profile_context",[m
[31m-            "saved meals": "get_saved_meals_context",[m
[31m-            "shopping list": "get_shopping_list_context",[m
[31m-            "daily plan": "get_daily_notes_context",[m
[31m-            "meal ideas": "get_new_meal_ideas_context",[m
[31m-            "meals i can make": "get_instock_meals_context",[m
[31m-            "ingredient info": "get_ingredients_info_context",[m
[31m-            "add to inventory": "update_inventory",[m
[31m-            "change taste": "update_taste_profile",[m
[31m-            "save meal": "update_saved_meals",[m
[31m-            "shopping add": "update_shopping_list",[m
[31m-            "plan update": "update_daily_plan",[m
[31m-            "plan meals": "run_meal_planner",[m
[31m-            "suggest meal": "run_meal_suggestion_generator",[m
[31m-            "new recipe": "run_new_meal_ideator",[m
[32m+[m[32m            "inventory context": "pull_get_inventory_context",[m
[32m+[m[32m            "taste profile": "pull_get_taste_profile_context",[m
[32m+[m[32m            "saved meals": "pull_get_saved_meals_context",[m
[32m+[m[32m            "shopping list": "pull_get_shopping_list_context",[m
[32m+[m[32m            "daily plan": "pull_get_daily_notes_context",[m
[32m+[m[32m            "meal ideas": "pull_get_new_meal_ideas_context",[m
[32m+[m[32m            "meals i can make": "pull_get_instock_meals_context",[m
[32m+[m[32m            "ingredient info": "pull_get_ingredients_info_context",[m
[32m+[m[32m            "add to inventory": "push_update_inventory",[m
[32m+[m[32m            "change taste": "push_update_taste_profile",[m
[32m+[m[32m            "save meal": "push_update_saved_meals",[m
[32m+[m[32m            "shopping add": "push_update_shopping_list",[m
[32m+[m[32m            "plan update": "push_update_daily_plan",[m
[32m+[m[32m            "plan meals": "action_run_meal_suggestion_generator",[m
[32m+[m[32m            "suggest meal": "action_run_meal_suggestion_generator",[m
[32m+[m[32m            "new recipe": "action_run_new_meal_ideator",[m
         }[m
 [m
     async def run(self, prompt: str) -> str:[m
[36m@@ -50,13 +50,18 @@[m [mclass SimpleAgent:[m
             return "(no tool matched)"[m
 [m
         args = {}[m
[31m-        if tool in {"update_inventory", "update_saved_meals", "update_shopping_list", "update_daily_plan"}:[m
[32m+[m[32m        if tool in {"push_update_inventory", "push_update_saved_meals", "push_update_shopping_list", "push_update_daily_plan"}:[m
             args["user_input"] = prompt[m
[31m-        elif tool in {"update_taste_profile", "run_meal_planner", "run_meal_suggestion_generator", "run_new_meal_ideator"}:[m
[32m+[m[32m        elif tool in {"push_update_taste_profile", "action_run_meal_suggestion_generator", "action_run_new_meal_ideator"}:[m
             args["user_request"] = prompt[m
         [m
         result = await self.client.call_tool(tool, args)[m
[31m-        return result.content[0].text if result.content else ""[m
[32m+[m[32m        if hasattr(result, 'content') and result.content:[m
[32m+[m[32m            return result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])[m
[32m+[m[32m        elif isinstance(result, list) and result:[m
[32m+[m[32m            return result[0].text if hasattr(result[0], 'text') else str(result[0])[m
[32m+[m[32m        else:[m
[32m+[m[32m            return str(result) if result else ""[m
 [m
 # Helper functions to read tables -------------------------------------------[m
 [m
