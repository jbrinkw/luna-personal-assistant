import os
import time
import json
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
load_dotenv()

from core.agent.orchestrator_local import orchestrate

# Initialize OpenAI client (set your API key as environment variable OPENAI_API_KEY)
openai_client = OpenAI()


class ChatSession:
    """Maintains chat history for multi-step conversations"""

    def __init__(self):
        self.chat_history = []  # [{user, agent, timestamp, duration}]

    def _build_messages(self, new_user_message: str) -> list[dict]:
        messages: list[dict] = []
        for exchange in self.chat_history:
            messages.append({"role": "user", "content": exchange["user"]})
            messages.append({"role": "assistant", "content": exchange["agent"]})
        messages.append({"role": "user", "content": new_user_message})
        return messages

    def send_message(self, message):
        """Send a message using the new local orchestrator (no HTTP)."""
        start_time = time.time()

        try:
            result = asyncio.run(orchestrate(message))
            agent_reply = (result.get("synth", {}) or {}).get("output", "") or ""
            # Aggregate tool calls from domains, annotated with domain name
            tool_calls = []
            for d in (result.get("domains") or []):
                domain_name = d.get("name")
                for tc in (d.get("tool_calls") or []):
                    tool_calls.append({"domain": domain_name, **tc})

            duration = time.time() - start_time
            schema_errors = result.get("schema_errors") or []
            self.chat_history.append(
                {
                    "user": message,
                    "agent": agent_reply,
                    "timestamp": time.time(),
                    "duration": duration,
                    "tool_calls": tool_calls,
                    "schema_errors": schema_errors,
                }
            )
            return agent_reply, duration
        except Exception as e:
            duration = time.time() - start_time
            return f"Unexpected error - {e}", duration

    def print_history(self):
        print("\n=== Chat History ===")
        for i, exchange in enumerate(self.chat_history, 1):
            print(f"\n{i}. You: {exchange['user']}")
            print(f"   Agent: {exchange['agent']} (took {exchange['duration']:.2f}s)")
        print("==================\n")


