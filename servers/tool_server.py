from fastmcp import MCPServer
from extracted_tool.tool.tool_tools import (
    run_meal_planner,
    run_meal_suggestion_generator,
    run_new_meal_ideator,
    mealPlanning_layer1,
    mealPlanning_layer2,
    mealIdeation_layer1,
    mealIdeation_layer2,
    mealIdeation_layer3,
)

server = MCPServer("tool_server")

for tool in [
    run_meal_planner,
    run_meal_suggestion_generator,
    run_new_meal_ideator,
    mealPlanning_layer1,
    mealPlanning_layer2,
    mealIdeation_layer1,
    mealIdeation_layer2,
    mealIdeation_layer3,
]:
    server.register(tool)

app = server.app

if __name__ == "__main__":
    server.run(port=8003)
