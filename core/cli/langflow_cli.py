import argparse
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, Optional

import requests
import re


def load_tweaks_from_file(tweaks_path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not tweaks_path:
        return None
    try:
        with open(tweaks_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"[warn] Tweaks file not found: {tweaks_path}")
    except json.JSONDecodeError as exc:
        print(f"[warn] Failed to parse tweaks JSON: {exc}")
    return None


def build_headers(api_key: Optional[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        # Some Langflow versions also accept X-Langflow-Api-Key
        headers["X-Langflow-Api-Key"] = api_key
    return headers


def build_payload(
    input_text: str,
    input_type: str,
    output_type: str,
    session_id: str,
    tweaks: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "input_value": input_text,
        "input_type": input_type,
        "output_type": output_type,
        "session_id": session_id,
    }
    if tweaks is not None:
        payload["tweaks"] = tweaks
    return payload


def post_run(
    base_url: str,
    flow_id: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    timeout_seconds: float,
) -> requests.Response:
    # Langflow run endpoint (non-streaming)
    # Example: http://localhost:7860/api/v1/run/<flow_id>?stream=false
    url = f"{base_url.rstrip('/')}/api/v1/run/{flow_id}?stream=false"
    return requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)


def try_extract_text(response_json: Any) -> Optional[str]:
    # Heuristics to extract a human-friendly text from Langflow response
    if response_json is None:
        return None

    # Common direct fields
    for key in ("text", "message", "output_text", "content", "result"):
        val = response_json.get(key) if isinstance(response_json, dict) else None
        if isinstance(val, str) and val.strip():
            return val

    # Common nested structure: outputs -> [ { outputs: [ { results: { text/message/... } } ] } ]
    try:
        outputs = response_json.get("outputs")
        if isinstance(outputs, list) and outputs:
            first = outputs[0]
            inner_outputs = first.get("outputs") if isinstance(first, dict) else None
            if isinstance(inner_outputs, list) and inner_outputs:
                first_inner = inner_outputs[0]
                results = first_inner.get("results") if isinstance(first_inner, dict) else None
                if isinstance(results, dict):
                    for key in ("text", "message", "output_text", "content"):
                        val = results.get(key)
                        if isinstance(val, str) and val.strip():
                            return val
                artifacts = first_inner.get("artifacts") if isinstance(first_inner, dict) else None
                if isinstance(artifacts, dict):
                    for key, val in artifacts.items():
                        if isinstance(val, str) and val.strip():
                            return val
    except Exception:
        pass

    # Fallback: try stringify
    try:
        return json.dumps(response_json, ensure_ascii=False)
    except Exception:
        return str(response_json)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Interactive CLI for Langflow /api/v1/run. "
            "Reads user input, sends to a flow, and prints response and latency."
        )
    )
    parser.add_argument(
        "--url",
        default=os.getenv("LANGFLOW_URL", "http://192.168.0.226:7860"),
        help="Base URL of the Langflow server (env: LANGFLOW_URL)",
    )
    parser.add_argument(
        "--flow-id",
        default=os.getenv("LANGFLOW_FLOW_ID", "e5d633c6-75a1-46c1-bcf0-3629c912e4f4"),
        help="Flow ID to run (env: LANGFLOW_FLOW_ID). If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("LANGFLOW_API_KEY"),
        help="API key for Langflow, if required (env: LANGFLOW_API_KEY)",
    )
    parser.add_argument(
        "--input-type",
        default=os.getenv("LANGFLOW_INPUT_TYPE", "chat"),
        choices=["text", "chat", "any"],
        help="Input type for Langflow run (env: LANGFLOW_INPUT_TYPE)",
    )
    parser.add_argument(
        "--output-type",
        default=os.getenv("LANGFLOW_OUTPUT_TYPE", "chat"),
        choices=["text", "chat"],
        help="Output type for Langflow run (env: LANGFLOW_OUTPUT_TYPE)",
    )
    parser.add_argument(
        "--session-id",
        default=os.getenv("LANGFLOW_SESSION_ID"),
        help="Optional fixed session ID to retain memory (env: LANGFLOW_SESSION_ID). If omitted, a random one is generated.",
    )
    parser.add_argument(
        "--tweaks-file",
        default=os.getenv("LANGFLOW_TWEAKS_FILE"),
        help="Path to JSON file with 'tweaks' object (env: LANGFLOW_TWEAKS_FILE)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("LANGFLOW_TIMEOUT", "120")),
        help="Request timeout in seconds (env: LANGFLOW_TIMEOUT)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full JSON responses as well as extracted text.",
    )
    return parser.parse_args()


