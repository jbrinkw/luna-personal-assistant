import asyncio
import subprocess
import sys
import time
import json

from agents import Agent
from agents.mcp.server import MCPServerSse, MCPServerSseParams
from agents.run import Runner

SERVER_PORT = 8050
SERVER_URL = f"http://localhost:{SERVER_PORT}/sse"
SERVER_SCRIPT = "generalbyte/generalbyte_mcp_server.py"
MODEL = "gpt-4o"

async def run_agent(prompt: str) -> str:
    server = MCPServerSse(MCPServerSseParams(url=SERVER_URL))
    await server.connect()
    agent = Agent(name="GeneralByteTest", instructions="Use the general tools.", mcp_servers=[server], model=MODEL)
    try:
        result = await Runner.run(agent, prompt)
        return result.final_output
    finally:
        await server.cleanup()

async def run_tests():
    results = {}
    results["notify"] = await run_agent("send a notification")
    results["todo_list"] = await run_agent("show my todo list")
    results["modify_todo"] = await run_agent("create todo item buy milk")
    return results

def main():
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
