from fastmcp import MCPServer
from extracted_tool.push.push_tools import (
    update_inventory,
    update_taste_profile,
    update_saved_meals,
    update_shopping_list,
    update_daily_plan,
)

server = MCPServer("push_server")

for tool in [
    update_inventory,
    update_taste_profile,
    update_saved_meals,
    update_shopping_list,
    update_daily_plan,
]:
    server.register(tool)

app = server.app

if __name__ == "__main__":
    server.run(port=8002)
