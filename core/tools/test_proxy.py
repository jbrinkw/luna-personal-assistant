import os
import time
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
load_dotenv()

# Target the new OpenAI-compatible server
API_HOST = os.environ.get("API_HOST", "127.0.0.1").strip()
API_PORT = int(os.environ.get("API_PORT", "8010"))
API_URL = f"http://{API_HOST}:{API_PORT}/v1/chat/completions"

# Keep a 'url' variable for backward references (other tooling may read it)
url = API_URL

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
        """Send a message to the server with full conversation history."""
        start_time = time.time()

        payload = {"messages": self._build_messages(message)}

        try:
            resp = requests.post(API_URL, json=payload, timeout=60)
            resp.raise_for_status()
            # Server returns plain text body for the completion
            agent_reply = resp.text.strip()

            duration = time.time() - start_time
            self.chat_history.append(
                {
                    "user": message,
                    "agent": agent_reply,
                    "timestamp": time.time(),
                    "duration": duration,
                }
            )
            return agent_reply, duration
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            return f"Error making request - {e}", duration
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

Chat Log:
{chat_log}


Return your judgment as a JSON object with this exact structure:
{{
    "success": true/false,
    "reason": "Concise but technical and detailed explanation of why it passed or failed. If there is an error echo it",
    "confidence": "high/medium/low"
}}

Be strict in your evaluation - the AI must demonstrate clear memory of the specific information provided.
IF THE TEST IS A FAIL ECHO THE CHAT LOG YOU RECIVED
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

        print(f"=== Prompt Set {set_index}: {prompt_set['name']} ===")
        print(f"Description: {prompt_set['description']}\n")

        for i, prompt in enumerate(prompt_set['prompts'], 1):
            print(f"{i}. You: {prompt}")
            print("   Thinking...")

            reply, duration = chat.send_message(prompt)
            print(f"   Agent: {reply} (took {duration:.2f}s)")
            print()

        # Print history for this set
        print(f"--- History for {prompt_set['name']} ---")
        for i, exchange in enumerate(chat.chat_history, 1):
            print(f"{i}. You: {exchange['user']}")
            print(f"   Agent: {exchange['agent']} (took {exchange['duration']:.2f}s)")
        print("=" * 50 + "\n")

        # Judge the test with LLM
        print("🤖 Judging test with LLM...")
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
        }

        # Print individual judgment
        status = "✅ PASSED" if judgment["success"] else "❌ FAILED"
        print(f"Result: {status}")
        print(f"Reason: {judgment['reason']}")
        print(f"Confidence: {judgment['confidence']}")
        print(f"⏱️  Individual test time: {test_duration:.2f} seconds")
        print("=" * 50 + "\n")

        return result

    def run_tests(self, prompt_sets):
        """Run multiple sets of prompts in parallel"""

        print("🚀 Starting parallel test execution...")
        overall_start_time = time.time()

        test_results = []

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

        overall_end_time = time.time()
        total_duration = overall_end_time - overall_start_time

        # Sort results by original set index to maintain order
        test_results.sort(key=lambda x: x["set_index"])

        # Print summary of all results
        print(f"\n🏁 All tests completed!")
        print(f"⏱️  Total parallel execution time: {total_duration:.2f} seconds")
        self.print_test_summary(test_results, total_duration)

        return test_results

    def print_test_summary(self, test_results, total_parallel_time):
        """Print a structured summary of all test results"""

        print("🏁 TEST SUMMARY")
        print("=" * 60)

        passed_count = 0
        failed_count = 0
        total_test_time = 0

        for result in test_results:
            name = result["name"]
            judgment = result["judgment"]
            success = judgment["success"]
            reason = judgment["reason"]
            confidence = judgment["confidence"]
            duration = result.get("duration", 0)
            total_test_time += duration

            if success:
                passed_count += 1
                status_icon = "✅"
                status_text = "PASSED"
            else:
                failed_count += 1
                status_icon = "❌"
                status_text = "FAILED"

            print(f"{status_icon} {name}: {status_text}")
            print(f"   ⏱️  Test time: {duration:.2f}s")
            print(f"   📝 Reason: {reason}")
            print(f"   🎯 Confidence: {confidence}")
            print()

        total_tests = len(test_results)
        pass_rate = (passed_count / total_tests * 100) if total_tests > 0 else 0

        print("=" * 60)
        print(f"📊 OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_count}")
        print(f"   Failed: {failed_count}")
        print(f"   Pass Rate: {pass_rate:.1f}%")
        print()
        print(f"⏱️  TIMING SUMMARY:")
        print(f"   Total Test Time (sequential): {total_test_time:.2f}s")
        print(f"   Actual Runtime (parallel): {total_parallel_time:.2f}s")
        print("=" * 60)