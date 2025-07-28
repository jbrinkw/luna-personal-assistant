import db
import tools
from agent import create_agent


def reset_db():
    db.init_db()


def run_tests():
    reset_db()
    agent = create_agent()

    print("-- Create today's plan --")
    print("Before:", tools.run_sql("SELECT * FROM planned_sets"))
    plan = [
        {"exercise": "bench press", "order": 1, "reps": 10, "load": 100},
        {"exercise": "squat", "order": 2, "reps": 8, "load": 150},
    ]
    res = agent.invoke({"input": "Please set up today's workout with bench press for 10 reps at 100 pounds as set 1 and squat for 8 reps at 150 pounds as set 2."})
    print(res)
    print("After:", tools.run_sql("SELECT * FROM planned_sets"))

    print("-- Log completed set --")
    print("Before:", tools.run_sql("SELECT * FROM completed_sets"))
    res = agent.invoke({"input": "I just finished a bench press set of 10 reps at 100 pounds."})
    print(res)
    print("After:", tools.run_sql("SELECT * FROM completed_sets"))

    print("-- Update summary --")
    print("Before:", tools.run_sql("SELECT summary FROM daily_logs"))
    agent.invoke({"input": "Please record the summary 'Great session' for today."})
    print("After:", tools.run_sql("SELECT summary FROM daily_logs"))

    print("-- Get recent history --")
    res = agent.invoke({"input": "Show me the workout history for the last day."})
    print(res)


if __name__ == "__main__":
    run_tests()
