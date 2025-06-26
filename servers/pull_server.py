from fastmcp import MCPServer
from extracted_tool.pull.pull_tools import (
    get_inventory_context,
    get_taste_profile_context,
    get_saved_meals_context,
    get_shopping_list_context,
    get_daily_notes_context,
    get_new_meal_ideas_context,
    get_instock_meals_context,
    get_ingredients_info_context,
)

server = MCPServer("pull_server")

# Register all pull tools as endpoints
for tool in [
    get_inventory_context,
    get_taste_profile_context,
    get_saved_meals_context,
    get_shopping_list_context,
    get_daily_notes_context,
    get_new_meal_ideas_context,
    get_instock_meals_context,
    get_ingredients_info_context,
]:
    server.register(tool)

app = server.app

if __name__ == "__main__":
    server.run(port=8001)
