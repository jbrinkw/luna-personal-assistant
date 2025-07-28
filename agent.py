import os
import json
from typing import List

from langchain_openai import ChatOpenAI
from langchain.agents import Tool, create_react_agent, AgentExecutor
from langchain import hub

import tools
from models import PlanItem, LogCompletedInput, RunSQLInput

# Setup LLM
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "test")
llm = ChatOpenAI(model="gpt-4-1106-preview", temperature=0.0)

def create_agent():
    tool_list: List[Tool] = [
        Tool(
            name="get_today_plan",
            func=lambda _: str(tools.get_today_plan()),
            description="Retrieve today's planned sets as a list"
        ),
        Tool(
            name="log_completed_set",
            func=lambda input: str(tools.log_completed_set(**LogCompletedInput.model_validate_json(input).dict())),
            description="Log a completed set. Input JSON with exercise, reps, load"
        ),
        Tool(
            name="new_daily_plan",
            func=lambda input: str(tools.new_daily_plan([p.dict() for p in [PlanItem(**item) for item in json.loads(input)]])),
            description="Create today's plan. Input JSON list of {exercise, order, reps, load}"
        ),
        Tool(
            name="update_summary",
            func=lambda input: tools.update_summary(input),
            description="Update today's summary with provided text"
        ),
        Tool(
            name="get_recent_history",
            func=lambda input: str(tools.get_recent_history(int(input))),
            description="Get history for last N days"
        ),
        Tool(
            name="run_sql",
            func=lambda input: str(tools.run_sql(**RunSQLInput.model_validate_json(input).dict())),
            description="Run arbitrary SELECT query. Provide JSON {query, params?, confirm?}"
        ),
        Tool(
            name="arbitrary_update",
            func=lambda input: str(tools.arbitrary_update(**RunSQLInput.model_validate_json(input).model_dump(exclude={"confirm"}))),
            description="Run arbitrary UPDATE/INSERT/DELETE SQL. Input JSON {query, params}"
        ),
    ]

    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm, tool_list, prompt)
    executor = AgentExecutor(agent=agent, tools=tool_list, verbose=True)
    return executor
