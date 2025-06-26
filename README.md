# Virtual Personal Chef

The long-term goal of this project is to build a multifaceted personal assistant that can track and assist with any part of your life through natural language interactions. It will consist of a series of specialized AI agents, each handling its own domain.

Currently, the only working agent is ChefByte, which helps with a range of food-related tasks such as inventory tracking, meal planning, automated grocery ordering, and more.

The next planned agent is a virtual personal trainer that will track workout progress and collaborate with ChefByte to generate meals aligned with daily activity.

---

## Notes

**3/30/25:**  
Just finished a major refactor of the entire project. There are too many features and nuances to describe everything in a single agent system prompt. To keep the system consistently on target with arbitrary natural language input, I built a series of routers. The three main routers handle pushing data to the database, pulling data from the database, and calling tools. The push and pull routers are fairly straightforward, but tool-related logic often requires additional layers of routing to curate a smoother user experience.

Performance improved significantly after switching from raw data to internal item IDs during LLM processing. For example, when the user asks for a meal suggestion, the AI only returns a few numeric IDs, which I then resolve into full meal data through a separate function.

This update includes rough drafts of all major system components, except for the shopping list and automated ordering features. I’ll reimplement those after I create a dictionary of ingredients and products available at Walmart to ensure reliable and consistent ordering.

---

## Main Features

**Food inventory tracking** keeps a real-time record of pantry contents, including quantities and expiration dates.

**Meal suggestions and planning** use current inventory and user preferences to generate single or multi-day meal plans.

**Automated shopping list generation** compares your inventory against selected meals and compiles a list of missing items.

**Walmart order placement** automates the process of purchasing missing items directly from Walmart based on the shopping list.

---

## Tech Stack Summary

The assistant is powered by open-source LLMs like DeepSeek R1 and LLaMA 3, orchestrated with LangChain and run asynchronously on local hardware to minimize API usage and costs.

The backend is built with FastAPI, containerized with Docker, and hosted on AWS EC2. The SQL database runs on Azure.

The frontend is a Streamlit-based interface deployed on Hugging Face Spaces.

## MCP Servers

The push, pull and tool routers are now exposed as independent MCP servers
using a lightweight `fastmcp` wrapper around FastAPI.

Run each server in a separate terminal:

```bash
uvicorn servers.pull_server:app --port 8001
uvicorn servers.push_server:app --port 8002
uvicorn servers.tool_server:app --port 8003
```

Each tool from the corresponding router is available as a POST endpoint at
`/<tool_name>` returning JSON `{ "result": "..." }`.

## Testing

The project ships with a small SQLite database located at `data/chefbyte.db`.
Unit tests rely on this file, so no additional database setup is required.

Install the Python dependencies and run the tests with:

```bash
pip install -r requirements.txt
pytest -q
```

