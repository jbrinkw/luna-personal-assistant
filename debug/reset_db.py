import sys
import os
import json
from datetime import datetime, timedelta
import traceback

# Add project root to sys.path to allow importing db_functions
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import the database functions
from db.db_functions import Database, Inventory, TasteProfile, SavedMeals
from db.db_functions import NewMealIdeas, SavedMealsInStockIds, NewMealIdeasInStockIds
from db.db_functions import DailyPlanner, ShoppingList, IngredientsFood, init_tables, DB_PATH
from db.meal_availability import MealAvailabilityUpdater, update_all_meal_availability
from db.ingredient_matcher import IngredientMatcher

class ResetDB:
    def __init__(self, add_to_shopping_list=False):
        # Initialize database connection and table objects
        self.db, self.tables = init_tables()
        # Whether to add missing ingredients to shopping list
        self.add_to_shopping_list = add_to_shopping_list
        
        # Hardcoded meals list
        self.meals = [
            ["Bacon Cheeseburger", 20, 
             [{"name": "Ground beef", "quantity": "to taste"}, {"name": "bacon", "quantity": "to taste"}, 
              {"name": "burger bun", "quantity": "to taste"}, {"name": "extra sharp cheddar", "quantity": "to taste"}, 
              {"name": "condiments", "quantity": "to taste"}], 
             "Form beef patties, cook to desired doneness; fry bacon; assemble patty with bacon and cheese on bun."],
            ["Sesame Chicken", 25, 
             [{"name": "Chicken pieces", "quantity": "to taste"}, {"name": "sesame seeds", "quantity": "to taste"}, 
              {"name": "soy sauce", "quantity": "to taste"}, {"name": "garlic", "quantity": "to taste"}, 
              {"name": "ginger", "quantity": "to taste"}, {"name": "cornstarch", "quantity": "to taste"}], 
             "Marinate chicken in soy sauce, garlic, and ginger; coat lightly with cornstarch; stir-fry until cooked; sprinkle sesame seeds."],
            ["Magic Spaghetti", 15, 
             [{"name": "Spaghetti", "quantity": "to taste"}, {"name": "parmesan cheese", "quantity": "to taste"}, 
              {"name": "butter", "quantity": "to taste"}, {"name": "olive oil", "quantity": "to taste"}, 
              {"name": "pepper", "quantity": "to taste"}], 
             "Cook spaghetti; toss with butter, olive oil, parmesan, and pepper."],
            ["Steak Burrito", 25, 
             [{"name": "Thin-sliced steak", "quantity": "to taste"}, {"name": "white rice", "quantity": "to taste"}, 
              {"name": "black beans", "quantity": "to taste"}, {"name": "tortilla", "quantity": "to taste"}, 
              {"name": "extra cheese", "quantity": "to taste"}, {"name": "mayo", "quantity": "to taste"}], 
             "Sauté steak strips; warm rice and beans; layer steak, rice, beans, cheese, and mayo on tortilla; roll up."],
            ["Breakfast Egg Sandwich", 15, 
             [{"name": "Eggs", "quantity": "to taste"}, {"name": "cheese", "quantity": "to taste"}, 
              {"name": "turkey sausage patties", "quantity": "to taste"}, {"name": "sourdough bread", "quantity": "to taste"}, 
              {"name": "mayo", "quantity": "to taste"}], 
             "Scramble eggs with cheese; heat sausage patties; toast sourdough with mayo; assemble sandwich."],
            ["Homemade McChicken", 20, 
             [{"name": "Chicken patties", "quantity": "to taste"}, {"name": "burger buns", "quantity": "to taste"}, 
              {"name": "mayo", "quantity": "to taste"}], 
             "Cook chicken patties; toast buns with a bit of mayo; place patty between buns."],
            ["Chicken Caesar Wrap", 15, 
             [{"name": "Pre-cooked chicken", "quantity": "to taste"}, {"name": "tortilla", "quantity": "to taste"}, 
              {"name": "shredded cheese", "quantity": "to taste"}, {"name": "Caesar dressing", "quantity": "to taste"}], 
             "Layer sliced chicken, cheese, and Caesar dressing in tortilla; roll tightly."],
            ["Turkey and Cheese Sandwich", 10, 
             [{"name": "Sliced turkey", "quantity": "to taste"}, {"name": "cheese", "quantity": "to taste"}, 
              {"name": "toasted sourdough or bagel", "quantity": "to taste"}, {"name": "mayo", "quantity": "to taste"}], 
             "Layer turkey and cheese on toasted bread/bagel with mayo."],
            ["Grilled Cheese Sandwich", 10, 
             [{"name": "Bread", "quantity": "to taste"}, {"name": "butter", "quantity": "to taste"}, 
              {"name": "sliced cheese", "quantity": "to taste"}], 
             "Butter bread on outside, add cheese in between; grill until golden."],
            ["Quesadilla", 15, 
             [{"name": "Tortilla", "quantity": "to taste"}, {"name": "cheese", "quantity": "to taste"}, 
              {"name": "pre-cooked chicken or turkey", "quantity": "to taste"}], 
             "Fill tortilla with cheese and meat; cook in pan until tortilla is crispy and cheese melts."],
            ["Mac and Cheese with Bacon", 15, 
             [{"name": "Boxed mac and cheese", "quantity": "to taste"}, {"name": "bacon bits", "quantity": "to taste"}], 
             "Prepare mac and cheese per box directions; stir in cooked bacon bits."],
            ["Instant Ramen with Egg", 10, 
             [{"name": "Instant ramen", "quantity": "to taste"}, {"name": "egg", "quantity": "to taste"}, 
              {"name": "water", "quantity": "to taste"}], 
             "Cook ramen as directed; add a boiled or poached egg before serving."],
            ["Bagel with Cream Cheese and Bacon", 10, 
             [{"name": "Bagel", "quantity": "to taste"}, {"name": "cream cheese", "quantity": "to taste"}, 
              {"name": "bacon", "quantity": "to taste"}], 
             "Toast bagel; spread cream cheese; add cooked bacon."],
            ["Spaghetti with Meat Sauce", 25, 
             [{"name": "Spaghetti", "quantity": "to taste"}, {"name": "ground beef", "quantity": "to taste"}, 
              {"name": "non-chunky tomato sauce", "quantity": "to taste"}, {"name": "parmesan", "quantity": "to taste"}], 
             "Cook spaghetti; brown ground beef; mix with tomato sauce; serve over pasta with parmesan."],
            ["Chicken Alfredo", 20, 
             [{"name": "Pasta", "quantity": "to taste"}, {"name": "store-bought Alfredo sauce", "quantity": "to taste"}, 
              {"name": "pre-cooked chicken", "quantity": "to taste"}], 
             "Cook pasta; heat Alfredo sauce and chicken together; combine with pasta."],
            ["Pulled Pork with BBQ", 25, 
             [{"name": "Pre-cooked pulled pork", "quantity": "to taste"}, {"name": "BBQ sauce", "quantity": "to taste"}, 
              {"name": "instant mashed potatoes or rice", "quantity": "to taste"}], 
             "Heat pulled pork with BBQ sauce; serve with instant mashed potatoes or rice."],
            ["Shrimp Scampi", 15, 
             [{"name": "Pre-cooked shrimp", "quantity": "to taste"}, {"name": "pasta", "quantity": "to taste"}, 
              {"name": "garlic", "quantity": "to taste"}, {"name": "butter", "quantity": "to taste"}, 
              {"name": "olive oil", "quantity": "to taste"}, {"name": "parsley", "quantity": "to taste"}], 
             "Cook pasta; sauté garlic in butter and olive oil; add shrimp; toss with pasta and parsley."],
            ["Philly Cheesesteak Sliders", 25, 
             [{"name": "Thinly sliced steak", "quantity": "to taste"}, {"name": "slider buns", "quantity": "to taste"}, 
              {"name": "cheese", "quantity": "to taste"}, {"name": "onions", "quantity": "to taste"}], 
             "Sauté steak and onions; place mixture and cheese on slider buns; heat until cheese melts."],
            ["Chicken Tenders and Fries", 25, 
             [{"name": "Pre-breaded chicken tenders", "quantity": "to taste"}, {"name": "frozen fries", "quantity": "to taste"}], 
             "Bake chicken tenders and fries as per package instructions; serve together."],
            ["Beef Tacos", 20, 
             [{"name": "Ground beef", "quantity": "to taste"}, {"name": "taco seasoning", "quantity": "to taste"}, 
              {"name": "taco shells", "quantity": "to taste"}, {"name": "cheese", "quantity": "to taste"}], 
             "Cook beef with taco seasoning; fill taco shells with beef and top with cheese."],
            ["Stir-Fry with Pre-Cooked Chicken", 20, 
             [{"name": "Pre-cooked chicken strips", "quantity": "to taste"}, {"name": "frozen mixed vegetables", "quantity": "to taste"}, 
              {"name": "soy sauce", "quantity": "to taste"}, {"name": "microwaveable rice", "quantity": "to taste"}], 
             "Stir-fry chicken and vegetables with soy sauce; serve over heated rice."],
            ["Pasta with Pesto", 15, 
             [{"name": "Pasta", "quantity": "to taste"}, {"name": "store-bought pesto", "quantity": "to taste"}, 
              {"name": "parmesan cheese", "quantity": "to taste"}], 
             "Cook pasta; toss with pesto and sprinkle parmesan on top."],
            ["Sloppy Joes", 20, 
             [{"name": "Ground beef", "quantity": "to taste"}, {"name": "sloppy joe sauce", "quantity": "to taste"}, 
              {"name": "hamburger buns", "quantity": "to taste"}], 
             "Brown ground beef; mix with sloppy joe sauce; spoon onto hamburger buns."]
        ]
        
        # Hardcoded meal ideas list
        self.meal_ideas = [
            ('Garlic Salmon Pasta', 30, 
             [{"name": "salmon", "quantity": "to taste"}, {"name": "spaghetti", "quantity": "to taste"}, 
              {"name": "garlic", "quantity": "to taste"}, {"name": "olive oil", "quantity": "to taste"}, 
              {"name": "parmesan cheese", "quantity": "to taste"}], 
             '1. Cook spaghetti according to package instructions. \n2. In a pan, heat olive oil and garlic, then add salmon and cook until done. \n3. Combine cooked pasta with salmon, garlic, and olive oil. \n4. Serve with grated parmesan cheese on top.'),
            ('Bacon Egg Sourdough Toast', 20, 
             [{"name": "sourdough bread", "quantity": "to taste"}, {"name": "eggs", "quantity": "to taste"}, 
              {"name": "bacon", "quantity": "to taste"}, {"name": "shredded cheese", "quantity": "to taste"}, 
              {"name": "butter", "quantity": "to taste"}],
             '1. Cook bacon until crispy, then scramble eggs. \n2. Toast sourdough bread slices. \n3. Assemble by placing scrambled eggs and bacon on top of the toast. \n4. Sprinkle shredded cheese and melt under broiler. \n5. Serve hot with a side of butter.'),
            ('Sesame Ginger Chicken Wrap', 25, 
             [{"name": "rotisserie chicken", "quantity": "to taste"}, {"name": "tortilla", "quantity": "to taste"}, 
              {"name": "garlic", "quantity": "to taste"}, {"name": "ginger", "quantity": "to taste"}, 
              {"name": "sesame seeds", "quantity": "to taste"}, {"name": "soy sauce", "quantity": "to taste"}, 
              {"name": "shredded cheese", "quantity": "to taste"}],
             '1. Shred rotisserie chicken and mix with garlic, ginger, sesame seeds, and soy sauce. \n2. Warm tortilla and fill with the chicken mixture. \n3. Sprinkle shredded cheese on top. \n4. Roll up the wrap and enjoy.'),
            ('Cheesy Chicken Tortilla Bake', 40, 
             [{"name": "pre-cooked chicken", "quantity": "to taste"}, {"name": "tortilla", "quantity": "to taste"}, 
              {"name": "non-chunky tomato sauce", "quantity": "to taste"}, {"name": "shredded cheese", "quantity": "to taste"}, 
              {"name": "onions", "quantity": "to taste"}],
             '1. Preheat oven to 350°F. \n2. Layer tortillas, chicken, tomato sauce, onions, and shredded cheese in a baking dish. \n3. Repeat layers and top with more cheese. \n4. Bake for 25-30 minutes until cheese is melted and bubbly. \n5. Serve hot.'),
            ('Bacon Egg Fried Rice', 25, 
             [{"name": "Bacon", "quantity": "to taste"}, {"name": "Eggs", "quantity": "to taste"}, 
              {"name": "White rice", "quantity": "to taste"}, {"name": "Onion", "quantity": "to taste"}, 
              {"name": "Garlic", "quantity": "to taste"}, {"name": "Frozen mixed vegetables", "quantity": "to taste"}, 
              {"name": "Soy sauce", "quantity": "to taste"}, {"name": "Olive oil", "quantity": "to taste"}],
             '1. Cook bacon until crispy, then set aside. \n2. In the same pan, sauté onions and garlic. \n3. Add cooked white rice and frozen mixed vegetables. \n4. Push rice to the side, scramble eggs, and mix in. \n5. Crumble bacon and add to the rice. \n6. Season with soy sauce and serve hot.'),
            ('Chicken Tomato Garlic Pasta', 30, 
             [{"name": "Rotisserie chicken", "quantity": "to taste"}, {"name": "Spaghetti", "quantity": "to taste"}, 
              {"name": "Non-chunky tomato sauce", "quantity": "to taste"}, {"name": "Garlic", "quantity": "to taste"}, 
              {"name": "Olive oil", "quantity": "to taste"}, {"name": "Parmesan cheese", "quantity": "to taste"}],
             '1. Cook spaghetti according to package instructions. \n2. In a pan, heat olive oil and garlic, then add shredded rotisserie chicken. \n3. Pour in tomato sauce and simmer. \n4. Toss cooked pasta in the sauce. \n5. Serve with grated parmesan cheese on top.'),
            ('Ginger Soy Salmon Stir-Fry', 25, 
             [{"name": "Salmon", "quantity": "to taste"}, {"name": "Frozen mixed vegetables", "quantity": "to taste"}, 
              {"name": "Onion", "quantity": "to taste"}, {"name": "Garlic", "quantity": "to taste"}, 
              {"name": "Ginger", "quantity": "to taste"}, {"name": "Soy sauce", "quantity": "to taste"}, 
              {"name": "Microwaveable rice", "quantity": "to taste"}],
             '1. In a pan, stir-fry salmon, vegetables, onion, garlic, and ginger. \n2. Add soy sauce and cook until salmon is done. \n3. Microwave rice according to package instructions. \n4. Serve stir-fry over rice.'),
            ('Steak Cheddar Sourdough Melt', 35, 
             [{"name": "Thin-sliced steak", "quantity": "to taste"}, {"name": "Sourdough bread", "quantity": "to taste"}, 
              {"name": "Shredded cheese", "quantity": "to taste"}, {"name": "Onion", "quantity": "to taste"}, 
              {"name": "Butter", "quantity": "to taste"}, {"name": "Mayo", "quantity": "to taste"}],
             '1. Cook steak slices in a pan until desired doneness. \n2. Butter sourdough bread slices and toast. \n3. Spread mayo on one side of the bread. \n4. Layer steak, shredded cheese, and onions on the other side. \n5. Close the sandwich and grill until cheese melts. \n6. Serve hot.'),
            ('Shrimp and Bacon Carbonara', 30, 
             [{"name": "Pre-cooked shrimp", "quantity": "to taste"}, {"name": "Bacon", "quantity": "to taste"}, 
              {"name": "Eggs", "quantity": "to taste"}, {"name": "Spaghetti", "quantity": "to taste"}, 
              {"name": "Parmesan cheese", "quantity": "to taste"}, {"name": "Olive oil", "quantity": "to taste"}, 
              {"name": "Garlic", "quantity": "to taste"}],
             '1. Cook bacon until crispy, then set aside. \n2. In the same pan, sauté garlic and shrimp. \n3. Cook spaghetti according to package instructions. \n4. Whisk eggs and parmesan cheese in a bowl. \n5. Drain pasta and toss with egg mixture. \n6. Add shrimp and crumbled bacon. \n7. Serve hot.')
        ]
    
        # Default inventory items
        self.inventory_items = [
            "Ground beef", "Bacon", "Sesame seeds", "Soy sauce", "Garlic",
            "Ginger", "Spaghetti", "Parmesan cheese", "Butter", "Olive oil",
            "Thin-sliced steak", "White rice", "Black beans", "Tortilla", "Mayo",
            "Eggs", "Sourdough bread", "Pre-cooked chicken", "Shredded cheese",
            "Caesar dressing", "Instant ramen", "Non-chunky tomato sauce",
            "Pre-cooked pulled pork", "BBQ sauce", "Instant mashed potatoes",
            "Pre-cooked shrimp", "Onions", "Taco seasoning", "Taco shells",
            "Frozen mixed vegetables", "Microwaveable rice", "Rotisserie chicken",
            "Salmon", "Tortilla chips", "Whole milk", "Frozen waffles",
            "Microwave burrito", "Carrots"
        ]
        
        # Sample data for ingredients_foods with shorter URLs
        self.ingredients_foods = [
            {"name": "Fairlife chocolate milk", "min_amount": 1, 
            "walmart_link": "https://www.walmart.com/ip/43922523"},
            {"name": "Whole milk", "min_amount": 1, 
            "walmart_link": "https://www.walmart.com/ip/10450114"},
            {"name": "Cream cheese", "min_amount": 1, 
            "walmart_link": "https://www.walmart.com/ip/10295585"}
        ]
    
        # Taste profile string
        self.taste_profile = """
Proteins:
- Hard-boiled eggs
- Rotisserie chicken
- Pre-cooked sausage
- Bacon
- Deli meats
- Salmon
- Tilapia

Carbs & Grains:
- Pasta varieties (plain, mac and cheese)
- Bread (sourdough, tortillas, bagels)
- Instant rice
- Instant mashed potatoes
- Tortilla chips

Dairy:
- Extra sharp cheddar
- Cream cheese
- Shredded cheese
- Whole milk
- Fairlife chocolate milk

Frozen/Pre-Made Convenience Items:
- Frozen waffles, pancakes, French toast sticks
- Microwave burrito
- Hamburger Helper (boxed meal)
- Pre-packaged frozen meals:
  * Devour Frozen White Cheddar with Bacon Mac n Cheese
  * Stouffer's fettuccine Alfredo
  * Jimmy Dean frozen sausage biscuits
  * Freschetta plain cheese pizza
  * Frozen fish sticks

Vegetables (Preferred):
- Carrots
- Peas
- Corn
- Sweet potatoes
- Regular potatoes
- Green beans
- Non-chunky tomato sauce
- Broccoli
- Most beans

Dislikes:
- Fruits
- Greek yogurt
- Cottage cheese
- Yogurt
- Lettuce
- Peppers
- Avocado
- Spinach
- Hummus
- Tuna
- Oatmeal
"""
    
    # --- CLEAR FUNCTIONS ---
    
    def clear_saved_meals(self):
        """Clears the saved_meals table."""
        print("\nClearing saved meals...")
        
        # Create the table
        self.tables["saved_meals"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['saved_meals'].table_name}")
        
        print("✓ Saved meals cleared")
    
    def clear_taste_profile(self):
        """Clears the taste profile table."""
        print("\nClearing taste profile...")
        
        # Create the table
        self.tables["taste_profile"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['taste_profile'].table_name}")
        
        print("✓ Taste profile cleared")
    
    def clear_inventory(self):
        """Clears the inventory table."""
        print("\nClearing inventory...")
        
        # Create the table
        self.tables["inventory"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['inventory'].table_name}")
        
        print("✓ Inventory cleared")
    
    def clear_new_meal_ideas(self):
        """Clears the new_meal_ideas table."""
        print("\nClearing new meal ideas...")
        
        # Create the table
        self.tables["new_meal_ideas"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['new_meal_ideas'].table_name}")
        
        # Get the correct sequence name before resetting
        sequence_result = self.db.execute_query(
            "SELECT pg_get_serial_sequence('new_meal_ideas', 'id')",
            fetch=True
        )
        
        if sequence_result and sequence_result[0][0]:
            sequence_name = sequence_result[0][0]
            self.db.execute_query(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1")
            print(f"Reset ID sequence: {sequence_name}")
        else:
            print("Warning: Could not find sequence for id column")
            
        print("✓ New meal ideas cleared")
    
    def clear_daily_planner(self):
        """Clears the daily_planner table."""
        print("\nClearing daily planner...")
        
        # Create the table
        self.tables["daily_planner"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['daily_planner'].table_name}")
        
        print("✓ Daily planner cleared")
    
    def clear_shopping_list(self):
        """Clears the shopping_list table."""
        print("\nClearing shopping list...")
        
        # Create the table
        self.tables["shopping_list"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['shopping_list'].table_name}")
        
        print("✓ Shopping list cleared")
    
    def clear_ingredients_foods(self):
        """Clears the ingredients_foods table."""
        print("\nClearing ingredients foods...")
        
        # Create the table
        self.tables["ingredients_foods"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['ingredients_foods'].table_name}")
        
        print("✓ Ingredients foods cleared")
    
    def clear_saved_meals_instock_ids(self):
        """Clears the saved_meals_instock_ids table."""
        print("\nClearing saved meals in stock IDs...")
        
        # Create the table
        self.tables["saved_meals_instock_ids"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['saved_meals_instock_ids'].table_name}")
        
        print("✓ Saved meals in stock IDs cleared")
    
    def clear_new_meal_ideas_instock_ids(self):
        """Clears the new_meal_ideas_instock_ids table."""
        print("\nClearing new meal ideas in stock IDs...")
        
        # Create the table
        self.tables["new_meal_ideas_instock_ids"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['new_meal_ideas_instock_ids'].table_name}")
        
        print("✓ New meal ideas in stock IDs cleared")

    def clear_all(self):
        """Clears all tables."""
        print("Starting complete database clear...")
        
        # Clear all tables
        self.clear_saved_meals()
        self.clear_new_meal_ideas()
        self.clear_taste_profile()
        self.clear_inventory()
        self.clear_daily_planner()
        self.clear_shopping_list()
        self.clear_ingredients_foods()
        self.clear_saved_meals_instock_ids()
        self.clear_new_meal_ideas_instock_ids()
        
        print("\nDone! All tables have been cleared.")

    # --- LOAD FUNCTIONS ---
    
    def load_saved_meals(self):
        """Loads sample data into the saved_meals table."""
        print("\nLoading saved meals...")
        
        # Insert sample data
        for idx, meal in enumerate(self.meals):
            name, prep_time, ingredients, recipe = meal
            meal_id = self.tables["saved_meals"].create(name, prep_time, ingredients, recipe)
            
            if meal_id is not None:
                print(f"✓ Added: {name}")
            else:
                print(f"✗ Failed to add: {name}")
    
    def load_taste_profile(self):
        """Loads sample data into the taste profile table."""
        print("\nLoading taste profile...")
        
        # Insert sample data
        success = self.tables["taste_profile"].create(self.taste_profile)
        
        if success is not None:
            print("✓ Taste profile updated successfully")
        else:
            print("✗ Failed to update taste profile")
    
    def load_inventory(self):
        """Loads sample data into the inventory table."""
        print("\nLoading inventory...")
        
        # Set default expiration date
        default_expiration = datetime.now() + timedelta(days=7)
        
        # Insert sample data
        for item in self.inventory_items:
            item_id = self.tables["inventory"].create(item, "1", default_expiration)
            
            if item_id is not None:
                print(f"✓ Added: {item}")
            else:
                print(f"✗ Failed to add: {item}")
    
    def load_new_meal_ideas(self):
        """Loads sample data into the new_meal_ideas table."""
        print("\nLoading new meal ideas...")
        
        # Insert sample data
        for meal in self.meal_ideas:
            name, prep_time, ingredients, recipe = meal
            new_id = self.tables["new_meal_ideas"].create(name, prep_time, ingredients, recipe)
            
            if new_id is not None:
                print(f"✓ Added meal idea: {name} with id {new_id}")
            else:
                print(f"✗ Failed to add meal idea: {name}")
    
    def load_daily_planner(self):
        """Loads sample data into the daily_planner table for 2025."""
        print("\nLoading daily planner...")
        
        # Insert entries for each day of 2025
        start_date = datetime(2025, 1, 1).date()
        end_date = datetime(2025, 12, 31).date()
        current_date = start_date
        
        while current_date <= end_date:
            success = self.tables["daily_planner"].create(current_date, None, [])
            current_date += timedelta(days=1)
        
        print("✓ Daily planner populated for 2025")
    
    def load_shopping_list(self):
        """Initializes the shopping_list table."""
        print("\nLoading shopping list...")
        print("✓ Shopping list initialized (empty)")
    
    def load_ingredients_foods(self):
        """Loads sample data into the ingredients_foods table."""
        print("\nLoading ingredients foods...")
        
        # Insert sample data
        for item in self.ingredients_foods:
            food_id = self.tables["ingredients_foods"].create(
                item["name"],
                item["min_amount"],
                item["walmart_link"]
            )
            
            if food_id is not None:
                print(f"✓ Added ingredient: {item['name']}")
            else:
                print(f"✗ Failed to add ingredient: {item['name']}")
    
    def load_saved_meals_instock_ids(self):
        """
        Updates the saved_meals_instock_ids table using meal availability checker.
        Can optionally add missing ingredients to shopping list.
        """
        print("\nUpdating saved meals in stock IDs...")
        
        # Use the meal availability updater
        updater = MealAvailabilityUpdater(self.db)
        available_meals = updater.update_saved_meals_availability(self.add_to_shopping_list)
        
        print(f"✓ Found {len(available_meals)} saved meals that can be made with current inventory")
        if available_meals:
            print(f"  Meal IDs: {available_meals[:5]}{'...' if len(available_meals) > 5 else ''}")
        
        if self.add_to_shopping_list:
            print("  Missing ingredients added to shopping list")
    
    def load_new_meal_ideas_instock_ids(self):
        """
        Updates the new_meal_ideas_instock_ids table using meal availability checker.
        Can optionally add missing ingredients to shopping list.
        """
        print("\nUpdating new meal ideas in stock IDs...")
        
        # Use the meal availability updater
        updater = MealAvailabilityUpdater(self.db)
        available_meal_ideas = updater.update_new_meal_ideas_availability(self.add_to_shopping_list)
        
        print(f"✓ Found {len(available_meal_ideas)} meal ideas that can be made with current inventory")
        if available_meal_ideas:
            print(f"  Meal IDs: {available_meal_ideas[:5]}{'...' if len(available_meal_ideas) > 5 else ''}")
        
        if self.add_to_shopping_list:
            print("  Missing ingredients added to shopping list")
    
    def update_all_meal_availability(self):
        """
        Updates both in-stock tables using the meal availability checker.
        Can optionally add missing ingredients to shopping list.
        """
        print("\nUpdating all meal availability...")
        
        results = update_all_meal_availability(self.add_to_shopping_list)
        
        print(f"✓ Found {len(results['saved_meals'])} saved meals and {len(results['new_meal_ideas'])} meal ideas that can be made with current inventory")
        
        if self.add_to_shopping_list:
            print("  Missing ingredients added to shopping list")
        
        return results
    
    def load_all(self):
        """Loads sample data into all tables."""
        print("Starting complete database load...")
        
        # Load all tables
        self.load_saved_meals()
        self.load_new_meal_ideas()
        self.load_taste_profile()
        self.load_inventory()
        self.load_daily_planner()
        self.load_shopping_list()
        self.load_ingredients_foods()
        
        # Update meal availability after loading inventory and meals
        self.update_all_meal_availability()
        
        print("\nDone! All tables have been loaded with sample data.")

    # --- RELOAD FUNCTIONS ---
    
    def reload_saved_meals(self):
        """Clears and reloads the saved_meals table."""
        self.clear_saved_meals()
        self.load_saved_meals()
    
    def reload_taste_profile(self):
        """Clears and reloads the taste profile table."""
        self.clear_taste_profile()
        self.load_taste_profile()
    
    def reload_inventory(self):
        """Clears and reloads the inventory table."""
        self.clear_inventory()
        self.load_inventory()
        
        # After reloading inventory, update meal availability
        self.update_all_meal_availability()
    
    def reload_new_meal_ideas(self):
        """Clears and reloads the new_meal_ideas table."""
        self.clear_new_meal_ideas()
        self.load_new_meal_ideas()
    
    def reload_daily_planner(self):
        """Clears and reloads the daily_planner table."""
        self.clear_daily_planner()
        self.load_daily_planner()
    
    def reload_shopping_list(self):
        """Clears and reloads the shopping_list table."""
        self.clear_shopping_list()
        self.load_shopping_list()
    
    def reload_ingredients_foods(self):
        """Clears and reloads the ingredients_foods table."""
        self.clear_ingredients_foods()
        self.load_ingredients_foods()
    
    def reload_saved_meals_instock_ids(self):
        """Clears and updates the saved_meals_instock_ids table."""
        self.clear_saved_meals_instock_ids()
        self.load_saved_meals_instock_ids()
    
    def reload_new_meal_ideas_instock_ids(self):
        """Clears and updates the new_meal_ideas_instock_ids table."""
        self.clear_new_meal_ideas_instock_ids()
        self.load_new_meal_ideas_instock_ids()
    
    def reload_all(self):
        """Clears and reloads all tables."""
        print("Starting complete database reload...")
        self.clear_all()
        self.load_all()
        print("\nDone! Database has been completely reloaded with sample data.")
    
    # --- LEGACY METHODS (KEPT FOR BACKWARD COMPATIBILITY) ---
    
    def reset_saved_meals(self):
        """Legacy method: Clears and repopulates the saved_meals table."""
        self.reload_saved_meals()
    
    def reset_taste_profile(self):
        """Legacy method: Clears and resets the taste profile table."""
        self.reload_taste_profile()
    
    def reset_inventory(self):
        """Legacy method: Clears and repopulates the inventory table."""
        self.reload_inventory()
    
    def reset_new_meal_ideas(self):
        """Legacy method: Clears and repopulates the new_meal_ideas table."""
        self.reload_new_meal_ideas()
    
    def reset_daily_planner(self):
        """Legacy method: Clears and populates the daily_planner table for 2025."""
        self.reload_daily_planner()
    
    def reset_shopping_list(self):
        """Legacy method: Clears and initializes the shopping_list table."""
        self.reload_shopping_list()
    
    def reset_ingredients_foods(self):
        """Legacy method: Clears and populates the ingredients_foods table with sample data."""
        self.reload_ingredients_foods()
    
    def reset_saved_meals_instock_ids(self):
        """Legacy method: Clears the saved_meals_instock_ids table."""
        self.reload_saved_meals_instock_ids()
    
    def reset_new_meal_ideas_instock_ids(self):
        """Legacy method: Clears the new_meal_ideas_instock_ids table."""
        self.reload_new_meal_ideas_instock_ids()
    
    def reset_all(self):
        """Legacy method: Runs the complete reset process."""
        self.reload_all()

def reset_database():
    """Resets the SQLite database by clearing data and reloading sample data."""
    print(f"Attempting to reset data in database: {DB_PATH}")
    db = None # Initialize db to None
    try:
        # Initialize db connection and ensure tables exist
        # This also ensures the db file exists for the ResetDB class later
        db, tables = init_tables()
        
        if not db or not tables:
            print("[ERROR] Failed to initialize database connection or tables. Cannot reset.")
            return
            
        print("Clearing data from tables...")
        success_count = 0
        fail_count = 0
        for table_name, table_obj in tables.items():
            print(f"  Clearing table: {table_name}...")
            try:
                if hasattr(table_obj, 'table_name'):
                    delete_query = f"DELETE FROM {table_obj.table_name};"
                    db.execute_query(delete_query)
                    print(f"    Table '{table_name}' cleared.")
                    success_count += 1
                else:
                     print(f"    Skipping {table_name}: Cannot determine table name from object.")
                     fail_count += 1
            except Exception as table_e:
                print(f"    [ERROR] Failed to clear table '{table_name}': {table_e}")
                fail_count += 1
                
        # Optional: Reclaim space
        if fail_count == 0:
             print("All tables cleared successfully. Vacuuming database...")
             try:
                  db.execute_query("VACUUM;")
                  print("Database vacuumed.")
             except Exception as vac_e:
                  print(f"[WARN] Failed to vacuum database: {vac_e}")
        else:
             print(f"Finished clearing tables with {fail_count} errors.")

        # --- Load Sample Data --- 
        print("\nLoading sample data...")
        # Instantiate the ResetDB class to use its loading methods
        # Pass add_to_shopping_list=False by default, or make it configurable
        reset_db_loader = ResetDB(add_to_shopping_list=False) 
        reset_db_loader.load_all() # Use the method that loads all sample data
        # ------------------------

        print("\nDatabase reset and sample data loading complete.")
            
    except Exception as e:
        print(f"[ERROR] An error occurred during database reset/load: {e}")
        print(traceback.format_exc())
    finally:
         # Ensure connection is closed (init_tables connects, load_all might too)
         if db and db.conn:
              db.disconnect()
         # Also ensure the loader's connection is closed if it's separate
         if 'reset_db_loader' in locals() and reset_db_loader.db and reset_db_loader.db.conn:
              if reset_db_loader.db != db: # Only disconnect if it's a different connection object
                   reset_db_loader.db.disconnect()

if __name__ == "__main__":
    # Reset and load directly without confirmation
    reset_database()