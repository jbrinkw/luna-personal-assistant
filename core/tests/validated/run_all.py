import os
import sys
import subprocess


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if REPO_ROOT not in sys.path:
	sys.path.insert(0, REPO_ROOT)


SCRIPTS = [
	os.path.join(REPO_ROOT, "core", "tests", "validated", "scripts", name)
	for name in [
		"coachbyte.py",
		"home_assistant.py",
		"todo_list.py",
		"notes.py",
		"generalbyte.py",
	]
]


def main(argv=None) -> int:
	failures = 0
	for path in SCRIPTS:
		print(f"\n=== Running {path} ===")
		try:
			proc = subprocess.run([sys.executable, path], capture_output=True, text=True)
			print(proc.stdout)
			if proc.stderr:
				print(proc.stderr)
			if proc.returncode != 0:
				failures += 1
		except Exception as e:
			print(f"<runner error: {e}>")
			failures += 1
	print(f"\n=== Completed. Exit code: {1 if failures else 0} ===")
	return 1 if failures else 0


if __name__ == "__main__":
	raise SystemExit(main(sys.argv[1:]))





