#!/usr/bin/env python
import config
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from db_functions import run_query, create_table

# Define models for taste preferences extraction.
class TastePreference(BaseModel):
    item: str = Field(..., description="The food item for which the preference is stated")
    preference: str = Field(..., description="User's sentiment or preference about the food item")

class PreferencesData(BaseModel):
    preferences: List[TastePreference] = Field(..., description="List of extracted taste preferences")

class TastePreferencesExtractor:
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.llm_model = "gpt-3.5-turbo"
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, openai_api_key=self.api_key)
        self.output_parser = PydanticOutputParser(pydantic_object=PreferencesData)
        self.format_instructions = self.output_parser.get_format_instructions()
        self.extraction_prompt_template = """\
Analyze the following user input and extract any taste preferences the user communicates about food.
If possible, format each preference as "item: preference" (but only if it fits naturally).
Return the results as a JSON object following this schema:
{format_instructions}

User Input: {user_input}
"""
    def extract_preferences(self, user_input: str) -> PreferencesData:
        prompt = ChatPromptTemplate.from_template(template=self.extraction_prompt_template)
        messages = prompt.format_messages(
            user_input=user_input,
            format_instructions=self.format_instructions
        )
        response = self.chat.invoke(messages)
        parsed_output = self.output_parser.parse(response.content)
        return PreferencesData.parse_obj(parsed_output)

def update_taste_preferences_in_db(user_input: str):
    extractor = TastePreferencesExtractor()
    preferences_data = extractor.extract_preferences(user_input)
    
    if not preferences_data.preferences:
        print("No taste preferences extracted from the input.")
        return

    # Ensure the taste_profile table exists.
    create_table("""
        CREATE TABLE IF NOT EXISTS taste_profile (
            id SERIAL PRIMARY KEY,
            profile TEXT
        )
    """)
    
    for pref in preferences_data.preferences:
        pref_str = f"{pref.item}: {pref.preference}"
        query = "INSERT INTO taste_profile (profile) VALUES (%s)"
        run_query(query, (pref_str,), commit=True)
    
    print("Successfully updated taste preferences:")
    for pref in preferences_data.preferences:
        print(f"- {pref.item}: {pref.preference}")

if __name__ == "__main__":
    user_message = "I love spicy food, but I really don't like mushrooms and I prefer my coffee black."
    update_taste_preferences_in_db(user_message)