class TestRunner:
    """Runs AI memory tests in parallel with LLM judgment"""

    def __init__(self):
        self.openai_client = OpenAI()

    def judge_test_with_llm(self, test_name, test_description, chat_history):
        """Use OpenAI to judge if the test passed or failed"""

        # Format chat history for the prompt
        chat_log = ""
        for i, exchange in enumerate(chat_history, 1):
            chat_log += f"{i}. User: {exchange['user']}\n"
            chat_log += f"   AI: {exchange['agent']}\n"

        prompt = f"""
You are evaluating an AI memory test. Based on the test description and chat log, determine if the AI successfully remembered and recalled the information.

Test Name: {test_name}
Test Description: {test_description}

Chat Log (verbatim; content is exactly between the markers):
<CHAT_LOG_START>
{chat_log}
<CHAT_LOG_END>


Return your judgment as a JSON object with this exact structure:
{{
    "success": true/false,
    "reason": "Concise but technical and detailed explanation of why it passed or failed. If there is an error echo it",
    "confidence": "high/medium/low"
}}

Be strict in your evaluation - the AI must demonstrate clear memory of the specific information provided.
If the test is a FAIL, include the exact Chat Log content between <CHAT_LOG_START> and <CHAT_LOG_END> in the reason (verbatim). If there is no content between the markers, explicitly state that the chat log was empty.
"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an AI test evaluator. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )

            judgment_text = response.choices[0].message.content.strip()
            judgment = json.loads(judgment_text)
            return judgment

        except Exception as e:
            return {
                "success": False,
                "reason": f"Error in judgment: {str(e)}",
                "confidence": "low",
            }

    def run_single_test_set(self, prompt_set, set_index):
        """Run a single test set and return results"""
        test_start_time = time.time()
        chat = ChatSession()  # New session for each set

        for i, prompt in enumerate(prompt_set['prompts'], 1):
            reply, duration = chat.send_message(prompt)

        # Judge the test with LLM
        judgment = self.judge_test_with_llm(
            prompt_set["name"], prompt_set["description"], chat.chat_history
        )

        test_end_time = time.time()
        test_duration = test_end_time - test_start_time

        result = {
            "name": prompt_set["name"],
            "judgment": judgment,
            "set_index": set_index,
            "duration": test_duration,
            "chat_history": chat.chat_history,
        }

        return result

    def run_tests(self, prompt_sets):
        """Run multiple sets of prompts in parallel"""

        overall_start_time = time.time()

        test_results = []
        total = len(prompt_sets)
        completed = 0

        # Run tests in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(prompt_sets)) as executor:
            # Submit all test sets
            future_to_test = {
                executor.submit(self.run_single_test_set, prompt_set, i): i
                for i, prompt_set in enumerate(prompt_sets, 1)
            }

            # Collect results as they complete
            for future in as_completed(future_to_test):
                result = future.result()
                test_results.append(result)
                completed += 1
                print(f"[{completed}/{total}] {result['name']}")

        overall_end_time = time.time()
        total_duration = overall_end_time - overall_start_time

        # Sort results by original set index to maintain order
        test_results.sort(key=lambda x: x["set_index"])

        # Final consolidated summary
        self.print_test_summary(test_results, total_duration)

        return test_results

    def print_test_summary(self, test_results, total_parallel_time):
        """Print a structured summary of all test results"""

        passed = [r for r in test_results if r.get("judgment", {}).get("success")]
        failed = [r for r in test_results if not r.get("judgment", {}).get("success")]

        total_tests = len(test_results)
        passed_count = len(passed)
        failed_count = len(failed)
        total_test_time = sum(r.get("duration", 0.0) for r in test_results)
        pass_rate = (passed_count / total_tests * 100) if total_tests else 0.0

        print("\n🏁 TEST RESULTS")
        print("=" * 60)
        print(f"Total: {total_tests}   Passed: {passed_count}   Failed: {failed_count}   Pass Rate: {pass_rate:.1f}%")
        print(f"Parallel runtime: {total_parallel_time:.2f}s   Sum of test times: {total_test_time:.2f}s")
        print("=" * 60)

        def _print_test_block(section_title, items):
            if not items:
                return
            print(section_title)
            for r in items:
                name = r["name"]
                j = r["judgment"]
                duration = r.get("duration", 0.0)
                icon = "✅" if j.get("success") else "❌"
                print(f"{icon} {name}")
                print(f"   ⏱️  {duration:.2f}s   🎯 {j.get('confidence')}   📝 {j.get('reason')}")
                # Chat log with tool calls
                for idx, ex in enumerate(r.get("chat_history", []), 1):
                    print(f"   {idx}. User: {ex.get('user')}")
                    schema_errs = ex.get("schema_errors") or []
                    for se in schema_errs:
                        print(f"      ! schema error [{se.get('domain')}]: {se.get('error')}")
                    tcs = ex.get("tool_calls") or []
                    for tc in tcs:
                        domain = tc.get("domain")
                        name_tc = tc.get("name")
                        args = tc.get("args")
                        result = tc.get("result") if "result" in tc else tc.get("error")
                        print(f"      - tool: {name_tc} [{domain}]")
                        print(f"        args: {json.dumps(args, ensure_ascii=False)}")
                        # stringify result safely
                        try:
                            result_str = json.dumps(result, ensure_ascii=False)
                        except Exception:
                            result_str = str(result)
                        print(f"        result: {result_str}")
                    print(f"     Agent: {ex.get('agent')} (took {ex.get('duration', 0.0):.2f}s)")
                print()

        _print_test_block("PASSED TESTS", passed)
        _print_test_block("FAILED TESTS", failed)

        # Final one-line summary
        print(f"{passed_count}/{total_tests} tests passed")