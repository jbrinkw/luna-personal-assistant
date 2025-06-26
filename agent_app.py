from agents import Agent, Runner
from dotenv import load_dotenv
import os
import sys
import traceback
from langchain.schema import HumanMessage

# --- Import for Visualization ---

# --- Local Imports ---
# Ensure Python can find these modules. Add project root if needed.
project_root = os.path.dirname(os.path.abspath(__file__))  # Get the directory of agent_app.py
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# Also add parent if db is outside current dir? Adjust as needed.
parent_dir = os.path.dirname(project_root)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from agents_def import ChefByteAgent
    from agent_tools import (
        get_inventory_context, update_inventory,
        get_taste_profile_context, get_saved_meals_context, get_shopping_list_context,
        get_daily_notes_context, get_new_meal_ideas_context, get_instock_meals_context,
        get_ingredients_info_context,
        update_taste_profile, update_saved_meals, update_shopping_list, update_daily_plan
    )
    # Import functional tool wrappers
    from extracted_tool.tool import (
        run_meal_planner,
        run_meal_suggestion_generator,
        run_new_meal_ideator,
    )
    # original layer wrappers are also available if needed
    from db.db_functions import init_tables, Database
except ImportError as e:
    print(f"Error importing local modules: {e}")
    print(f"Current sys.path: {sys.path}")
    print("Please ensure 'agents_def.py', 'agent_tools.py', 'tools/' and the 'db' directory are structured correctly and accessible.")
    print("You might need to run this script from the project root directory or adjust sys.path insertion.")
    sys.exit(1)

load_dotenv()

# --- Specialized Agent Definitions ---

# 1. Context Agent (Handles GET requests - Pull Router equivalent)
context_tools = [
    get_inventory_context,
    get_taste_profile_context,
    get_saved_meals_context,
    get_shopping_list_context,
    get_daily_notes_context,
    get_new_meal_ideas_context,
    get_instock_meals_context,
    get_ingredients_info_context,
]
context_agent = Agent(
    name="ChefByte Context Agent",
    instructions=(
        "You are responsible for retrieving information for the user. "
        "Analyze the user's request (which led to this handoff) to determine *specifically* which pieces of information are needed. "
        "Use the appropriate tool to fetch the required data. "
        "Return the fetched information clearly."
    ),
    tools=context_tools,
    model="gpt-4o-mini",
)

# 2. Update Agent (Handles PUT/POST/DELETE requests - Push Router equivalent)
update_tools = [
    update_inventory,
    update_taste_profile,
    update_saved_meals,
    update_shopping_list,
    # update_daily_plan, # Removed: Planning is now handled by Functional Tool Agent
]
update_agent = Agent(
    name="ChefByte Update Agent",
    instructions=(
        "You are responsible for updating the user's information in the system. "
        "Analyze the user's request (which led to this handoff) to determine *specifically* what needs to be changed "
        "(e.g., inventory item quantities, taste profile text, saving/deleting meals, adding/removing shopping items, modifying daily plans). "
        "Use the appropriate tool to perform the update(s). "
        "After using a tool, formulate a clear confirmation message for the user summarizing the changes made based on the tool's output. "
        "Handle requests to update multiple items if necessary by calling the appropriate tool multiple times or interpreting the tool's multi-update confirmation. "
        "Do not ask for confirmation before making changes; proceed with the update based on the request."
    ),
    tools=update_tools,
    model="gpt-4o-mini",
)

# 3. Functional Tool Agent (Handles complex tools like planning, suggestions - Tool Router equivalent)

# --- Functional Tool Wrappers ---


# Replace placeholder list with the actual wrapped tools
functional_tools = [
    run_meal_planner,
    run_meal_suggestion_generator,
    run_new_meal_ideator,
]

functional_tool_agent = Agent(
    name="ChefByte Functional Tool Agent",
    instructions=(
        "You handle complex user requests that require specialized tools beyond simple data retrieval or updates. "
        "Analyze the user's request (which led to this handoff). "
        "Determine which specialized tool (meal planning, meal suggestion, new meal idea generation) is most appropriate. "
        "Use the selected tool, passing the necessary details from the user's request. "
        "Present the result from the tool to the user."
    ),
    tools=functional_tools, # Use the list of real tool wrappers
    model="gpt-4o-mini",
)


# 4. Orchestrator Agent (Main routing agent)
# Uses the other agents as tools
orchestrator_tools = [
    context_agent.as_tool(
        tool_name="get_chefbyte_context",
        tool_description="Fetches current information like inventory, taste profile, saved meals, shopping list, daily plan, etc., based on the user's question."
    ),
    update_agent.as_tool(
        tool_name="update_chefbyte_data",
        tool_description="Updates information like inventory, taste profile, saved meals, shopping list, or daily plan based on the user's statement or request."
    ),
    functional_tool_agent.as_tool(
        tool_name="execute_chefbyte_complex_task",
        tool_description="Handles complex tasks such as multi-day meal planning, generating meal suggestions based on criteria, or creating entirely new recipe ideas."
    )
]

