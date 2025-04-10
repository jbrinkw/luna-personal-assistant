import sys
import os
from dotenv import load_dotenv
from langchain.schema import HumanMessage, AIMessage
import traceback
import json

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Now import the function and necessary classes
try:
    from tools.meal_suggestion_gen import generate_meal_suggestions, MealSuggestionFilter, MealSuggestionFormatter
    # Import UserPreferences and ContextBuilder from the correct location
    from helpers.meal_suggestion_context_builder import MealSuggestionContextBuilder, UserPreferences 
    print("Successfully imported components.")
except ImportError as e:
    print(f"Error importing components: {e}")
    print("Please ensure the files exist and there are no circular dependencies.")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred during import: {e}")
    sys.exit(1)

# Load environment variables (especially OPENAI_API_KEY)
print("Loading environment variables...")
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY not found in environment variables.")

# Simulate a simple message history
test_history = [
    HumanMessage(content="Hi ChefByte!"),
    AIMessage(content="Hello! How can I help you with your meals today?"),
    HumanMessage(content="Suggest some quick meals I can make for dinner tonight."),
]

print("\n--- Starting Meal Suggestion Test ---")
print(f"Simulated History (using HumanMessage/AIMessage objects):")
for msg in test_history:
    print(f"- {type(msg).__name__}: {msg.content}")

try:
    # --- Step 1: Generate Context ---
    print("\n--- Step 1: Building Context ---")
    user_intent = "Suggest some quick meals I can make for dinner tonight."
    full_history = "\n".join([
        f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
        for msg in test_history[-5:]
    ])
    context_builder = MealSuggestionContextBuilder()

    # --- Analyze Preferences ---
    preferences = context_builder.analyze_user_preferences(user_intent)
    print("\n--- User Preferences (Analyzed) ---")
    print(preferences)
    print("-------------------------------------------")

    # --- Get Meal Options using analyzed preferences ---
    print("\n--- Getting Meal Options ---")
    meal_options = context_builder.get_meal_options(preferences, max_options=7)

    # --- Format the context string from the options obtained ---
    print("\n--- Formatting Meal Options into Context String ---")
    meal_context = context_builder.format_meal_suggestions(meal_options)

    print("\n--- Generated Meal Context ---")
    print(meal_context)
    print("-------------------------------")

    # --- Step 2: Filter Suggestions ---
    print("\n--- Step 2: Filtering Suggestions ---")
    suggestion_filter = MealSuggestionFilter()

    # --- Debug: Print Filter Prompt ---
    format_instructions = suggestion_filter.output_parser.get_format_instructions()
    prompt_template = suggestion_filter.filter_prompt
    formatted_prompt = prompt_template.format(
        meal_context=meal_context,
        user_intent=user_intent,
        format_instructions=format_instructions
    )
    print("\n--- Prompt Sent to Filter LLM ---")
    print(formatted_prompt)
    print("-------------------------------")

    # --- Call the LLM (Filter) ---
    print("\n--- Calling Filter LLM ---")
    raw_filter_response = suggestion_filter.chat.invoke(formatted_prompt)
    print("\n--- Raw Response from Filter LLM ---")
    print(raw_filter_response.content)
    print("------------------------------------")

    # --- Attempt Parsing ---
    print("\n--- Parsing Filter Response ---")
    meal_ids = []
    try:
        parsed_result = suggestion_filter.output_parser.parse(raw_filter_response.content)
        meal_ids = parsed_result.meal_ids
        print(f"Parsed Meal IDs: {meal_ids}")
    except Exception as parse_error:
        print(f"Pydantic parsing failed: {parse_error}")
        print("Attempting fallback regex extraction...")
        try:
            import re
            temp_ids = []
            # Simple regex to find numbers in the raw response (might need refinement)
            found = re.findall(r'\d+', raw_filter_response.content)
            if found:
                temp_ids = [int(fid) for fid in found]
            # Often the response might be like ```json\n{\n  "meal_ids": [1, 2, 3] ... }```
            # Try parsing JSON directly
            try:
                json_str_match = re.search(r'```json\n(\{.*?\})\n```', raw_filter_response.content, re.DOTALL)
                if json_str_match:
                    json_data = json.loads(json_str_match.group(1))
                    if 'meal_ids' in json_data and isinstance(json_data['meal_ids'], list):
                        temp_ids = [int(mid) for mid in json_data['meal_ids']]
                elif raw_filter_response.content.strip().startswith('{'): # Check if it's just JSON
                    json_data = json.loads(raw_filter_response.content.strip())
                    if 'meal_ids' in json_data and isinstance(json_data['meal_ids'], list):
                        temp_ids = [int(mid) for mid in json_data['meal_ids']]

            except (json.JSONDecodeError, TypeError) as json_e:
                print(f"Direct JSON parsing failed: {json_e}")

            meal_ids = temp_ids[:3] # Limit to 3 as a fallback
            print(f"Fallback Extracted Meal IDs: {meal_ids}")
        except Exception as fallback_error:
            print(f"Fallback extraction also failed: {fallback_error}")
            meal_ids = []

    # --- Step 3: Format Results ---
    print("\n--- Step 3: Formatting Results ---")
    formatter = MealSuggestionFormatter()
    final_output = formatter.format_meal_suggestions(meal_ids)
    print("\n--- Final Formatted Output ---")
    print(final_output)
    print("----------------------------")

    print("\n--- Test Completed ---")

except Exception as e:
    print(f"\n--- ERROR during test execution ---")
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")
    print("Traceback:")
    print(traceback.format_exc())
    print("--- Test Failed ---") 