def extract_langflow_from_test_proxy() -> tuple[Optional[str], Optional[str]]:
    """Attempt to read base_url and flow_id from test_proxy.py's url variable.

    Returns (base_url, flow_id) or (None, None) if not found.
    """
    proxy_path = os.path.join(os.path.dirname(__file__), "test_proxy.py")
    try:
        with open(proxy_path, "r", encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError:
        return None, None

    # Find a line like: url = "http://host:7860/api/v1/run/<flow_id>"
    match = re.search(r"url\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not match:
        return None, None

    full_url = match.group(1)
    # Split at /api/v1/run/
    split_marker = "/api/v1/run/"
    if split_marker not in full_url:
        return None, None

    base, after = full_url.split(split_marker, 1)
    flow_id = after.split("?")[0].split("/")[0]
    base_url = base.rstrip("/")
    return base_url, flow_id


def main() -> int:
    args = parse_args()

    base_url: str = args.url
    flow_id: Optional[str] = args.flow_id
    api_key: Optional[str] = args.api_key
    input_type: str = args.input_type
    output_type: str = args.output_type
    session_id: str = args.session_id or str(uuid.uuid4())
    timeout_seconds: float = args.timeout
    verbose: bool = getattr(args, "verbose", False)

    # If flow_id not provided, try to grab it (and base URL) from test_proxy.py
    if not flow_id or base_url == "http://localhost:7860":
        proxy_base_url, proxy_flow_id = extract_langflow_from_test_proxy()
        if not flow_id and proxy_flow_id:
            flow_id = proxy_flow_id
        # Override base_url only if the current value is the default and we found one
        if base_url == "http://localhost:7860" and proxy_base_url:
            base_url = proxy_base_url

    if not flow_id:
        # Still missing; prompt the user
        flow_id = input("Enter Langflow flow ID: ").strip()
        if not flow_id:
            print("[error] Flow ID is required.")
            return 2

    tweaks = load_tweaks_from_file(args.tweaks_file)
    headers = build_headers(api_key)

    print(
        "Connected to Langflow:",
        f"base_url={base_url}",
        f"flow_id={flow_id}",
        f"session_id={session_id}",
        f"input_type={input_type}",
        f"output_type={output_type}",
    )
    print("Type 'exit' or 'quit' to leave. Press Enter on an empty line to skip.")

    while True:
        try:
            user_text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()  # newline after Ctrl+C / Ctrl+Z
            break

        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            break

        payload = build_payload(
            input_text=user_text,
            input_type=input_type,
            output_type=output_type,
            session_id=session_id,
            tweaks=tweaks,
        )

        start = time.perf_counter()
        try:
            resp = post_run(
                base_url=base_url,
                flow_id=flow_id,
                payload=payload,
                headers=headers,
                timeout_seconds=timeout_seconds,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
        except requests.RequestException as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            print(f"[error] Request failed after {elapsed_ms:.0f} ms: {exc}")
            continue

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if resp.status_code != 200:
            print(f"[error] HTTP {resp.status_code} after {elapsed_ms:.0f} ms")
            try:
                print(resp.text)
            except Exception:
                pass
            continue

        try:
            data = resp.json()
        except json.JSONDecodeError:
            print(f"[warn] Non-JSON response after {elapsed_ms:.0f} ms:")
            print(resp.text)
            continue

        extracted = try_extract_text(data)
        if verbose:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"bot> {extracted}")
        print(f"[time] {elapsed_ms:.0f} ms\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())


