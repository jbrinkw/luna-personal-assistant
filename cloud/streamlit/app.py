import streamlit as st
import requests
import os

# --- Configuration ---
# Determine the API URL based on environment (e.g., local vs. deployed)
# For local development, we assume the API runs on localhost:8000
# You might need to adjust this if your API runs elsewhere
API_BASE_URL = os.getenv("API_URL", "http://44.215.171.173:8000")
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"
RESET_ENDPOINT = f"{API_BASE_URL}/reset"

# --- Streamlit Page Setup ---
st.set_page_config(page_title="ChefByte Chat", page_icon="🍳")
st.title("🍳 ChefByte Assistant")
st.caption("Your friendly AI Cooking Companion")

# --- Session State Initialization ---
# Initialize chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! How can I help you with your cooking today?"}
    ]

# --- Helper Functions ---
def send_message_to_api(user_message):
    """Sends the user message to the FastAPI backend and returns the response."""
    try:
        response = requests.post(CHAT_ENDPOINT, json={"text": user_message}, timeout=60) # Increased timeout
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json().get("text", "Sorry, I received an unexpected response.")
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with ChefByte API: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

def reset_conversation_api():
    """Sends a request to reset the conversation history on the API."""
    try:
        response = requests.post(RESET_ENDPOINT, timeout=10)
        response.raise_for_status()
        return response.json().get("message", "Reset signal sent, but no confirmation message received.")
    except requests.exceptions.RequestException as e:
        st.error(f"Error sending reset signal to API: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during reset: {e}")
        return None

# --- Chat Interface ---

# Display existing messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input field for user message
if prompt := st.chat_input("What would you like to cook or ask about?"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get assistant response from API
    with st.spinner("ChefByte is thinking..."):
        assistant_response = send_message_to_api(prompt)

    # Display assistant response in chat message container
    if assistant_response:
        with st.chat_message("assistant"):
            st.markdown(assistant_response)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    else:
        # If API call failed, don't add an empty assistant message
        # Error is already displayed by send_message_to_api
        pass # Optionally add a default error message here if needed

# --- Sidebar Options ---
st.sidebar.title("Options")
if st.sidebar.button("Reset Conversation"):
    reset_message = reset_conversation_api()
    if reset_message:
        st.session_state.messages = [
            {"role": "assistant", "content": "Conversation history reset. How can I help you now?"}
        ]
        st.success(f"API Confirmation: {reset_message}")
        st.rerun() # Rerun the script to clear the chat display instantly
    else:
        st.error("Failed to reset conversation on the backend.")

st.sidebar.markdown("-----")
st.sidebar.markdown(f"API Status: `{API_BASE_URL}`") 