orchestrator_agent = Agent(
    name="ChefByte Orchestrator",
    instructions=(
        "You are ChefByte, a friendly and helpful cooking assistant. Your primary role is to understand the user's request, use your specialized tools (which are other agents) to get information or perform actions, and then synthesize the results into a final, coherent response for the user. "
        "Analyze the latest user message in the context of the conversation history. Determine the main goal: "
        "1. **Get Information:** User is asking FOR information (e.g., 'what's in inventory?', 'show plan', etc.). Use the 'get_chefbyte_context' tool. Present the information clearly. "
        "2. **Update Specific Item:** User is TELLING you information or asking to modify/add/delete ONE specific item related to inventory, taste profile, saved meals, or shopping list. Use the 'update_chefbyte_data' tool. Confirm the action using the tool's output. " # Allow confirmation synthesis
        "3. **Perform Complex Task / Planning:** User is asking for multi-step/generative tasks OR any request involving the daily meal plan OR multiple updates. Use the 'execute_chefbyte_complex_task' tool. Present the results from the tool. " # Allow result presentation
        "4. **General Conversation:** It's a greeting, thank you, or general chat. Respond directly and conversationally. "
        "CRITICAL: Be precise. If the request involves the daily plan OR multiple updates, use 'execute_chefbyte_complex_task'. Otherwise, if it's getting info, use 'get_chefbyte_context'. If it's updating a single non-plan item, use 'update_chefbyte_data'. "
        "Always formulate a complete, user-facing response based on the tool's output or your direct reply."
    ),
    # handoffs=[context_agent, update_agent, functional_tool_agent], # REMOVED handoffs
    tools=orchestrator_tools, # ADDED agents as tools
    model="gpt-4o-mini"
)


def main():
    print("Initializing ChefByte Agent App (Multi-Agent Mode)...")

    # Initialize Database (silent check)
    db = None
    try:
        print("Attempting initial database connection check...")
        db, tables = init_tables(verbose=False)
        if not db or not tables:
            raise ConnectionError("Failed to initialize database during startup check.")
        print("Initial database connection check successful.")
        if db and db.conn:
            db.disconnect(verbose=False)
            print("Closed initial check connection.")
        db = None
    except Exception as e:
        print(f"Warning: Could not initialize database during startup check: {e}")
        print("Agent will proceed, but database tools might fail if connection issues persist.")

    # --- Agent Initialization Check ---
    print("\n--- Defined Agents ---")
    all_agents = [orchestrator_agent, context_agent, update_agent, functional_tool_agent] # Added context_agent back
    for agent in all_agents:
        print(f"- {agent.name}")
        print(f"  Instructions: {agent.instructions[:100]}...") # Print snippet
        tool_names = [tool.name for tool in agent.tools] if agent.tools else "None"
        handoff_names = [handoff.name for handoff in agent.handoffs] if agent.handoffs else "None"
        print(f"  Tools: {tool_names}")
        print(f"  Handoffs: {handoff_names}")
    print("----------------------\n")

    # Check API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    # Setup Chat Loop
    print("--- ChefByte Agent Initialized (Multi-Agent) ---")
    print("Type 'quit' or 'exit' to end the chat.")

    # Initialize conversation history storage
    messages = []  # Renamed from chat_history and will store OpenAI message format

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["quit", "exit"]:
                print("Goodbye!")
                break

            # If we have existing conversation history, append the new user message
            if messages:
                messages.append({"role": "user", "content": user_input})
                # Use the full messages history as input to Runner.run_sync
                input_for_runner = messages
            else:
                # For the first message, just use the string
                input_for_runner = user_input

            # Debugging: Print the input being sent (optional, but helpful)
            # print(f"DEBUG: Sending to Runner: {input_for_runner[:100] if isinstance(input_for_runner, list) else input_for_runner}{'...' if isinstance(input_for_runner, list) and len(str(input_for_runner)) > 100 else ''}")

            # Use the Runner with the appropriate input (history or initial query)
            result = Runner.run_sync(orchestrator_agent, input_for_runner) # Pass history or input

            # Get the assistant's response
            assistant_response = result.final_output

            # Update messages with the complete conversation history from the result
            # This is the crucial step for maintaining memory
            messages = result.to_input_list()

            # Debugging: Print updated messages (optional)
            # print(f"DEBUG: Updated messages (showing first few): {str(messages[:3])[:200]}...")

            # Handle potential unicode errors when printing to console
            printable_response = assistant_response.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
            print(f"\nChefByte: {printable_response}")

            # --- Debugging Steps ---
            # The result object from run_sync might not have detailed steps like async.
            # If debugging is needed, consider using run for async or adding logging within tools/agents.
            # print("\n--- Agent Run Details (May be limited in sync mode) ---")
            # print(f"Final Output Agent: {result.final_agent.name if result.final_agent else 'N/A'}")
            # # Accessing internal steps might require delving into the result object structure
            # print("--- End Run Details ---")


        except Exception as e:
            print(f"\nError during agent execution: {e}")
            traceback.print_exc()
            print("Please try again.")
            print("(Continuing after error)")

    print("Application finished.")

if __name__ == "__main__":
    main()

