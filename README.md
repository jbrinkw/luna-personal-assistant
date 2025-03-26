# Virtual Personal Chef

## Main Features

**Food Inventory Tracking:**  
Keeps a real-time record of what you have in your pantry, including quantities and expiration dates.

**Meal Suggestions & Planning:**  
Uses your taste preferences and current inventory to suggest meals on the fly and even generate multi-day meal plans.

**Automated Shopping Lists:**  
Compares your meal plans against your inventory and automatically creates a shopping list for any missing items.

**Walmart Order Placement:**  
Takes the shopping list a step further by placing orders with Walmart, so you get what you need without manual effort.



## Tech Stack Summary

- **AI & Language Processing:**  
  LLM-driven assistant built with LangChain and open-source LLMs (DeepSeek R1, Llama 3) for asynchronous processing on personal hardware, reducing API costs.

- **Backend:**  
  FastAPI application hosted on AWS EC2 using Docker, with a SQL database on Azure.

- **Frontend:**  
  User interface deployed on Hugging Face Spaces using Streamlit UI.
