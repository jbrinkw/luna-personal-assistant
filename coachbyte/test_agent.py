import asyncio
import subprocess
import sys
import time
import json

from agents import Agent
from agents.mcp.server import MCPServerSse, MCPServerSseParams
from agents.run import Runner

import db

SERVER_PORT = 8100
SERVER_URL = f"http://localhost:{SERVER_PORT}/sse"
SERVER_SCRIPT = "coachbyte/coachbyte_mcp_server.py"
MODEL = "gpt-4o"

async def run_agent(prompt: str) -> str:
    server = MCPServerSse(MCPServerSseParams(url=SERVER_URL))
    await server.connect()
    agent = Agent(
        name="CoachByteTest",
        instructions="Use the workout tools to respond to the user.",
        mcp_servers=[server],
        model=MODEL,
    )
    try:
        result = await Runner.run(agent, prompt)
        return result.final_output
    finally:
        await server.cleanup()

def try_reset_db():
    try:
        db.init_db(sample=True)
        return True
    except Exception as e:
        print("CoachByte DB not accessible:", e)
        return False

async def run_tests():
    results = {}
    results["plan"] = await run_agent("show today's plan")
    results["new_plan"] = await run_agent("create simple plan with push ups")
    return results

def main():
    if not try_reset_db():
        print("Skipping CoachByte tests")
        return
    server = subprocess.Popen([sys.executable, SERVER_SCRIPT, "--port", str(SERVER_PORT)])
    try:
        time.sleep(2)
        results = asyncio.run(run_tests())
    finally:
        server.terminate()
        server.wait()
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
