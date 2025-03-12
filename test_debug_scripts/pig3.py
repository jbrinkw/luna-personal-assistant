from app.db_functions import get_inventory, get_taste_profile, get_saved_meals, clear_table

def handle_command(command):
    command = command.lower().strip()
    
    # Show commands
    if command == '/show_inventory':
        inventory = get_inventory()
        print("Inventory:", inventory)
    elif command == '/show_taste_profile':
        taste_profile = get_taste_profile()
        print("Taste Profile:", taste_profile)
    elif command == '/show_saved_meals':
        saved_meals = get_saved_meals()
        print("Saved Meals:", saved_meals)
    
    # Clear commands
    elif command == '/clear_inventory':
        clear_table('inventory')
        print("Inventory table cleared!")
    elif command == '/clear_taste_profile':
        clear_table('taste_profile')
        print("Taste profile table cleared!")
    elif command == '/clear_saved_meals':
        clear_table('meals')  # Changed from 'saved_meals' to 'meals'
        print("Saved meals table cleared!")
    
    # Help command
    elif command == '/help':
        print("\nAvailable commands:")
        print("  /show_inventory - Display inventory")
        print("  /show_taste_profile - Display taste profile")
        print("  /show_saved_meals - Display saved meals")
        print("  /clear_inventory - Clear inventory table")
        print("  /clear_taste_profile - Clear taste profile table")
        print("  /clear_saved_meals - Clear saved meals table")
        print("  /quit - Exit the program")
        print("  /help - Show this help message\n")
    
    elif command == '/quit':
        return False
    else:
        print("Unknown command. Type /help for available commands.")
    
    return True

def main():
    print("Welcome to the Database Management CLI")
    print("Type /help for available commands")
    print("Type /quit to exit")
    
    running = True
    while running:
        command = input("\n> ")
        running = handle_command(command)

if __name__ == "__main__":
    main()