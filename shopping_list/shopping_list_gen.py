from db_functions import get_daily_notes_range
from meal_planning.meal_plan_in_stock_checker import MealPlanInStockChecker
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
import config

class ShoppingItem(BaseModel):
    name: str = Field(..., description="Shopping item name")
    quantity: str = Field(..., description="Shopping quantity in retail units")

class ShoppingListData(BaseModel):
    items: List[ShoppingItem] = Field(..., description="List of shopping items with retail quantities")

class ShoppingListGenerator:
    def __init__(self):
        self.checker = MealPlanInStockChecker()
        self.chat = ChatOpenAI(
            temperature=0, 
            model="gpt-4o-mini", 
            openai_api_key=config.OPENAI_API_KEY
        )
        self.output_parser = PydanticOutputParser(pydantic_object=ShoppingListData)
        
    def _optimize_shopping_list(self, ingredients: list) -> ShoppingListData:
        template = """Convert this list of recipe ingredients into practical shopping quantities.
        Combine similar items and convert to retail units. For example:
        - 4 eggs → 1 dozen eggs
        - 2 slices bacon → 1 package bacon
        - 3 tbsp olive oil → 1 bottle olive oil
        - 2 cups rice → 1 bag rice
        Return the optimized shopping list as JSON with name and quantity fields.
        
        Ingredient List:
        {ingredients}
        
        {format_instructions}
        """
        
        prompt = ChatPromptTemplate.from_template(template=template)
        messages = prompt.format_messages(
            ingredients="\n".join([f"- {item}" for item in ingredients]),
            format_instructions=self.output_parser.get_format_instructions()
        )
        response = self.chat.invoke(messages)
        return self.output_parser.parse(response.content)
        
    def generate_list(self, days_to_plan: int) -> tuple[list, list, bool]:
        """
        Generate a shopping list for X days into the future.
        
        Args:
            days_to_plan (int): Number of days to plan ahead
            
        Returns:
            tuple[list, list, bool]: Raw ingredients list, optimized shopping list, and success status
        """
        start = datetime.now()
        end = start + timedelta(days=days_to_plan)
        
        all_missing_ingredients = set()
        current = start
        
        while current <= end:
            current_date = current.strftime('%Y-%m-%d')
            notes_for_day = get_daily_notes_range(current_date, current_date)
            
            if notes_for_day and notes_for_day[0]:
                date_str, day_of_week, note_content = notes_for_day[0]
                missing = self.checker.get_missing_ingredients(note_content)
                all_missing_ingredients.update(missing)
            
            current += timedelta(days=1)
        
        raw_list = sorted(all_missing_ingredients)
        optimized_list = self._optimize_shopping_list(raw_list)
        
            
        return raw_list, optimized_list.items, True


if __name__ == "__main__":
    # Create an instance of the shopping list generator
    generator = ShoppingListGenerator()
    
    # Generate shopping list for the next 7 days
    raw_list, optimized_list, success = generator.generate_list(3)
    
    print("\nRaw Ingredients List:")
    for item in raw_list:
        print(f"- {item}")
    
    print("\nOptimized Shopping List:")
    for item in optimized_list:
        print(f"- {item.name}: {item.quantity}")
    
    # Convert optimized list to space-separated string for Walmart agent
    shopping_items = " ".join([item.name for item in optimized_list])
    
    # Generate Walmart links
    from shopping_list.walmart_agent import get_walmart_links
    get_walmart_links(shopping_items)