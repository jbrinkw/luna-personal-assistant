import db
from agent import create_agent


def main():
    db.init_db(sample=True)
    agent = create_agent()
    print("CoachByte demo. Type 'quit' to exit.")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in {"quit", "exit"}:
            break
        result = agent.invoke({"input": user_input})
        print(result.get("output"))


if __name__ == "__main__":
    main()
