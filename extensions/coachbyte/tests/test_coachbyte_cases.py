import os
import sys
import json
import subprocess
import pytest

# Ensure repo root on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from core.tools.test_proxy import TestRunner


def _reset_db_with_guard():
    """Invoke guarded DB reset script; safe to call concurrently and repeatedly."""
    try:
        subprocess.run(
            [sys.executable, "extensions/coachbyte/code/python/load_sample_data.py"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Warning: DB reset reported error: {e}. Proceeding with existing data...")


def _get_prompt_sets():
    from extensions.coachbyte.tests.coachbyte_tests import get_prompt_sets
    return get_prompt_sets()


@pytest.fixture(scope="session", autouse=True)
def reset_db_once_per_session():
    # One-time guarded reset per pytest session (guard prevents duplicates across processes)
    _reset_db_with_guard()


@pytest.mark.parametrize("prompt_set", _get_prompt_sets(), ids=lambda s: s.get("name"))
@pytest.mark.timeout(120)
@pytest.mark.order("any")
@pytest.mark.flaky(reruns=0)
@pytest.mark.coachbyte
@pytest.mark.usefixtures("reset_db_once_per_session")
def test_coachbyte_prompt_set(prompt_set):
    runner = TestRunner()
    result = runner.run_single_test_set(prompt_set, set_index=1)

    # Print per-step logs so they appear in pytest output
    chat_history = result.get("chat_history", [])
    print("\n=== Chat History (", prompt_set.get("name"), ") ===", sep="")
    for idx, ex in enumerate(chat_history, 1):
        print(f"{idx}. User: {ex.get('user')}")
        schema_errs = ex.get("schema_errors") or []
        for se in schema_errs:
            print(f"   ! schema error [{se.get('domain')}]: {se.get('error')}")
        tcs = ex.get("tool_calls") or []
        for tc in tcs:
            domain = tc.get("domain")
            name_tc = tc.get("name")
            args = tc.get("args")
            result_tc = tc.get("result") if "result" in tc else tc.get("error")
            print(f"   - tool: {name_tc} [{domain}]")
            print(f"     args: {json.dumps(args, ensure_ascii=False)}")
            try:
                result_str = json.dumps(result_tc, ensure_ascii=False)
            except Exception:
                result_str = str(result_tc)
            print(f"     result: {result_str}")
        print(f"   Agent: {ex.get('agent')} (took {ex.get('duration', 0.0):.2f}s)")
    print("=== End Chat History ===\n")

    judgment = result.get("judgment", {})
    assert judgment.get("success") is True, (
        f"LLM judgment failed for {prompt_set.get('name')}: {judgment}"
    )

