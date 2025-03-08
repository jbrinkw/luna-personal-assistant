#!/usr/bin/env python
import config
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from db_functions import run_query, create_table, get_taste_profile, get_saved_meals, clear_table

# Define models for meal extraction
class Meal(BaseModel):
    name: str = Field(..., description="Meal name")
    prep_time: Optional[str] = Field(
        None, description="Preparation time, e.g. '30 minutes'. Generate one if missing based on taste profile."
    )
    ingredients: Optional[List[str]] = Field(
        None, description="List of ingredients. Generate if not provided, using the taste profile."
    )
    recipe: Optional[str] = Field(
        None, description="Recipe instructions. Generate if missing, aligning with taste profile and details."
    )

class MealsData(BaseModel):
    meals: List[Meal] = Field(..., description="List of meals extracted from the input")

# Extractor class for meals CRUD
class MealExtractor:
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.llm_model = "gpt-3.5-turbo"
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, openai_api_key=self.api_key)
        self.output_parser = PydanticOutputParser(pydantic_object=MealsData)
        self.format_instructions = self.output_parser.get_format_instructions()
        self.taste_profile = get_taste_profile()
        self.extraction_prompt_template = """\
Analyze the following user input to extract a list of meals. For each meal, output the following fields:
- name: the meal name.
- prep_time: the preparation time. If missing, generate a realistic prep time that suits the taste profile '{taste_profile}'.
- ingredients: a list of ingredients. If not provided, create one based on the taste profile and any given details.
- recipe: recipe instructions. If absent, generate a recipe that aligns with the taste profile and meal context.
Return the results as a JSON object following this schema:
{format_instructions}

User Input: {user_input}
"""
    def extract_meals(self, user_input: str) -> MealsData:
        prompt = ChatPromptTemplate.from_template(template=self.extraction_prompt_template)
        messages = prompt.format_messages(
            user_input=user_input,
            taste_profile=self.taste_profile,
            format_instructions=self.format_instructions
        )
        response = self.chat.invoke(messages)
        parsed_output = self.output_parser.parse(response.content)
        return MealsData.parse_obj(parsed_output)

def filter_duplicate_recipes(meals_data: MealsData) -> MealsData:
    """
    For each meal in meals_data, use AI to compare its name with existing meal names
    in the database. If a similar name is found (even with slight differences), remove the meal.
    """
    saved_meals = get_saved_meals()
    existing_names = [meal[1] for meal in saved_meals if meal[1]]
    if not existing_names:
        return meals_data

    llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo", openai_api_key=config.OPENAI_API_KEY)
    filtered_meals = []
    for meal in meals_data.meals:
        existing_list = "\n".join([f"- {name}" for name in existing_names])
        prompt = f"""You are a meal name comparison assistant.
Compare the new meal name with the list of existing meal names.
If the new name is very similar to any existing name (even with slight spelling or wording differences),
answer ONLY "REMOVE". If the name is unique, answer ONLY "KEEP".

New Meal Name: {meal.name}

Existing Meal Names:
{existing_list}

Answer:"""
        response = llm.invoke([{"role": "user", "content": prompt}])
        answer = response.content.strip().upper()
        if answer == "KEEP":
            filtered_meals.append(meal)
        else:
            print(f"Skipping meal '{meal.name}' because a similar name already exists in the DB.")
    
    meals_data.meals = filtered_meals
    return meals_data

class MealDBUpdater:
    """
    This class saves meals to one of two tables.
    If new=True, it saves the meals to the 'new_meal_ideas' table
    (clearing existing meal ideas before insertion),
    otherwise it saves them to the 'meals' table with duplicate filtering.
    """
    def __init__(self):
        self.extractor = MealExtractor()
    
    def update_meals_in_db(self, user_input: str, new: bool):
        meals_data = self.extractor.extract_meals(user_input)
        # Only filter duplicates when saving to the 'meals' table.
        if not new:
            meals_data = filter_duplicate_recipes(meals_data)
        
        if not meals_data.meals:
            print("No meals extracted from the input.")
            return
        
        table_name = "new_meal_ideas" if new else "meals"
        create_table(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                prep_time TEXT,
                ingredients TEXT,
                recipe TEXT
            )
        """)
        
        # If updating new meal ideas, clear the table first.
        if new:
            clear_table(table_name)
        
        query_max = f"SELECT MAX(id) FROM {table_name}"
        result = run_query(query_max, (), commit=False)
        current_max = result[0][0] if result and result[0][0] is not None else -1
        
        for idx, meal in enumerate(meals_data.meals):
            meal_id = current_max + 1 + idx
            ingredients_str = ", ".join(meal.ingredients) if meal.ingredients else "N/A"
            query = f"INSERT INTO {table_name} (id, name, prep_time, ingredients, recipe) VALUES (%s, %s, %s, %s, %s)"
            run_query(query, (meal_id, meal.name, meal.prep_time, ingredients_str, meal.recipe), commit=True)
            print(f"{meal_id} - {meal.name} | {meal.prep_time} | {ingredients_str} | {meal.recipe}")
        
        print(f"Meals updated successfully in table '{table_name}'.")

# Example usage for quick testing:
if __name__ == "__main__":
    test_input = (
        """Magic spaghetti (spaghetti, parmesan cheese, butter, olive oil, pepper)
Steak burrito
Breakfast egg sandwich (scrambled eggs, cheese, turkey sausage, mayo-toasted sourdough)
Homemade McChicken (Tyson frozen spicy chicken patties, toasted burger buns, extra mayo)"""
    )
    updater = MealDBUpdater()
    # new=True clears the 'new_meal_ideas' table before inserting.
    updater.update_meals_in_db(test_input, new=True)
