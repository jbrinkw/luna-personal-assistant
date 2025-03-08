import config
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from request_router import Router
from taste_preferences import update_taste_preferences_in_db
from inventory_manager import update_inventory_in_db
from adhoc_meal_recs import MealPlanner
from db_functions import get_inventory, get_taste_profile

default_model = ChatOpenAI(model="gpt-4o", api_key=config.OPENAI_API_KEY)

# System message that explains the default LLM's role:
system_message = SystemMessage(content=(
    "You are the default chat processor for this application. The app first checks the user's input "
    "with a routing module, which determines if specific updates (like inventory changes or taste preference updates) "
    "should be handled by dedicated modules. Those modules provide confirmation messages at the top of the response. "
    "Your job is to generate a plain text, conversational reply for any remaining part of the user's query. "
    "Do not use any special formatting (e.g., no markdown or triple quotes) and do not repeat or reference confirmation messages."
))
chat_history = [system_message]

# Initialize our router and meal suggestion engine
router_instance = Router()
meal_engine = MealPlanner()  

def conversation_history_to_string(history):
    # Convert conversation history to a simple string (ignoring system messages)
    return "\n".join([msg.content for msg in history if hasattr(msg, "content") and not msg.content.startswith("You are the")])

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break

    # Append user's message to chat history
    chat_history.append(HumanMessage(content=user_input))
    
    # --- Step 1: Call the Router ---
    router_output = router_instance.route_request(user_input)
    router_output_str = "Router Output: " + str(router_output)
    
    # --- Step 2: Process Focuses ---
    response_parts = [router_output_str]
    
    # Trigger Taste Preferences update if flagged
    if router_output.get("taste_preferences"):
        update_taste_preferences_in_db(user_input)
        response_parts.append("Taste preferences updated successfully.")
    
    # Trigger Inventory CRUD update if flagged
    if router_output.get("inventory"):
        current_inventory = get_inventory()  # Get current inventory as a string
        update_inventory_in_db(user_input, current_inventory)
        response_parts.append("Inventory updated successfully.")
    
    # --- Step 3: Generate the final chat response ---
    # Handle meal suggestion, meal planning, and order ingredients based on router output
    if router_output.get("meal_suggestion"):
        conv_str = conversation_history_to_string(chat_history)
        meal_response = meal_engine.generate_meal_plan(conv_str)
        response_parts.append("Meal Suggestions:\n" + meal_response)
    
    if router_output.get("meal_planning"):
        from meal_planner import MealPlanningSystem
        meal_planner_system = MealPlanningSystem()  # called with no args to use default planning settings
        planning_success = meal_planner_system.plan_meals()
        if planning_success:
            response_parts.append("Meal planning completed successfully.")
        else:
            response_parts.append("Meal planning encountered an error.")

    if router_output.get("order_ingredients"):
        from shopping_list_gen import ShoppingListGenerator
        shopping_gen = ShoppingListGenerator()
        raw_list, optimized_list, list_success = shopping_gen.generate_list(3)
        if list_success:
            shopping_items = " ".join([item.name for item in optimized_list])
            from walmart_agent import get_walmart_links
            walmart_response = get_walmart_links(shopping_items)
            response_parts.append("Walmart Order:\n" + str(walmart_response))
            response_parts.append("Optimized Shopping List:\n" + shopping_items)
        else:
            response_parts.append("Failed to generate shopping list.")

    # Fallback for queries that did not trigger the above focuses
    if not (router_output.get("meal_suggestion") or router_output.get("meal_planning") or router_output.get("order_ingredients")):
        taste_profile = get_taste_profile()
        current_inventory = get_inventory()
        fallback_history = chat_history.copy()
        fallback_history.append(SystemMessage(content=(
            f"Taste Profile:\n{taste_profile}\n\nCurrent Inventory:\n{current_inventory}"
        )))
        default_response = default_model.invoke(fallback_history).content
        response_parts.append(default_response)
    
    # --- Step 4: Build and output the final response ---
    final_response = "\n\n".join(response_parts)
    chat_history.append(AIMessage(content=final_response))
    
    print(f"AI: {final_response}\n")

