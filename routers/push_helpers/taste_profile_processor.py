"""
This module handles taste profile updates from natural language inputs.
"""

import os
from typing import Tuple
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from db.db_functions import Database, TasteProfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TasteProfileUpdate(BaseModel):
    """Model for taste profile update output"""
    updated_profile: str = Field(..., description="The updated taste profile text")

class TasteProfileProcessor:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.llm_model = "gpt-4o-mini"  # Using a simpler model for efficiency
        self.chat = ChatOpenAI(temperature=0, model=self.llm_model, api_key=self.api_key)
        self.output_parser = PydanticOutputParser(pydantic_object=TasteProfileUpdate)
        
        # Create prompt template for updating taste profile
        self.format_instructions = self.output_parser.get_format_instructions()
        self.update_prompt_template = """
You are an assistant helping manage a user's taste profile for cooking. 
The taste profile contains information about the user's food preferences, dietary restrictions, allergies, and cooking habits.

Current taste profile:
{current_profile}

User request:
{user_request}

Your task is to update the taste profile based on the user's request. Follow these rules:
1. If the user asks to add or modify preferences, update the taste profile accordingly
2. If the user asks to remove something, remove it from the profile
3. Maintain the structure, format, and style of the existing profile
4. If the user request doesn't specify clear changes, keep the profile as is
5. Make sure the updated profile is complete and coherent

Return the updated taste profile as a JSON object with the field "updated_profile" containing the full updated profile.

{format_instructions}
"""

    def get_current_profile(self):
        """Get the current taste profile from the database"""
        db = Database()
        taste_profile = TasteProfile(db)
        try:
            result = taste_profile.read()
            if result and result[0] and result[0][0]:
                return result[0][0]
            return "No taste profile found."
        finally:
            db.disconnect()
    
    def update_taste_profile(self, user_request):
        """Update the taste profile based on the user request"""
        current_profile = self.get_current_profile()
        
        # Initialize database connection
        db = Database()
        taste_profile = TasteProfile(db)
        
        try:
            # Create the prompt
            prompt = ChatPromptTemplate.from_template(template=self.update_prompt_template)
            messages = prompt.format_messages(
                current_profile=current_profile,
                user_request=user_request,
                format_instructions=self.format_instructions
            )
            
            # Get response from LLM
            response = self.chat.invoke(messages)
            print(f"[DEBUG] Taste Profile LLM raw output (truncated): '{response.content[:300]}...'")
            
            # Parse the response
            parsed_response = self.output_parser.parse(response.content)
            updated_profile = parsed_response.updated_profile
            
            # Compare profiles to see if any changes were made
            if updated_profile == current_profile:
                return False, "No changes were made to your taste profile."
            
            # Update the database
            taste_profile.update(updated_profile)
            
            # Create confirmation message
            confirmation = "TASTE PROFILE UPDATED:\n"
            confirmation += f"Your taste profile has been updated based on: '{user_request}'\n\n"
            confirmation += "CURRENT TASTE PROFILE:\n"
            confirmation += updated_profile
            
            return True, confirmation
        except Exception as e:
            print(f"[ERROR] Taste profile processor error: {e}")
            return False, f"Failed to update taste profile: {e}"
        finally:
            # Disconnect from database
            db.disconnect() 