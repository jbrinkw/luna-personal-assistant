from app.db_functions import clear_table, get_all_table_names, run_query
from datetime import datetime, timedelta
from meal_suggestions.in_stock_checker import InStockChecker

class ResetDB:
    def __init__(self):
        # Hardcoded meals list
        self.meals = [
            ["Bacon Cheeseburger", "20 min", 
             "Ground beef, bacon, burger bun, extra sharp cheddar, condiments", 
             "Form beef patties, cook to desired doneness; fry bacon; assemble patty with bacon and cheese on bun."],
            ["Sesame Chicken", "25 min", 
             "Chicken pieces, sesame seeds, soy sauce, garlic, ginger, cornstarch", 
             "Marinate chicken in soy sauce, garlic, and ginger; coat lightly with cornstarch; stir-fry until cooked; sprinkle sesame seeds."],
            ["Magic Spaghetti", "15 min", 
             "Spaghetti, parmesan cheese, butter, olive oil, pepper", 
             "Cook spaghetti; toss with butter, olive oil, parmesan, and pepper."],
            ["Steak Burrito", "25 min", 
             "Thin-sliced steak, white rice, black beans, tortilla, extra cheese, mayo", 
             "Sauté steak strips; warm rice and beans; layer steak, rice, beans, cheese, and mayo on tortilla; roll up."],
            ["Breakfast Egg Sandwich", "15 min", 
             "Eggs, cheese, turkey sausage patties, sourdough bread, mayo", 
             "Scramble eggs with cheese; heat sausage patties; toast sourdough with mayo; assemble sandwich."],
            ["Homemade McChicken", "20 min", 
             "Chicken patties, burger buns, mayo", 
             "Cook chicken patties; toast buns with a bit of mayo; place patty between buns."],
            ["Chicken Caesar Wrap", "15 min", 
             "Pre-cooked chicken, tortilla, shredded cheese, Caesar dressing", 
             "Layer sliced chicken, cheese, and Caesar dressing in tortilla; roll tightly."],
            ["Turkey and Cheese Sandwich", "10 min", 
             "Sliced turkey, cheese, toasted sourdough or bagel, mayo", 
             "Layer turkey and cheese on toasted bread/bagel with mayo."],
            ["Grilled Cheese Sandwich", "10 min", 
             "Bread, butter, sliced cheese", 
             "Butter bread on outside, add cheese in between; grill until golden."],
            ["Quesadilla", "15 min", 
             "Tortilla, cheese, pre-cooked chicken or turkey", 
             "Fill tortilla with cheese and meat; cook in pan until tortilla is crispy and cheese melts."],
            ["Mac and Cheese with Bacon", "15 min", 
             "Boxed mac and cheese, bacon bits", 
             "Prepare mac and cheese per box directions; stir in cooked bacon bits."],
            ["Instant Ramen with Egg", "10 min", 
             "Instant ramen, egg, water", 
             "Cook ramen as directed; add a boiled or poached egg before serving."],
            ["Bagel with Cream Cheese and Bacon", "10 min", 
             "Bagel, cream cheese, bacon", 
             "Toast bagel; spread cream cheese; add cooked bacon."],
            ["Spaghetti with Meat Sauce", "25 min", 
             "Spaghetti, ground beef, non-chunky tomato sauce, parmesan", 
             "Cook spaghetti; brown ground beef; mix with tomato sauce; serve over pasta with parmesan."],
            ["Chicken Alfredo", "20 min", 
             "Pasta, store-bought Alfredo sauce, pre-cooked chicken", 
             "Cook pasta; heat Alfredo sauce and chicken together; combine with pasta."],
            ["Pulled Pork with BBQ", "25 min", 
             "Pre-cooked pulled pork, BBQ sauce, instant mashed potatoes or rice", 
             "Heat pulled pork with BBQ sauce; serve with instant mashed potatoes or rice."],
            ["Shrimp Scampi", "15 min", 
             "Pre-cooked shrimp, pasta, garlic, butter, olive oil, parsley", 
             "Cook pasta; sauté garlic in butter and olive oil; add shrimp; toss with pasta and parsley."],
            ["Philly Cheesesteak Sliders", "25 min", 
             "Thinly sliced steak, slider buns, cheese, onions", 
             "Sauté steak and onions; place mixture and cheese on slider buns; heat until cheese melts."],
            ["Chicken Tenders and Fries", "25 min", 
             "Pre-breaded chicken tenders, frozen fries", 
             "Bake chicken tenders and fries as per package instructions; serve together."],
            ["Beef Tacos", "20 min", 
             "Ground beef, taco seasoning, taco shells, cheese", 
             "Cook beef with taco seasoning; fill taco shells with beef and top with cheese."],
            ["Stir-Fry with Pre-Cooked Chicken", "20 min", 
             "Pre-cooked chicken strips, frozen mixed vegetables, soy sauce, microwaveable rice", 
             "Stir-fry chicken and vegetables with soy sauce; serve over heated rice."],
            ["Pasta with Pesto", "15 min", 
             "Pasta, store-bought pesto, parmesan cheese", 
             "Cook pasta; toss with pesto and sprinkle parmesan on top."],
            ["Sloppy Joes", "20 min", 
             "Ground beef, sloppy joe sauce, hamburger buns", 
             "Brown ground beef; mix with sloppy joe sauce; spoon onto hamburger buns."]
        ]
    
        # Hardcoded meal ideas list
        self.meal_ideas = [
            (0, 'Garlic Salmon Pasta', '30 minutes', 'salmon, spaghetti, garlic, olive oil, parmesan cheese', 
             '1. Cook spaghetti according to package instructions. \n2. In a pan, heat olive oil and garlic, then add salmon and cook until done. \n3. Combine cooked pasta with salmon, garlic, and olive oil. \n4. Serve with grated parmesan cheese on top.'),
            (1, 'Bacon Egg Sourdough Toast', '20 minutes', 'sourdough bread, eggs, bacon, shredded cheese, butter',
             '1. Cook bacon until crispy, then scramble eggs. \n2. Toast sourdough bread slices. \n3. Assemble by placing scrambled eggs and bacon on top of the toast. \n4. Sprinkle shredded cheese and melt under broiler. \n5. Serve hot with a side of butter.'),
            (2, 'Sesame Ginger Chicken Wrap', '25 minutes', 'rotisserie chicken, tortilla, garlic, ginger, sesame seeds, soy sauce, shredded cheese',
             '1. Shred rotisserie chicken and mix with garlic, ginger, sesame seeds, and soy sauce. \n2. Warm tortilla and fill with the chicken mixture. \n3. Sprinkle shredded cheese on top. \n4. Roll up the wrap and enjoy.'),
            (3, 'Cheesy Chicken Tortilla Bake', '40 minutes', 'pre-cooked chicken, tortilla, non-chunky tomato sauce, shredded cheese, onions',
             '1. Preheat oven to 350°F. \n2. Layer tortillas, chicken, tomato sauce, onions, and shredded cheese in a baking dish. \n3. Repeat layers and top with more cheese. \n4. Bake for 25-30 minutes until cheese is melted and bubbly. \n5. Serve hot.'),
            (4, 'Bacon Egg Fried Rice', '25 minutes', 'Bacon, Eggs, White rice, Onion, Garlic, Frozen mixed vegetables, Soy sauce, Olive oil',
             '1. Cook bacon until crispy, then set aside. \n2. In the same pan, sauté onions and garlic. \n3. Add cooked white rice and frozen mixed vegetables. \n4. Push rice to the side, scramble eggs, and mix in. \n5. Crumble bacon and add to the rice. \n6. Season with soy sauce and serve hot.'),
            (5, 'Chicken Tomato Garlic Pasta', '30 minutes', 'Rotisserie chicken, Spaghetti, Non-chunky tomato sauce, Garlic, Olive oil, Parmesan cheese',
             '1. Cook spaghetti according to package instructions. \n2. In a pan, heat olive oil and garlic, then add shredded rotisserie chicken. \n3. Pour in tomato sauce and simmer. \n4. Toss cooked pasta in the sauce. \n5. Serve with grated parmesan cheese on top.'),
            (6, 'Ginger Soy Salmon Stir-Fry', '25 minutes', 'Salmon, Frozen mixed vegetables, Onion, Garlic, Ginger, Soy sauce, Microwaveable rice',
             '1. In a pan, stir-fry salmon, vegetables, onion, garlic, and ginger. \n2. Add soy sauce and cook until salmon is done. \n3. Microwave rice according to package instructions. \n4. Serve stir-fry over rice.'),
            (7, 'Steak Cheddar Sourdough Melt', '35 minutes', 'Thin-sliced steak, Sourdough bread, Shredded cheese, Onion, Butter, Mayo',
             '1. Cook steak slices in a pan until desired doneness. \n2. Butter sourdough bread slices and toast. \n3. Spread mayo on one side of the bread. \n4. Layer steak, shredded cheese, and onions on the other side. \n5. Close the sandwich and grill until cheese melts. \n6. Serve hot.'),
            (8, 'Shrimp and Bacon Carbonara', '30 minutes', 'Pre-cooked shrimp, Bacon, Eggs, Spaghetti, Parmesan cheese, Olive oil, Garlic',
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
    
    def clear_individual_table(self, table_name):
        """Clears a single table."""
        success = clear_table(table_name)
        status = "✓" if success else "✗"
        print(f"{status} Cleared {table_name}")
    
    def reset_meals(self):
        """Clears and repopulates the meals table."""
        self.clear_individual_table("meals")
    
        create_table_query = """
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            prep_time TEXT,
            ingredients TEXT,
            recipe TEXT
        )
        """
        run_query(create_table_query, commit=True)
    
        for idx, meal in enumerate(self.meals):
            name, prep_time, ingredients, recipe = meal
            query = """
            INSERT INTO meals (id, name, prep_time, ingredients, recipe) 
            VALUES (%s, %s, %s, %s, %s)
            """
            success = run_query(query, (idx, name, prep_time, ingredients, recipe), commit=True)
            if success:
                print(f"✓ Added: {name}")
            else:
                print(f"✗ Failed to add: {name}")
    
    def reset_taste_profile(self):
        """Clears and resets the taste profile table."""
        self.clear_individual_table("taste_profile")
    
        create_table_query = """
        CREATE TABLE IF NOT EXISTS taste_profile (
            id INTEGER PRIMARY KEY,
            profile TEXT NOT NULL
        )
        """
        run_query(create_table_query, commit=True)
    
        query = """
        INSERT INTO taste_profile (id, profile) 
        VALUES (%s, %s)
        """
        success = run_query(query, (1, self.taste_profile), commit=True)
    
        if success:
            print("✓ Taste profile updated successfully")
        else:
            print("✗ Failed to update taste profile")
    
    def reset_inventory(self):
        """Clears and repopulates the inventory table."""
        self.clear_individual_table("inventory")
    
        create_table_query = """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            expiration DATE
        )
        """
        run_query(create_table_query, commit=True)
    
        default_expiration = datetime.now() + timedelta(days=7)
    
        for idx, item in enumerate(self.inventory_items):
            query = """
            INSERT INTO inventory (id, name, quantity, expiration) 
            VALUES (%s, %s, %s, %s)
            """
            success = run_query(query, (idx, item, 1, default_expiration), commit=True)
    
            if success:
                print(f"✓ Added: {item}")
            else:
                print(f"✗ Failed to add: {item}")
    
    def reset_meal_ideas(self):
        """Clears and repopulates the new_meal_ideas table."""
        self.clear_individual_table("new_meal_ideas")
        clear_query = "DELETE FROM new_meal_ideas"
        run_query(clear_query, commit=True)
    
        insert_query = """
        INSERT INTO new_meal_ideas (id, name, prep_time, ingredients, recipe)
        VALUES (%s, %s, %s, %s, %s)
        """
    
        for meal in self.meal_ideas:
            run_query(insert_query, meal, commit=True)
            print(f"Added meal: {meal[1]}")
    
    def reset_daily_notes(self):
        """Clears and populates the daily_notes table for 2025."""
        self.clear_individual_table("daily_notes")
    
        create_table_query = """
        CREATE TABLE IF NOT EXISTS daily_notes (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            notes TEXT
        );
        """
    
        insert_query = """
        INSERT INTO daily_notes (date)
        SELECT generate_series(
            '2025-01-01'::date,
            '2025-12-31'::date,
            '1 day'::interval
        );
        """
    
        if run_query(create_table_query, commit=True):
            print("✓ Daily notes table created")
            if run_query(insert_query, commit=True):
                print("✓ Daily notes populated for 2025")
            else:
                print("✗ Failed to populate daily notes")
        else:
            print("✗ Failed to create daily notes table")
    
    def reset_all(self):
        """Runs the complete reset process."""
        # Clear remaining tables that may be used by the app
        tables_to_clear = [
            'inventory',
            'taste_profile',
            'meals',
            'new_meal_ideas',
            'meal_ideas_in_stock',
            'saved_meals_in_stock'
        ]
        all_tables = get_all_table_names()
        table_list = list(set(tables_to_clear + all_tables))
        for table in table_list:
            clear_table(table)
    
        print("\nPopulating meals database...")
        self.reset_meals()
    
        self.reset_taste_profile()
    
        print("\nUpdating inventory...")
        self.reset_inventory()
    
        print("\nLoading meal ideas...")
        self.reset_meal_ideas()
    
        print("\nSetting up daily notes...")
        self.reset_daily_notes()
    
        print("\nChecking which meals can be made with inventory...")
        # Check saved meals
        checker = InStockChecker(new=False)
        available_meals = checker.update_available_meals()
        if available_meals:
            print("\nSaved meals that can be made with current inventory:")
            print(f"Meal IDs: {available_meals}")
        else:
            print("\nNo saved meals can be made with the current inventory.")
    
        # Check meal ideas
        checker = InStockChecker(new=True)
        available_ideas = checker.update_available_meals()
        if available_ideas:
            print("\nMeal ideas that can be made with current inventory:")
            print(f"Meal IDs: {available_ideas}")
        else:
            print("\nNo meal ideas can be made with the current inventory.")
    
        print("\nDone!")

if __name__ == "__main__":
    resetdb = ResetDB()
    # To run the complete reset process:
    resetdb.reset_all()
    
    # Alternatively, you can call individual reset functions:
    # resetdb.reset_meals()
    # resetdb.reset_taste_profile()
    # resetdb.reset_inventory()
    # resetdb.reset_meal_ideas()
    # resetdb.reset_daily_notes()