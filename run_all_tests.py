import subprocess
import sys
import json

TEST_SCRIPTS = [
    "chefbyte/test_agent.py",
    "coachbyte/test_agent.py",
    "generalbyte/test_agent.py",
]


def run_script(path):
    proc = subprocess.run([sys.executable, path], capture_output=True, text=True)
    return {
        "script": path,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main():
    results = [run_script(s) for s in TEST_SCRIPTS]
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
