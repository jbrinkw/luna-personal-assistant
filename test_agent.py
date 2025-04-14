import subprocess
import sys
import os

def run_agent_test():
    """Runs agent_app.py with predefined inputs and captures output."""
    
    target_script = "agent_app.py"
    
    # Ensure the target script exists
    if not os.path.exists(target_script):
        print(f"Error: Target script '{target_script}' not found in the current directory.")
        print(f"Current directory: {os.getcwd()}")
        return

    # Define the sequence of inputs to send to the agent app
    inputs = (
        # Ask for the context that previously failed
        "what is in my shopping list",
        # Add an inventory check as well
        "what is in my inventory",
        # Add subsequent steps if needed for debugging context, e.g.:
        # "What's the plan for tomorrow?", 
        "quit"
    )

    print("---------------------------------------------")

    input_data = "\n".join(inputs) + "\n"

    print(f"--- Starting Proxy Test for {target_script} ---")
    print(f"Sending inputs:\n{input_data.strip()}")
    print("---------------------------------------------")

    # Run the agent_app.py as a subprocess
    process = subprocess.Popen(
        [sys.executable, target_script], # Use the same python interpreter
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True, # Work with text streams (auto-decode/encode)
        encoding='utf-8', # Explicitly set encoding
        errors='ignore', # Ignore decoding errors
        bufsize=1 # Line buffering
    )

    # Send input and capture output/error
    try:
        stdout_data, stderr_data = process.communicate(input=input_data, timeout=120)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout_data, stderr_data = process.communicate()
        print("\n--- ERROR: Process timed out ---")
        
    print("--- Agent App STDOUT --- ")
    print(stdout_data)
    print("--- End STDOUT ---")

    if stderr_data:
        print("--- Agent App STDERR --- ")
        print(stderr_data)
        print("--- End STDERR ---")
    else:
        print("--- Agent App STDERR (empty) ---")

    print(f"--- Proxy Test Finished (Exit Code: {process.returncode}) ---")

    # Basic checks
    if process.returncode != 0:
        print("*** TEST FAILED: Agent app exited with non-zero code.")
    # Ensure data is not None before checking for substrings
    elif (stdout_data and "Error" in stdout_data) or (stderr_data and "Error" in stderr_data):
         print("*** TEST WARNING: Potential errors detected in output.")
    # Check for the actual correct output format from the inventory context tool
    elif stdout_data and "CURRENT INVENTORY:" in stdout_data and "- Ground beef:" in stdout_data:
        print("*** TEST PASSED (Basic Check): Agent responded and inventory context found.")
    else:
        print("*** TEST FAILED: Did not find expected inventory output pattern (e.g., 'CURRENT INVENTORY:\n- Ground beef:') in STDOUT.")

if __name__ == "__main__":
    run_agent_test() 