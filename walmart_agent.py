import csv
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
import config

class GroceryItem(BaseModel):
    name: str = Field(..., description="Normalized grocery item name")
    index: Optional[int] = Field(None, description="Index of matching item in link_pointers.csv")

class GroceryItemList(BaseModel):
    items: List[GroceryItem] = Field(..., description="List of grocery items with matches")

def get_walmart_links(grocery_list: str) -> None:
    """
    Take a grocery list string and generate a links.csv file with matching Walmart product links.
    
    Args:
        grocery_list (str): Space-separated list of grocery items
    """
    # Initialize ChatGPT
    chat = ChatOpenAI(
        temperature=0, 
        model="gpt-4o-mini", 
        openai_api_key=config.OPENAI_API_KEY
    )
    output_parser = PydanticOutputParser(pydantic_object=GroceryItemList)
    
    # Load link pointers
    link_pointers = []
    try:
        with open('link_pointers.csv', 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if len(row) >= 3:
                    link_pointers.append({
                        'index': i,
                        'name': row[1],
                        'link': row[2]
                    })
    except FileNotFoundError:
        print("Error: link_pointers.csv not found")
        return

    # Create and format prompt
    prompt_template = """\
Given a grocery list and a database of items available for purchase, match each grocery item to the best corresponding item in the database.
For items that have no good match, leave the index as null.

Grocery list: {grocery_list}

Available items:
{available_items}

{format_instructions}

Return the results as structured data following the above schema.
"""
    
    prompt = ChatPromptTemplate.from_template(template=prompt_template)
    available_items = "\n".join([f"{i}: {item['name']}" for i, item in enumerate(link_pointers)])
    
    # Clean up input and get matches
    cleaned_list = re.sub(r'\s+', ' ', grocery_list).strip()
    messages = prompt.format_messages(
        grocery_list=cleaned_list,
        available_items=available_items,
        format_instructions=output_parser.get_format_instructions()
    )
    
    response = chat.invoke(messages)
    matched_items = GroceryItemList.parse_obj(output_parser.parse(response.content))
    
    # Generate links.csv
    links = []
    for item in matched_items.items:
        if item.index is not None:
            try:
                index = int(item.index)
                if 0 <= index < len(link_pointers):
                    links.append(link_pointers[index]['link'])
            except (ValueError, IndexError, KeyError):
                continue
    
    # Write to links.csv
    with open('links.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        for link in links:
            writer.writerow([link])
    
    print(f"Generated links.csv with {len(links)} links.")

if __name__ == "__main__":
    # Example usage
    sample_list = "milk eggs bread cheese"
    get_walmart_links(sample_list)