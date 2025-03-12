import config
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from chat_processors.request_router import Router
from chat_processors.taste_preferences import update_taste_preferences_in_db
from chat_processors.inventory_manager import update_inventory_in_db
from meal_suggestions.adhoc_meal_recs import MealPlanner
from db_functions import get_inventory, get_taste_profile

class LunaAssistant:
    def __init__(self):
        self.default_model = ChatOpenAI(model="gpt-4o", api_key=config.OPENAI_API_KEY)
        self.system_message = SystemMessage(content=(
            "You are the default chat processor for this application. The app first checks the user's input "
            "with a routing module, which determines if specific updates (like inventory changes or taste preference updates) "
            "should be handled by dedicated modules. Those modules provide confirmation messages at the top of the response. "
            "Your job is to generate a plain text, conversational reply for any remaining part of the user's query. "
            "Do not use any special formatting (e.g., no markdown or triple quotes) and do not repeat or reference confirmation messages."
        ))
        self.chat_history = [self.system_message]
        self.router_instance = Router()
        self.meal_engine = MealPlanner()

    def _conversation_history_to_string(self):
        return "\n".join([msg.content for msg in self.chat_history 
                         if hasattr(msg, "content") and not msg.content.startswith("You are the")])

    def process_message(self, user_input: str) -> dict:
        """Process a single message and return structured response data"""
        
        self.chat_history.append(HumanMessage(content=user_input))
        
        # Step 1: Route the request
        router_output = self.router_instance.route_request(user_input)
        response_parts = [f"Router Output: {str(router_output)}"]
        
        # Step 2: Process focused updates
        if router_output.get("taste_preferences"):
            update_taste_preferences_in_db(user_input)
            response_parts.append("Taste preferences updated successfully.")
        
        if router_output.get("inventory"):
            current_inventory = get_inventory()
            update_inventory_in_db(user_input, current_inventory)
            response_parts.append("Inventory updated successfully.")
        
        # Step 3: Handle specific features
        if router_output.get("meal_suggestion"):
            conv_str = self._conversation_history_to_string()
            meal_response = self.meal_engine.generate_meal_plan(conv_str)
            response_parts.append(f"Meal Suggestions:\n{meal_response}")
        
        if router_output.get("meal_planning"):
            from meal_planning.meal_planner import MealPlanningSystem
            meal_planner = MealPlanningSystem()
            if meal_planner.plan_meals():
                response_parts.append("Meal planning completed successfully.")
            else:
                response_parts.append("Meal planning encountered an error.")

        if router_output.get("order_ingredients"):
            from shopping_list.shopping_list_gen import ShoppingListGenerator
            shopping_gen = ShoppingListGenerator()
            raw_list, optimized_list, list_success = shopping_gen.generate_list(3)
            if list_success:
                shopping_items = " ".join([item.name for item in optimized_list])
                from shopping_list.walmart_agent import get_walmart_links
                walmart_response = get_walmart_links(shopping_items)
                response_parts.append(f"Walmart Order:\n{str(walmart_response)}")
                response_parts.append(f"Optimized Shopping List:\n{shopping_items}")
            else:
                response_parts.append("Failed to generate shopping list.")

        # Handle general queries
        if not any(router_output.get(key) for key in ["meal_suggestion", "meal_planning", "order_ingredients"]):
            taste_profile = get_taste_profile()
            current_inventory = get_inventory()
            fallback_history = self.chat_history.copy()
            fallback_history.append(SystemMessage(content=
                f"Taste Profile:\n{taste_profile}\n\nCurrent Inventory:\n{current_inventory}"
            ))
            default_response = self.default_model.invoke(fallback_history).content
            response_parts.append(default_response)
        
        # Build final response
        final_response = "\n\n".join(response_parts)
        self.chat_history.append(AIMessage(content=final_response))
        
        return {
            "response": final_response,
            "router_output": router_output,
            "response_parts": response_parts
        }

    def reset_conversation(self):
        """Reset the conversation history"""
        self.chat_history = [self.system_message]



if __name__ == "__main__":
    # Create instance of Luna
    luna = LunaAssistant()
    
    print("Luna Personal Assistant (Press Ctrl+C to exit)")
    print("--------------------------------------------")
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                break
                
            if user_input.lower() == 'reset':
                luna.reset_conversation()
                print("Conversation reset.")
                continue
            
            if not user_input:
                continue
                
            result = luna.process_message(user_input)
            print("\nLuna:", result["response"])
            
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")