# MCP Server Test Suite

This project includes simple agents that exercise each sub-agent's MCP server.
Tests use the OpenAI `agents` SDK with the `gpt-4o` model.  Every test script
starts the appropriate server, issues natural language prompts and prints a JSON
report.

## ChefByte
* `chefbyte/test_agent.py`
  - Resets the SQLite database to the provided sample data.
  - Starts `chefbyte_mcp_server.py` and connects an Agent via SSE.
  - For each major table (inventory, taste profile, saved meals, shopping list
    and daily planner) it:
    1. Captures the current rows.
    2. Prompts the agent to update the table (e.g. "add carrots to inventory").
    3. Captures the rows again and asks the agent to display them.
    4. Stores the before/after data along with the agent responses.
  - A short LLM evaluation summarises whether the updates worked.

## CoachByte
* `coachbyte/test_agent.py`
  - Attempts to initialize the PostgreSQL database with sample data. If the
    connection fails the test is skipped.
  - If successful, starts `coachbyte_mcp_server.py` and runs a couple of simple
    prompts to fetch and create workout plans.

## GeneralByte
* `generalbyte/test_agent.py`
  - Starts `generalbyte_mcp_server.py` and runs prompts for the notification and
    to-do list tools.

## Running All Tests
Execute `python run_all_tests.py` from the project root. Each test script prints
its own JSON output. The aggregator collects return codes and captured output for
review.
