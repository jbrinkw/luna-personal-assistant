import app.config as config

from langchain_openai import ChatOpenAI  # Updated import per deprecation warning
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser

class Router:
    def __init__(self):
        # Load the API key from config.py
        self.api_key = config.OPENAI_API_KEY

        self.llm_model = "gpt-4o-mini"
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, openai_api_key=self.api_key)

        # Define response schemas for routing decisions
        self.taste_preferences_schema = ResponseSchema(
            name="taste_preferences",
            description="Trigger if the user mentions food preferences (likes or dislikes). Return True if so, otherwise False."
        )
        self.inventory_schema = ResponseSchema(
            name="inventory",
            description="Trigger if the user wants to add, remove, update, or view inventory items. Return True if so, otherwise False."
        )
        self.meal_suggestion_schema = ResponseSchema(
            name="meal_suggestion",
            description="Trigger if the user asks for immediate/one-off meal recommendations (e.g., 'what should I eat now?', 'suggest dinner for tonight'). Do NOT trigger for multi-day meal planning or recipe requests. Return True if so, otherwise False."
        )
        self.meal_planning_schema = ResponseSchema(
            name="meal_planning",
            description="Trigger if the user wants to plan meals across multiple time periods (e.g., 'plan my meals for the week', 'make a meal plan for next 3 days'). Return True if so, otherwise False."
        )
        self.order_ingredients_schema = ResponseSchema(
            name="order_ingredients",
            description="Trigger if the user wants to order missing ingredients or create a shopping list from Walmart (e.g., 'order ingredients for my meal plan', 'get missing items from Walmart'). Return True if so, otherwise False."
        )

        self.response_schemas = [
            self.taste_preferences_schema,
            self.inventory_schema,
            self.meal_suggestion_schema,
            self.meal_planning_schema,
            self.order_ingredients_schema
        ]
        self.output_parser = StructuredOutputParser.from_response_schemas(self.response_schemas)
        self.format_instructions = self.output_parser.get_format_instructions()

        # Define Routing LLM Prompt Template
        self.routing_prompt_template = """\
Analyze the following user input and determine which focus areas should be triggered.

- taste_preferences: True if the user mentions food preferences (likes or dislikes).
- inventory: True if the user wants to add, remove, or update inventory items.
- meal_suggestion: True if the user asks for immediate/one-off meal recommendations, but NOT for multi-day planning or recipes.
- meal_planning: True if the user wants to plan meals across multiple time periods.
- order_ingredients: True if the user wants to order missing ingredients or create a shopping list from Walmart.

Return the results in the following JSON format:

{format_instructions}

User Input: {user_input}
"""

    def route_request(self, user_input):
        prompt = ChatPromptTemplate.from_template(template=self.routing_prompt_template)
        messages = prompt.format_messages(
            user_input=user_input,
            format_instructions=self.format_instructions
        )

        response = self.chat.invoke(messages)

        # Parse the response into a dictionary
        output_dict = self.output_parser.parse(response.content)
        
        # Convert string values to booleans
        for key in output_dict:
            output_dict[key] = str(output_dict[key]).strip().lower() == "true"
        
        return output_dict
