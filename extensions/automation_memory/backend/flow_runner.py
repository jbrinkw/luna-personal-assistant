#!/usr/bin/env python3
"""
Flow Runner - Executes task flows with progress tracking
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env')
except Exception:
    pass

import psycopg
from psycopg.rows import dict_row


def get_db_conninfo():
    """Get database connection string from environment."""
    host = os.getenv('DB_HOST', os.getenv('PGHOST', os.getenv('POSTGRES_HOST', '127.0.0.1')))
    port = os.getenv('DB_PORT', os.getenv('PGPORT', '5432'))
    database = os.getenv('DB_NAME', os.getenv('PGDATABASE', 'luna'))
    user = os.getenv('DB_USER', os.getenv('PGUSER', 'postgres'))
    password = os.getenv('DB_PASSWORD', os.getenv('PGPASSWORD', ''))
    
    return f"host={host} port={port} dbname={database} user={user} password={password}"


async def execute_prompt_with_agent(prompt: str, agent: str, memories: list) -> dict:
    """Execute a single prompt using the specified agent."""
    import aiohttp
    
    agent_api_host = os.getenv('AGENT_API_HOST', os.getenv('SUPERVISOR_HOST', '127.0.0.1'))
    agent_api_url = f"http://{agent_api_host}:{os.getenv('AGENT_API_PORT', '8080')}/v1/chat/completions"
    
    payload = {
        "model": agent,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(agent_api_url, json=payload, timeout=300) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    return {
                        "success": True,
                        "prompt": prompt,
                        "response": response,
                        "error": None
                    }
                else:
                    error_text = await resp.text()
                    return {
                        "success": False,
                        "prompt": prompt,
                        "response": None,
                        "error": f"HTTP {resp.status}: {error_text}"
                    }
    except Exception as e:
        return {
            "success": False,
            "prompt": prompt,
            "response": None,
            "error": str(e)
        }


async def run_flow(flow_id: int, execution_id: int):
    """Execute a task flow and track progress in the database."""
    conninfo = get_db_conninfo()
    
    try:
        conn = await psycopg.AsyncConnection.connect(conninfo, row_factory=dict_row)
        
        # Get flow details
        async with conn.cursor() as cur:
            await cur.execute('SELECT id, call_name, prompts, agent FROM task_flows WHERE id = %s', (flow_id,))
            flow = await cur.fetchone()
            
            if not flow:
                print(f"Flow {flow_id} not found", file=sys.stderr)
                return
            
            # Get memories
            await cur.execute('SELECT content FROM memories ORDER BY id DESC')
            memory_rows = await cur.fetchall()
            memories = [row['content'] for row in memory_rows]
            
            prompts = flow['prompts'] if isinstance(flow['prompts'], list) else json.loads(flow['prompts'])
            agent = flow['agent']
            
            print(f"[flow_runner] Executing flow: {flow['call_name']} with {len(prompts)} prompts using {agent}")
            
            # Execute each prompt
            for idx, prompt in enumerate(prompts):
                print(f"[flow_runner] Prompt {idx + 1}/{len(prompts)}: {prompt[:50]}...")
                
                # Execute prompt
                result = await execute_prompt_with_agent(prompt, agent, memories)
                
                # Update progress in database
                async with conn.cursor() as update_cur:
                    # Get current results
                    await update_cur.execute(
                        'SELECT prompt_results FROM flow_executions WHERE id = %s',
                        (execution_id,)
                    )
                    row = await update_cur.fetchone()
                    current_results = row['prompt_results'] if row else []
                    if isinstance(current_results, str):
                        current_results = json.loads(current_results)
                    
                    current_results.append(result)
                    
                    await update_cur.execute(
                        'UPDATE flow_executions SET current_prompt_index = %s, prompt_results = %s WHERE id = %s',
                        (idx + 1, json.dumps(current_results), execution_id)
                    )
                    await conn.commit()
                
                if not result['success']:
                    print(f"[flow_runner] Error in prompt {idx + 1}: {result['error']}", file=sys.stderr)
                    # Mark execution as failed
                    async with conn.cursor() as fail_cur:
                        await fail_cur.execute(
                            'UPDATE flow_executions SET status = %s, completed_at = CURRENT_TIMESTAMP, error = %s WHERE id = %s',
                            ('failed', result['error'], execution_id)
                        )
                        await conn.commit()
                    await conn.close()
                    return
                
                print(f"[flow_runner] Response: {result['response'][:100]}...")
            
            # Mark execution as completed
            async with conn.cursor() as complete_cur:
                await complete_cur.execute(
                    'UPDATE flow_executions SET status = %s, completed_at = CURRENT_TIMESTAMP WHERE id = %s',
                    ('completed', execution_id)
                )
                await conn.commit()
            
            print(f"[flow_runner] Flow execution completed successfully")
            
        await conn.close()
        
    except Exception as e:
        print(f"[flow_runner] Fatal error: {e}", file=sys.stderr)
        # Try to mark execution as failed
        try:
            conn = await psycopg.AsyncConnection.connect(conninfo)
            async with conn.cursor() as cur:
                await cur.execute(
                    'UPDATE flow_executions SET status = %s, completed_at = CURRENT_TIMESTAMP, error = %s WHERE id = %s',
                    ('failed', str(e), execution_id)
                )
                await conn.commit()
            await conn.close()
        except:
            pass


async def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: flow_runner.py <flow_id> <execution_id>", file=sys.stderr)
        sys.exit(1)
    
    flow_id = int(sys.argv[1])
    execution_id = int(sys.argv[2])
    
    await run_flow(flow_id, execution_id)


if __name__ == '__main__':
    asyncio.run(main())





