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
    def __init__(self, taste_profile_table: TasteProfile):
        """Initialize processor with shared TasteProfile table object."""
        self.taste_profile_table = taste_profile_table # Store passed object
        
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
        """Get the current taste profile using the shared table object."""
        # No db connection needed here, use self.taste_profile_table
        try:
            profile = self.taste_profile_table.read()
            return profile if profile else "No taste profile found."
        except Exception as e:
            print(f"[ERROR] Failed to get current taste profile in processor: {e}")
            return "Error retrieving current taste profile."
        # No disconnect needed
    
    def update_taste_profile(self, user_request):
        """Update the taste profile based on the user request using the shared table object."""
        current_profile = self.get_current_profile()
        
        # No need to initialize database connection, use self.taste_profile_table
        taste_profile = self.taste_profile_table
        
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
            # Handle None case for current_profile
            if updated_profile == (current_profile if current_profile != "No taste profile found." else None):
                print("[INFO] Taste profile unchanged.")
                return False, "No changes were detected or applied to your taste profile."
            
            # Update the database using shared table object
            taste_profile.update(updated_profile)
            
            # Create confirmation message
            confirmation = "TASTE PROFILE UPDATE CONFIRMATION\n-------------------------------------\n"
            # confirmation += f"Your taste profile has been updated based on: '{user_request}'\n\n"
            confirmation += "NEW TASTE PROFILE:\n"
            confirmation += updated_profile
            
            return True, confirmation
        except Exception as e:
            print(f"[ERROR] Taste profile processor error: {e}")
            import traceback
            print(traceback.format_exc())
            return False, f"Failed to update taste profile: {e}"
        # No disconnect needed 