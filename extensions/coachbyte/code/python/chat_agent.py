import json
import os
import sys
import io

# Set environment variable for UTF-8 encoding on Windows
if os.name == 'nt':  # Windows
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from agent import create_agent, run_agent
from db import save_chat_message, get_recent_chat_messages


def safe_print(text):
    """
    Safely print text handling Unicode encoding errors.
    Falls back to removing problematic characters if needed.
    """
    try:
        # Try to reconfigure stdout to use utf-8 with error handling
        if hasattr(sys.stdout, 'reconfigure'):
            # Use getattr to avoid linter issues
            reconfigure_method = getattr(sys.stdout, 'reconfigure', None)
            if reconfigure_method:
                reconfigure_method(encoding='utf-8', errors='replace')
        print(text)
    except UnicodeEncodeError:
        try:
            # If that fails, try printing with ascii encoding and replace errors
            safe_text = text.encode('ascii', errors='replace').decode('ascii')
            print(safe_text)
        except Exception:
            # Last resort: remove all non-ascii characters
            safe_text = ''.join(char for char in text if ord(char) < 128)
            print(safe_text)
    except Exception as e:
        # Fallback for any other errors
        print(f"Error displaying message: {e}")
        print("Message content could not be displayed due to encoding issues.")


def main():
    if len(sys.argv) != 2:
        safe_print("Usage: python chat_agent.py <temp_file>")
        return 1
    temp_file = sys.argv[1]
    with open(temp_file, 'r', encoding='utf-8') as f:
        chat_data = json.load(f)
    message = chat_data.get('message', '')

    recent_messages = get_recent_chat_messages(25)
    context = ""
    if recent_messages:
        context += "Previous conversation context:\n"
        for msg in recent_messages:
            role = "User" if msg['type'] == 'user' else 'Assistant'
            context += f"{role}: {msg['content']}\n"
        context += "\n"

    message_with_context = context + "Current user message: " + message
    save_chat_message('user', message)

    agent = create_agent()
    result = run_agent(agent, message_with_context)

    if hasattr(result, 'final_output') and result.final_output:
        assistant_response = result.final_output
        save_chat_message('assistant', assistant_response)
        safe_print(assistant_response)
    else:
        error_msg = "Error: Could not extract final output"
        save_chat_message('assistant', error_msg)
        safe_print(error_msg)

    os.remove(temp_file)
    return 0


if __name__ == '__main__':
    sys.exit(main())
