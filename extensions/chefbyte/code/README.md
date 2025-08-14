# Virtual Personal Chef

The long‑term goal of this project is to build a multifaceted personal assistant that can track and assist with many aspects of daily life via natural language.  The first major component is **ChefByte**, a food‑focused assistant that manages inventory, meal planning and shopping.

ChefByte exposes a collection of *tools* which can be called by LLM agents or other programs.  These tools wrap the underlying database layer and various helper engines.  They are grouped into **push**, **pull** and **action** categories:

* **Push tools** – update data tables such as the pantry inventory or meal planner.
* **Pull tools** – retrieve formatted context from the database.
* **Action tools** – orchestrate higher‑level flows like generating new recipes or planning meals.

Upcoming work includes additional agents (for example a fitness planner) that will integrate with ChefByte so meals can align with workout goals.

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

## Using the Tools

ChefByte's capabilities are exposed as a series of FastMCP tools.  Each tool can be invoked over HTTP, SSE or stdio when the corresponding server is running.  Tools fall into three categories:

* **Push** – modify data such as inventory or saved meals.
* **Pull** – retrieve context like the current shopping list.
* **Action** – run multi‑step workflows such as planning meals.

Refer to [docs/tools.md](docs/tools.md) for a complete reference of available tools and example invocations.

See [docs/database.md](docs/database.md) for the database schema used by these tools.

---

## Tech Stack Summary

The assistant is powered by open-source LLMs like DeepSeek R1 and LLaMA 3, orchestrated with LangChain and run asynchronously on local hardware to minimize API usage and costs.

The backend is built with FastAPI, containerized with Docker, and hosted on AWS EC2. The SQL database runs on Azure.

The UI is provided by a FastAPI + Jinja2 web app in `chefbyte_webapp/`.
