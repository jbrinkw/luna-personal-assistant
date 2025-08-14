import db
from agent import create_agent, run_agent, get_timestamp


def main():
    db.init_db(sample=True)
    agent = create_agent()
    print(f"{get_timestamp()} CoachByte demo. Type 'quit' to exit.")
    while True:
        user_input = input(f"{get_timestamp()} You: ")
        if user_input.strip().lower() in {"quit", "exit"}:
            break
        
        # Use the wrapper function with automatic timestamp inclusion
        result = run_agent(agent, user_input)
        print(f"{get_timestamp()} Agent: {result.final_output}")


if __name__ == "__main__":
    main()

