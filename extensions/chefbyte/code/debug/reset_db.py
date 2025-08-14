import sys
import os
import json
from datetime import datetime, timedelta, date
import traceback
from typing import Optional
import shutil # Import the shutil module for file operations

# Add project root to sys.path to allow importing db_functions
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import the database functions
from db.db_functions import Database, Inventory, TasteProfile, SavedMeals
from db.db_functions import NewMealIdeas, SavedMealsInStockIds, NewMealIdeasInStockIds
from db.db_functions import DailyPlanner, ShoppingList, IngredientsFood, init_tables
from db.meal_availability import MealAvailabilityUpdater, update_all_meal_availability

class ResetDB:
    def __init__(self, add_to_shopping_list=False):
        # Initialize database connection ONLY. Table objects will be created on demand.
        # For Postgres, we don't manage a file path; keep attribute for backwards prints
        self.db_path = "(postgres)"
        self.db = Database() # Initialize DB connection
        if not self.db.connect():
            raise ConnectionError("Failed to connect to database in ResetDB init.")
            
        # Initialize table object dictionary, but don't create tables yet
        # Table creation will happen in load methods after potential drops in clear methods
        self.tables = {
            "inventory": Inventory(self.db),
            "taste_profile": TasteProfile(self.db),
            "saved_meals": SavedMeals(self.db),
            "new_meal_ideas": NewMealIdeas(self.db),
            "saved_meals_instock_ids": SavedMealsInStockIds(self.db),
            "new_meal_ideas_instock_ids": NewMealIdeasInStockIds(self.db),
            "daily_planner": DailyPlanner(self.db),
            "shopping_list": ShoppingList(self.db),
            "ingredients_foods": IngredientsFood(self.db)
        }
        
        # Whether to add missing ingredients to shopping list
        self.add_to_shopping_list = add_to_shopping_list
        
        # Define ingredients_foods data FIRST
        self.ingredients_foods = [
            # Existing items with known links
            {"id": 101, "name": "Fairlife chocolate milk", "min_amount": 1, "walmart_link": "https://www.walmart.com/ip/43922523"},
            {"id": 102, "name": "Whole milk", "min_amount": 1, "walmart_link": "https://www.walmart.com/ip/10450114"},
            {"id": 103, "name": "Cream cheese", "min_amount": 1, "walmart_link": "https://www.walmart.com/ip/10295585"},
            # Items corresponding to inventory_items (will be defined later, ensure consistency)
            {"id": 104, "name": "Ground beef", "min_amount": 1, "walmart_link": ""},
            {"id": 105, "name": "Bacon", "min_amount": 1, "walmart_link": ""},
            {"id": 106, "name": "Garlic", "min_amount": 1, "walmart_link": ""},
            {"id": 107, "name": "Ginger", "min_amount": 1, "walmart_link": ""},
            {"id": 108, "name": "Spaghetti", "min_amount": 1, "walmart_link": ""},
            {"id": 109, "name": "Parmesan cheese", "min_amount": 1, "walmart_link": ""},
            {"id": 110, "name": "Butter", "min_amount": 1, "walmart_link": ""},
            {"id": 111, "name": "Olive oil", "min_amount": 1, "walmart_link": ""},
            {"id": 112, "name": "Thin-sliced steak", "min_amount": 1, "walmart_link": ""},
            {"id": 113, "name": "White rice", "min_amount": 1, "walmart_link": ""},
            {"id": 114, "name": "Black beans", "min_amount": 1, "walmart_link": ""},
            {"id": 115, "name": "Tortilla", "min_amount": 1, "walmart_link": ""},
            {"id": 116, "name": "Mayo", "min_amount": 1, "walmart_link": ""},
            {"id": 117, "name": "Eggs", "min_amount": 1, "walmart_link": ""},
            {"id": 118, "name": "Sourdough bread", "min_amount": 1, "walmart_link": ""},
            {"id": 119, "name": "Pre-cooked chicken", "min_amount": 1, "walmart_link": ""},
            {"id": 120, "name": "Shredded cheese", "min_amount": 1, "walmart_link": ""},
            {"id": 121, "name": "Caesar dressing", "min_amount": 1, "walmart_link": ""},
            {"id": 122, "name": "Instant ramen", "min_amount": 1, "walmart_link": ""},
            {"id": 123, "name": "Non-chunky tomato sauce", "min_amount": 1, "walmart_link": ""},
            {"id": 124, "name": "Pre-cooked pulled pork", "min_amount": 1, "walmart_link": ""},
            {"id": 125, "name": "BBQ sauce", "min_amount": 1, "walmart_link": ""},
            {"id": 126, "name": "Instant mashed potatoes", "min_amount": 1, "walmart_link": ""},
            {"id": 127, "name": "Pre-cooked shrimp", "min_amount": 1, "walmart_link": ""},
            {"id": 128, "name": "Onions", "min_amount": 1, "walmart_link": ""},
            {"id": 129, "name": "Taco seasoning", "min_amount": 1, "walmart_link": ""},
            {"id": 130, "name": "Taco shells", "min_amount": 1, "walmart_link": ""},
            {"id": 131, "name": "Frozen mixed vegetables", "min_amount": 1, "walmart_link": ""},
            {"id": 132, "name": "Microwaveable rice", "min_amount": 1, "walmart_link": ""},
            {"id": 133, "name": "Rotisserie chicken", "min_amount": 1, "walmart_link": ""},
            {"id": 134, "name": "Salmon", "min_amount": 1, "walmart_link": ""},
            {"id": 135, "name": "Tortilla chips", "min_amount": 1, "walmart_link": ""},
            {"id": 136, "name": "Sesame seeds", "min_amount": 1, "walmart_link": ""},
            {"id": 137, "name": "Soy sauce", "min_amount": 1, "walmart_link": ""},
            {"id": 138, "name": "Frozen waffles", "min_amount": 1, "walmart_link": ""},
            {"id": 139, "name": "Microwave burrito", "min_amount": 1, "walmart_link": ""},
            {"id": 140, "name": "Carrots", "min_amount": 1, "walmart_link": ""},
            # Extra ingredients needed for meals/ideas (assuming IDs)
            {"id": 141, "name": "Hamburger Bun", "min_amount": 1, "walmart_link": ""},
            {"id": 142, "name": "Extra Sharp Cheddar", "min_amount": 1, "walmart_link": ""},
            {"id": 143, "name": "Cornstarch", "min_amount": 1, "walmart_link": ""},
            {"id": 144, "name": "Pepper", "min_amount": 1, "walmart_link": ""},
            {"id": 145, "name": "Turkey sausage patties", "min_amount": 1, "walmart_link": ""},
            {"id": 146, "name": "Chicken patties", "min_amount": 1, "walmart_link": ""},
            {"id": 147, "name": "Sliced turkey", "min_amount": 1, "walmart_link": ""},
            {"id": 148, "name": "Bread", "min_amount": 1, "walmart_link": ""}, # Generic bread
            {"id": 149, "name": "Sliced cheese", "min_amount": 1, "walmart_link": ""}, # Generic sliced cheese
            {"id": 150, "name": "Boxed mac and cheese", "min_amount": 1, "walmart_link": ""},
            {"id": 151, "name": "Bagel", "min_amount": 1, "walmart_link": ""},
            {"id": 152, "name": "Pasta", "min_amount": 1, "walmart_link": ""}, # Generic pasta
            {"id": 153, "name": "Alfredo sauce", "min_amount": 1, "walmart_link": ""},
            {"id": 154, "name": "Parsley", "min_amount": 1, "walmart_link": ""},
            {"id": 155, "name": "Slider buns", "min_amount": 1, "walmart_link": ""},
            {"id": 156, "name": "Chicken tenders", "min_amount": 1, "walmart_link": ""},
            {"id": 157, "name": "Frozen fries", "min_amount": 1, "walmart_link": ""},
            {"id": 158, "name": "Pesto", "min_amount": 1, "walmart_link": ""},
            {"id": 159, "name": "Sloppy joe sauce", "min_amount": 1, "walmart_link": ""},
            # Make sure all used IDs exist, add any missing ones used in meals/ideas
        ]
        
        # Helper to find food ID (used when defining meals/ideas below)
        # Initialize the lookup dictionary AFTER defining the data it depends on
        self._food_id_lookup = {item['name'].lower(): item['id'] for item in self.ingredients_foods}
        
        # Hardcoded meals list - **Updated ingredient format**
        self.meals = [
            ["Bacon Cheeseburger", 20,
             [
                 [self._get_food_id_by_name("Ground beef"), "Ground beef", "1 patty (4-6 oz)"],
                 [self._get_food_id_by_name("Bacon"), "bacon", "2 strips"],
                 [self._get_food_id_by_name("Hamburger Bun"), "burger bun", "1"],
                 [self._get_food_id_by_name("Extra Sharp Cheddar"), "extra sharp cheddar", "1 slice"],
                 [None, "condiments", "1 tbsp each"]
             ],
             "Form beef patties, cook to desired doneness; fry bacon; assemble patty with bacon and cheese on bun."],
            ["Sesame Chicken", 25,
             [
                 [self._get_food_id_by_name("Pre-cooked chicken"), "Chicken pieces", "6 oz"],
                 [self._get_food_id_by_name("Sesame seeds"), "sesame seeds", "1 tsp"],
                 [self._get_food_id_by_name("Soy sauce"), "soy sauce", "2 tbsp"],
                 [self._get_food_id_by_name("Garlic"), "garlic", "1 clove, minced"],
                 [self._get_food_id_by_name("Ginger"), "ginger", "1/2 tsp, minced"],
                 [self._get_food_id_by_name("Cornstarch"), "cornstarch", "1 tsp"]
             ],
             "Marinate chicken in soy sauce, garlic, and ginger; coat lightly with cornstarch; stir-fry until cooked; sprinkle sesame seeds."],
            ["Magic Spaghetti", 15,
             [
                 [self._get_food_id_by_name("Spaghetti"), "Spaghetti", "1 serving (2 oz dry)"],
                 [self._get_food_id_by_name("Parmesan cheese"), "parmesan cheese", "2 tbsp, grated"],
                 [self._get_food_id_by_name("Butter"), "butter", "1 tbsp"],
                 [self._get_food_id_by_name("Olive oil"), "olive oil", "1 tbsp"],
                 [self._get_food_id_by_name("Pepper"), "pepper", "1/4 tsp"]
             ],
             "Cook spaghetti; toss with butter, olive oil, parmesan, and pepper."],
            ["Steak Burrito", 25,
             [
                 [self._get_food_id_by_name("Thin-sliced steak"), "Thin-sliced steak", "4-6 oz"],
                 [self._get_food_id_by_name("White rice"), "white rice", "1/2 cup, cooked"],
                 [self._get_food_id_by_name("Black beans"), "black beans", "1/4 cup"],
                 [self._get_food_id_by_name("Tortilla"), "tortilla", "1 large"],
                 [self._get_food_id_by_name("Shredded cheese"), "extra cheese", "1/4 cup"],
                 [self._get_food_id_by_name("Mayo"), "mayo", "1 tbsp"]
             ],
             "Sauté steak strips; warm rice and beans; layer steak, rice, beans, cheese, and mayo on tortilla; roll up."],
            ["Breakfast Egg Sandwich", 15,
             [
                 [self._get_food_id_by_name("Eggs"), "Eggs", "1-2"],
                 [self._get_food_id_by_name("Shredded cheese"), "cheese", "1 slice or 2 tbsp"],
                 [self._get_food_id_by_name("Turkey sausage patties"), "turkey sausage patties", "1-2"],
                 [self._get_food_id_by_name("Sourdough bread"), "sourdough bread", "2 slices"],
                 [self._get_food_id_by_name("Mayo"), "mayo", "1 tsp"]
             ],
             "Scramble eggs with cheese; heat sausage patties; toast sourdough with mayo; assemble sandwich."],
            ["Homemade McChicken", 20,
             [
                 [self._get_food_id_by_name("Chicken patties"), "Chicken patties", "1"],
                 [self._get_food_id_by_name("Hamburger Bun"), "burger buns", "1"],
                 [self._get_food_id_by_name("Mayo"), "mayo", "1 tbsp"]
             ],
             "Cook chicken patties; toast buns with a bit of mayo; place patty between buns."],
            ["Chicken Caesar Wrap", 15,
             [
                 [self._get_food_id_by_name("Pre-cooked chicken"), "Pre-cooked chicken", "3-4 oz, sliced"],
                 [self._get_food_id_by_name("Tortilla"), "tortilla", "1 large"],
                 [self._get_food_id_by_name("Shredded cheese"), "shredded cheese", "1/4 cup"],
                 [self._get_food_id_by_name("Caesar dressing"), "Caesar dressing", "2 tbsp"]
             ],
             "Layer sliced chicken, cheese, and Caesar dressing in tortilla; roll tightly."],
            ["Turkey and Cheese Sandwich", 10,
             [
                 [self._get_food_id_by_name("Sliced turkey"), "Sliced turkey", "3-4 slices"],
                 [self._get_food_id_by_name("Shredded cheese"), "cheese", "1-2 slices or 1/4 cup"], # Allow shredded or sliced
                 [self._get_food_id_by_name("Sourdough bread"), "toasted sourdough or bagel", "2 slices / 1 bagel"], # Map bagel to sourdough
                 [self._get_food_id_by_name("Mayo"), "mayo", "1 tbsp"]
             ],
             "Layer turkey and cheese on toasted bread/bagel with mayo."],
            ["Grilled Cheese Sandwich", 10,
             [
                 [self._get_food_id_by_name("Bread"), "Bread", "2 slices"], # Assumes generic Bread ID exists
                 [self._get_food_id_by_name("Butter"), "butter", "1 tbsp"],
                 [self._get_food_id_by_name("Sliced cheese"), "sliced cheese", "2 slices"] # Assumes ID exists
             ],
             "Butter bread on outside, add cheese in between; grill until golden."],
            ["Quesadilla", 15,
             [
                 [self._get_food_id_by_name("Tortilla"), "Tortilla", "1 large"],
                 [self._get_food_id_by_name("Shredded cheese"), "cheese", "1/2 cup"],
                 [self._get_food_id_by_name("Pre-cooked chicken"), "pre-cooked chicken or turkey", "3 oz"] # Map turkey to chicken
             ],
             "Fill tortilla with cheese and meat; cook in pan until tortilla is crispy and cheese melts."],
            ["Mac and Cheese with Bacon", 15,
             [
                 [self._get_food_id_by_name("Boxed mac and cheese"), "Boxed mac and cheese", "1 box (prepared)"], # Assumes ID exists
                 [self._get_food_id_by_name("Bacon"), "bacon bits", "2 tbsp, cooked & crumbled"] # Map bits to bacon
             ],
             "Prepare mac and cheese per box directions; stir in cooked bacon bits."],
            ["Instant Ramen with Egg", 10,
             [
                 [self._get_food_id_by_name("Instant ramen"), "Instant ramen", "1 package"],
                 [self._get_food_id_by_name("Eggs"), "egg", "1"],
                 [None, "water", "per package"] # No ID for water
             ],
             "Cook ramen as directed; add a boiled or poached egg before serving."],
            ["Bagel with Cream Cheese and Bacon", 10,
             [
                 [self._get_food_id_by_name("Bagel"), "Bagel", "1"], # Assumes ID exists
                 [self._get_food_id_by_name("Cream cheese"), "cream cheese", "2 tbsp"],
                 [self._get_food_id_by_name("Bacon"), "bacon", "2 strips, cooked"]
             ],
             "Toast bagel; spread cream cheese; add cooked bacon."],
            ["Spaghetti with Meat Sauce", 25,
             [
                 [self._get_food_id_by_name("Spaghetti"), "Spaghetti", "1 serving (2 oz dry)"],
                 [self._get_food_id_by_name("Ground beef"), "ground beef", "4 oz"],
                 [self._get_food_id_by_name("Non-chunky tomato sauce"), "non-chunky tomato sauce", "1/2 cup"],
                 [self._get_food_id_by_name("Parmesan cheese"), "parmesan", "1 tbsp, grated"]
             ],
             "Cook spaghetti; brown ground beef; mix with tomato sauce; serve over pasta with parmesan."],
            ["Chicken Alfredo", 20,
             [
                 [self._get_food_id_by_name("Pasta"), "Pasta", "1 serving (2 oz dry)"], # Assumes generic Pasta ID exists
                 [self._get_food_id_by_name("Alfredo sauce"), "store-bought Alfredo sauce", "1/2 cup"], # Assumes ID exists
                 [self._get_food_id_by_name("Pre-cooked chicken"), "pre-cooked chicken", "4 oz"]
             ],
             "Cook pasta; heat Alfredo sauce and chicken together; combine with pasta."],
            ["Pulled Pork with BBQ", 25,
             [
                 [self._get_food_id_by_name("Pre-cooked pulled pork"), "Pre-cooked pulled pork", "6 oz"],
                 [self._get_food_id_by_name("BBQ sauce"), "BBQ sauce", "1/4 cup"],
                 [self._get_food_id_by_name("Instant mashed potatoes"), "instant mashed potatoes or rice", "1 serving"] # Map rice to potatoes
             ],
             "Heat pulled pork with BBQ sauce; serve with instant mashed potatoes or rice."],
            ["Shrimp Scampi", 15,
             [
                 [self._get_food_id_by_name("Pre-cooked shrimp"), "Pre-cooked shrimp", "4 oz"],
                 [self._get_food_id_by_name("Pasta"), "pasta", "1 serving (2 oz dry)"],
                 [self._get_food_id_by_name("Garlic"), "garlic", "1 clove, minced"],
                 [self._get_food_id_by_name("Butter"), "butter", "1 tbsp"],
                 [self._get_food_id_by_name("Olive oil"), "olive oil", "1 tbsp"],
                 [self._get_food_id_by_name("Parsley"), "parsley", "1 tsp, chopped"] # Assumes ID exists
             ],
             "Cook pasta; sauté garlic in butter and olive oil; add shrimp; toss with pasta and parsley."],
            ["Philly Cheesesteak Sliders", 25,
             [
                 [self._get_food_id_by_name("Thin-sliced steak"), "Thinly sliced steak", "6 oz"], # Corrected typo here
                 [self._get_food_id_by_name("Slider buns"), "slider buns", "3"], # Assumes ID exists
                 [self._get_food_id_by_name("Shredded cheese"), "cheese", "1/2 cup"],
                 [self._get_food_id_by_name("Onions"), "onions", "1/4 cup, sliced"]
             ],
             "Sauté steak and onions; place mixture and cheese on slider buns; heat until cheese melts."],
            ["Chicken Tenders and Fries", 25,
             [
                 [self._get_food_id_by_name("Chicken tenders"), "Pre-breaded chicken tenders", "3-4"], # Assumes ID exists
                 [self._get_food_id_by_name("Frozen fries"), "frozen fries", "1 serving"] # Assumes ID exists
             ],
             "Bake chicken tenders and fries as per package instructions; serve together."],
            ["Beef Tacos", 20,
             [
                 [self._get_food_id_by_name("Ground beef"), "Ground beef", "4 oz"],
                 [self._get_food_id_by_name("Taco seasoning"), "taco seasoning", "1 tbsp"],
                 [self._get_food_id_by_name("Taco shells"), "taco shells", "2-3"],
                 [self._get_food_id_by_name("Shredded cheese"), "cheese", "1/4 cup"]
             ],
             "Cook beef with taco seasoning; fill taco shells with beef and top with cheese."],
            ["Stir-Fry with Pre-Cooked Chicken", 20,
             [
                 [self._get_food_id_by_name("Pre-cooked chicken"), "Pre-cooked chicken strips", "4 oz"],
                 [self._get_food_id_by_name("Frozen mixed vegetables"), "frozen mixed vegetables", "1 cup"],
                 [self._get_food_id_by_name("Soy sauce"), "soy sauce", "2 tbsp"],
                 [self._get_food_id_by_name("Microwaveable rice"), "microwaveable rice", "1 serving"]
             ],
             "Stir-fry chicken and vegetables with soy sauce; serve over heated rice."],
            ["Pasta with Pesto", 15,
             [
                 [self._get_food_id_by_name("Pasta"), "Pasta", "1 serving (2 oz dry)"],
                 [self._get_food_id_by_name("Pesto"), "store-bought pesto", "1/4 cup"], # Assumes ID exists
                 [self._get_food_id_by_name("Parmesan cheese"), "parmesan cheese", "1 tbsp, grated"]
             ],
             "Cook pasta; toss with pesto and sprinkle parmesan on top."],
            ["Sloppy Joes", 20,
             [
                 [self._get_food_id_by_name("Ground beef"), "Ground beef", "4 oz"],
                 [self._get_food_id_by_name("Sloppy joe sauce"), "sloppy joe sauce", "1/4 cup"], # Assumes ID exists
                 [self._get_food_id_by_name("Hamburger buns"), "hamburger buns", "1"] # Corrected ID lookup here
             ],
             "Brown ground beef; mix with sloppy joe sauce; spoon onto hamburger buns."]
        ]
        
        # Hardcoded meal ideas list - **Updated ingredient format**
        self.meal_ideas = [
            ('Garlic Salmon Pasta', 30,
             [
                 [self._get_food_id_by_name("Salmon"), "salmon", "1 fillet (4-6 oz)"],
                 [self._get_food_id_by_name("Spaghetti"), "spaghetti", "1 serving (2 oz dry)"],
                 [self._get_food_id_by_name("Garlic"), "garlic", "2 cloves, minced"],
                 [self._get_food_id_by_name("Olive oil"), "olive oil", "2 tbsp"],
                 [self._get_food_id_by_name("Parmesan cheese"), "parmesan cheese", "2 tbsp, grated"]
             ],
             '1. Cook spaghetti according to package instructions. \n2. In a pan, heat olive oil and garlic, then add salmon and cook until done. \n3. Combine cooked pasta with salmon, garlic, and olive oil. \n4. Serve with grated parmesan cheese on top.'),
            ('Bacon Egg Sourdough Toast', 20,
             [
                 [self._get_food_id_by_name("Sourdough bread"), "sourdough bread", "2 slices"],
                 [self._get_food_id_by_name("Eggs"), "eggs", "2"],
                 [self._get_food_id_by_name("Bacon"), "bacon", "2 strips, cooked"],
                 [self._get_food_id_by_name("Shredded cheese"), "shredded cheese", "1/4 cup"],
                 [self._get_food_id_by_name("Butter"), "butter", "1 tbsp"]
             ],
             '1. Cook bacon until crispy, then scramble eggs. \n2. Toast sourdough bread slices. \n3. Assemble by placing scrambled eggs and bacon on top of the toast. \n4. Sprinkle shredded cheese and melt under broiler. \n5. Serve hot with a side of butter.'),
            ('Sesame Ginger Chicken Wrap', 25,
             [
                 [self._get_food_id_by_name("Rotisserie chicken"), "rotisserie chicken", "4 oz, shredded"],
                 [self._get_food_id_by_name("Tortilla"), "tortilla", "1 large"],
                 [self._get_food_id_by_name("Garlic"), "garlic", "1 clove, minced"],
                 [self._get_food_id_by_name("Ginger"), "ginger", "1/2 tsp, minced"],
                 [self._get_food_id_by_name("Sesame seeds"), "sesame seeds", "1 tsp"],
                 [self._get_food_id_by_name("Soy sauce"), "soy sauce", "1 tbsp"],
                 [self._get_food_id_by_name("Shredded cheese"), "shredded cheese", "1/4 cup"]
             ],
             '1. Shred rotisserie chicken and mix with garlic, ginger, sesame seeds, and soy sauce. \n2. Warm tortilla and fill with the chicken mixture. \n3. Sprinkle shredded cheese on top. \n4. Roll up the wrap and enjoy.'),
            ('Cheesy Chicken Tortilla Bake', 40,
             [
                 [self._get_food_id_by_name("Pre-cooked chicken"), "pre-cooked chicken", "6 oz, chopped"],
                 [self._get_food_id_by_name("Tortilla"), "tortilla", "3-4 small"],
                 [self._get_food_id_by_name("Non-chunky tomato sauce"), "non-chunky tomato sauce", "1 cup"],
                 [self._get_food_id_by_name("Shredded cheese"), "shredded cheese", "1 cup"],
                 [self._get_food_id_by_name("Onions"), "onions", "1/4 cup, chopped"]
             ],
             '1. Preheat oven to 350°F. \n2. Layer tortillas, chicken, tomato sauce, onions, and shredded cheese in a baking dish. \n3. Repeat layers and top with more cheese. \n4. Bake for 25-30 minutes until cheese is melted and bubbly. \n5. Serve hot.'),
            ('Bacon Egg Fried Rice', 25,
             [
                 [self._get_food_id_by_name("Bacon"), "Bacon", "2 strips, chopped"],
                 [self._get_food_id_by_name("Eggs"), "Eggs", "1-2"],
                 [self._get_food_id_by_name("White rice"), "White rice", "1 cup, cooked & cooled"],
                 [self._get_food_id_by_name("Onions"), "Onion", "1/4 cup, chopped"],
                 [self._get_food_id_by_name("Garlic"), "Garlic", "1 clove, minced"],
                 [self._get_food_id_by_name("Frozen mixed vegetables"), "Frozen mixed vegetables", "1/2 cup"],
                 [self._get_food_id_by_name("Soy sauce"), "Soy sauce", "1-2 tbsp"],
                 [self._get_food_id_by_name("Olive oil"), "Olive oil", "1 tbsp"]
             ],
             '1. Cook bacon until crispy, then set aside. \n2. In the same pan, sauté onions and garlic. \n3. Add cooked white rice and frozen mixed vegetables. \n4. Push rice to the side, scramble eggs, and mix in. \n5. Crumble bacon and add to the rice. \n6. Season with soy sauce and serve hot.'),
            ('Chicken Tomato Garlic Pasta', 30,
             [
                 [self._get_food_id_by_name("Rotisserie chicken"), "Rotisserie chicken", "4 oz, shredded"],
                 [self._get_food_id_by_name("Spaghetti"), "Spaghetti", "1 serving (2 oz dry)"],
                 [self._get_food_id_by_name("Non-chunky tomato sauce"), "Non-chunky tomato sauce", "1/2 cup"],
                 [self._get_food_id_by_name("Garlic"), "Garlic", "2 cloves, minced"],
                 [self._get_food_id_by_name("Olive oil"), "Olive oil", "1 tbsp"],
                 [self._get_food_id_by_name("Parmesan cheese"), "Parmesan cheese", "2 tbsp, grated"]
             ],
             '1. Cook spaghetti according to package instructions. \n2. In a pan, heat olive oil and garlic, then add shredded rotisserie chicken. \n3. Pour in tomato sauce and simmer. \n4. Toss cooked pasta in the sauce. \n5. Serve with grated parmesan cheese on top.'),
            ('Ginger Soy Salmon Stir-Fry', 25,
             [
                 [self._get_food_id_by_name("Salmon"), "Salmon", "1 fillet (4-6 oz)"],
                 [self._get_food_id_by_name("Frozen mixed vegetables"), "Frozen mixed vegetables", "1 cup"],
                 [self._get_food_id_by_name("Onions"), "Onion", "1/4 cup, chopped"],
                 [self._get_food_id_by_name("Garlic"), "Garlic", "1 clove, minced"],
                 [self._get_food_id_by_name("Ginger"), "Ginger", "1/2 tsp, minced"],
                 [self._get_food_id_by_name("Soy sauce"), "Soy sauce", "2 tbsp"],
                 [self._get_food_id_by_name("Microwaveable rice"), "Microwaveable rice", "1 serving"]
             ],
             '1. In a pan, stir-fry salmon, vegetables, onion, garlic, and ginger. \n2. Add soy sauce and cook until salmon is done. \n3. Microwave rice according to package instructions. \n4. Serve stir-fry over rice.'),
            ('Steak Cheddar Sourdough Melt', 35,
             [
                 [self._get_food_id_by_name("Thin-sliced steak"), "Thin-sliced steak", "4-6 oz"],
                 [self._get_food_id_by_name("Sourdough bread"), "Sourdough bread", "2 slices"],
                 [self._get_food_id_by_name("Shredded cheese"), "Shredded cheese", "1/4 cup"], # Changed from cheddar
                 [self._get_food_id_by_name("Onions"), "Onion", "1/4 cup, sliced"],
                 [self._get_food_id_by_name("Butter"), "Butter", "1 tbsp"],
                 [self._get_food_id_by_name("Mayo"), "Mayo", "1 tbsp"]
             ],
             '1. Cook steak slices in a pan until desired doneness. \n2. Butter sourdough bread slices and toast. \n3. Spread mayo on one side of the bread. \n4. Layer steak, shredded cheese, and onions on the other side. \n5. Close the sandwich and grill until cheese melts. \n6. Serve hot.'),
            ('Shrimp and Bacon Carbonara', 30,
             [
                 [self._get_food_id_by_name("Pre-cooked shrimp"), "Pre-cooked shrimp", "4 oz"],
                 [self._get_food_id_by_name("Bacon"), "Bacon", "2 strips, chopped"],
                 [self._get_food_id_by_name("Eggs"), "Eggs", "1 yolk + 1 whole"],
                 [self._get_food_id_by_name("Spaghetti"), "Spaghetti", "1 serving (2 oz dry)"],
                 [self._get_food_id_by_name("Parmesan cheese"), "Parmesan cheese", "1/4 cup, grated"],
                 [self._get_food_id_by_name("Olive oil"), "Olive oil", "1 tbsp"],
                 [self._get_food_id_by_name("Garlic"), "Garlic", "1 clove, minced"]
             ],
             '1. Cook bacon until crispy, then set aside. \n2. In the same pan, sauté garlic and shrimp. \n3. Cook spaghetti according to package instructions. \n4. Whisk eggs and parmesan cheese in a bowl. \n5. Drain pasta and toss with egg mixture. \n6. Add shrimp and crumbled bacon. \n7. Serve hot.')
        ]
    
        # Default inventory items (uses IDs from ingredients_foods defined above)
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
        
        # Define sample inventory data in the new format: [ingredient_food_id, name, quantity, expiration]
        self.sample_inventory_data = [
            [104, "Ground beef", "1 lb", None],
            [105, "Bacon", "12 oz", None],
            [136, "Sesame seeds", "1 tbsp", None],
            [137, "Soy sauce", "1/4 cup", None],
            [106, "Garlic", "3 cloves", None],
            [107, "Ginger", "1 inch piece", None],
            [108, "Spaghetti", "1 box", None],
            [109, "Parmesan cheese", "1 wedge", None],
            [110, "Butter", "1 stick", None],
            [111, "Olive oil", "500ml bottle", None],
            [112, "Thin-sliced steak", "1 lb", None],
            [113, "White rice", "2 cups", None],
            [114, "Black beans", "1 can", None],
            [115, "Tortilla", "1 pack (10 ct)", None],
            [116, "Mayo", "1 jar", None],
            [117, "Eggs", "1 dozen", None],
            [118, "Sourdough bread", "1 loaf", None],
            [119, "Pre-cooked chicken", "1 lb", None],
            [120, "Shredded cheese", "1 bag", None],
            [121, "Caesar dressing", "1 bottle", None],
            [122, "Instant ramen", "3 packs", None],
            [123, "Non-chunky tomato sauce", "1 jar", None],
            [124, "Pre-cooked pulled pork", "1 container", None],
            [125, "BBQ sauce", "1 bottle", None],
            [126, "Instant mashed potatoes", "1 box", None],
            [127, "Pre-cooked shrimp", "1 lb", None],
            [128, "Onions", "2", None],
            [129, "Taco seasoning", "1 packet", None],
            [130, "Taco shells", "1 box", None],
            [131, "Frozen mixed vegetables", "1 bag", None],
            [132, "Microwaveable rice", "1 pouch", None],
            [133, "Rotisserie chicken", "1 whole", None],
            [134, "Salmon", "1 fillet", None],
            [135, "Tortilla chips", "1 bag", None],
            [102, "Whole milk", "1 gallon", None],
            [138, "Frozen waffles", "1 box", None],
            [139, "Microwave burrito", "2", None],
            [140, "Carrots", "1 bag", None]
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
    
    def _get_food_id_by_name(self, name: str) -> Optional[int]:
        """Helper to find the hardcoded food ID based on name."""
        # Simple case-insensitive lookup in the pre-built dictionary
        return self._food_id_lookup.get(name.lower())
    
    # --- CLEAR FUNCTIONS ---
    
    def clear_saved_meals(self):
        """Clears the saved_meals table."""
        print("\nClearing saved meals...")
        
        # Create the table
        self.tables["saved_meals"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['saved_meals'].table_name}")
        
        print("[OK] Saved meals cleared")
    
    def clear_taste_profile(self):
        """Clears the taste profile table."""
        print("\nClearing taste profile...")
        
        # Create the table
        self.tables["taste_profile"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['taste_profile'].table_name}")
        
        print("[OK] Taste profile cleared")
    
    def clear_inventory(self):
        """Clears the inventory table by dropping and recreating it."""
        print("\nClearing inventory (dropping table)...")
        
        # Drop the table first to ensure schema changes are applied
        try:
            self.db.execute_query(f"DROP TABLE IF EXISTS {self.tables['inventory'].table_name}")
            print(f"  Dropped table: {self.tables['inventory'].table_name}")
        except Exception as e:
            print(f"  [WARN] Failed to drop inventory table (may not exist yet): {e}")
            
        # Create the table with the potentially updated schema
        self.tables["inventory"].create_table()
        
        # Delete existing data if any (redundant if dropped, but safe)
        # self.db.execute_query(f"DELETE FROM {self.tables['inventory'].table_name}")
        
        print("[OK] Inventory table recreated")
    
    def clear_new_meal_ideas(self):
        """Clears the new_meal_ideas table."""
        print("\nClearing new meal ideas...")
        
        # Create the table
        self.tables["new_meal_ideas"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['new_meal_ideas'].table_name}")
        
        # Get the correct sequence name before resetting
        sequence_result = self.db.execute_query(
            "SELECT pg_get_serial_sequence('new_meal_ideas', 'id') AS seq",
            fetch=True
        )
        
        if sequence_result and sequence_result[0].get('seq'):
            sequence_name = sequence_result[0]['seq']
            self.db.execute_query(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1")
            print(f"Reset ID sequence: {sequence_name}")
        else:
            print("Warning: Could not find sequence for id column")
            
        print("[OK] New meal ideas cleared")
    
    def clear_daily_planner(self):
        """Clears the daily_planner table."""
        print("\nClearing daily planner...")
        
        # Create the table
        self.tables["daily_planner"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['daily_planner'].table_name}")
        
        print("[OK] Daily planner cleared")
    
    def clear_shopping_list(self):
        """Clears the shopping_list table."""
        print("\nClearing shopping list...")
        
        # Create the table
        self.tables["shopping_list"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['shopping_list'].table_name}")
        
        print("[OK] Shopping list cleared")
    
    def clear_ingredients_foods(self):
        """Clears the ingredients_foods table by dropping and recreating it."""
        print("\nClearing ingredients foods (dropping table)...")

        # Drop the table first
        try:
            self.db.execute_query(f"DROP TABLE IF EXISTS {self.tables['ingredients_foods'].table_name}")
            print(f"  Dropped table: {self.tables['ingredients_foods'].table_name}")
        except Exception as e:
             print(f"  [WARN] Failed to drop ingredients_foods table (may not exist yet): {e}")
        
        # Create the table
        self.tables["ingredients_foods"].create_table()
        
        # Delete existing data if any (redundant)
        # self.db.execute_query(f"DELETE FROM {self.tables['ingredients_foods'].table_name}")
        
        print("[OK] Ingredients foods table recreated")
    
    def clear_saved_meals_instock_ids(self):
        """Clears the saved_meals_instock_ids table."""
        print("\nClearing saved meals in stock IDs...")
        
        # Create the table
        self.tables["saved_meals_instock_ids"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['saved_meals_instock_ids'].table_name}")
        
        print("[OK] Saved meals in stock IDs cleared")
    
    def clear_new_meal_ideas_instock_ids(self):
        """Clears the new_meal_ideas_instock_ids table."""
        print("\nClearing new meal ideas in stock IDs...")
        
        # Create the table
        self.tables["new_meal_ideas_instock_ids"].create_table()
        
        # Delete existing data if any
        self.db.execute_query(f"DELETE FROM {self.tables['new_meal_ideas_instock_ids'].table_name}")
        
        print("[OK] New meal ideas in stock IDs cleared")

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
                print(f"[OK] Added: {name}")
            else:
                print(f"[FAIL] Failed to add: {name}")
    
    def load_taste_profile(self):
        """Loads sample data into the taste profile table."""
        print("\nLoading taste profile...")
        
        # Insert sample data
        success = self.tables["taste_profile"].create(self.taste_profile)
        
        if success is not None:
            print("[OK] Taste profile updated successfully")
        else:
            print("[FAIL] Failed to update taste profile")
    
    def load_inventory(self):
        """Loads sample data into the inventory table from self.sample_inventory_data."""
        print("\nLoading inventory...")
        
        # Ensure table exists with the correct schema *before* loading
        print("  Ensuring inventory table exists...")
        self.tables["inventory"].create_table()
        
        # Set default expiration date (used if expiration in sample data is None)
        default_expiration = datetime.now() + timedelta(days=7)
        
        # Insert sample data using the new list format
        for item_data in self.sample_inventory_data:
            if len(item_data) != 4:
                print(f"[WARN] Skipping invalid sample inventory data: {item_data}")
                continue
            
            food_id, name, quantity, expiration = item_data
            # Use default expiration if None is provided in the sample data
            effective_expiration = expiration if expiration else default_expiration
            
            item_id = self.tables["inventory"].create(
                name=name, 
                quantity=quantity,
                expiration=effective_expiration, 
                ingredient_food_id=food_id # Use the ID from the sample data
            )
            
            if item_id is not None:
                print(f"[OK] Added: {name} (Qty: {quantity}, FoodID: {food_id})")
            else:
                print(f"[FAIL] Failed to add: {name}")
    
    def load_new_meal_ideas(self):
        """Loads sample data into the new_meal_ideas table."""
        print("\nLoading new meal ideas...")
        
        # Insert sample data
        for meal in self.meal_ideas:
            name, prep_time, ingredients, recipe = meal
            new_id = self.tables["new_meal_ideas"].create(name, prep_time, ingredients, recipe)
            
            if new_id is not None:
                print(f"[OK] Added meal idea: {name} with id {new_id}")
            else:
                print(f"[FAIL] Failed to add meal idea: {name}")
    
    def load_daily_planner(self):
        """Initializes the daily_planner table and adds sample meals for today and tomorrow."""
        print("\nLoading daily planner...")

        # Simply ensure the table exists. Days will be created on demand.
        self.tables["daily_planner"].create_table()

        # Calculate dates
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Define meal plans
        meal_plans = [
            {
                "day": today,
                "meal_ids": [3, 1],  # Magic Spaghetti (lunch), Bacon Cheeseburger (dinner)
                "notes": "Lunch: Magic Spaghetti, Dinner: Bacon Cheeseburger"
            },
            {
                "day": tomorrow,
                "meal_ids": [5, 2],  # Breakfast Egg Sandwich (breakfast), Sesame Chicken (dinner)
                "notes": "Breakfast: Egg Sandwich, Dinner: Sesame Chicken"
            }
        ]
        
        # Add the meal plans
        for plan in meal_plans:
            try:
                success = self.tables["daily_planner"].create(
                    day=plan["day"],
                    notes=plan["notes"],
                    meal_ids=plan["meal_ids"]
                )
                
                if success:
                    meal_names = []
                    for meal_id in plan["meal_ids"]:
                        if meal_id == 1:
                            meal_names.append("Bacon Cheeseburger")
                        elif meal_id == 2:
                            meal_names.append("Sesame Chicken")
                        elif meal_id == 3:
                            meal_names.append("Magic Spaghetti")
                        elif meal_id == 5:
                            meal_names.append("Breakfast Egg Sandwich")
                    
                    print(f"[OK] Added meals for {plan['day']}: {', '.join(meal_names)} (IDs: {plan['meal_ids']})")
                else:
                    print(f"[WARN] Failed to add meals for {plan['day']}")
            except Exception as e:
                print(f"[ERROR] Error adding meals for {plan['day']}: {e}")

        print("[OK] Daily planner initialized with sample meal plans")
    
    def load_shopping_list(self):
        """Loads sample items into the shopping_list table."""
        print("\nLoading shopping list...")
        
        # Ensure table exists
        shopping_list_table = self.tables.get("shopping_list")
        if not shopping_list_table:
            print("[FAIL] Shopping list table object not found.")
            return
        shopping_list_table.create_table() # Ensure it exists
        
        # Define items to add [ingredient_food_id, amount]
        # IDs are from self.ingredients_foods
        default_items = [
            [102, 1.0], # Whole milk
            [101, 1.0]  # Fairlife chocolate milk
        ]
        
        added_count = 0
        failed_count = 0
        for item_id, amount in default_items:
            try:
                success = shopping_list_table.create(item_id, amount)
                if success:
                    added_count += 1
                    # Optional: print confirmation for each item
                    # print(f"  [OK] Added item ID {item_id} to shopping list.")
                else:
                    failed_count += 1
                    print(f"  [FAIL] Failed to add item ID {item_id} to shopping list.")
            except Exception as e:
                failed_count += 1
                print(f"  [ERROR] Exception adding item ID {item_id} to shopping list: {e}")
                
        if failed_count == 0:
            print(f"[OK] Shopping list loaded with {added_count} default items.")
        else:
            print(f"[WARN] Shopping list loaded with {added_count} items, but {failed_count} failures occurred.")
    
    def load_ingredients_foods(self):
        """Loads sample data into the ingredients_foods table using direct INSERT with hardcoded IDs."""
        print("\nLoading ingredients foods with hardcoded IDs...")
        
        # Ensure table exists with the correct schema *before* loading
        print("  Ensuring ingredients_foods table exists...")
        self.tables["ingredients_foods"].create_table()
        
        # Use direct INSERT to specify IDs
        insert_query = """
        INSERT INTO ingredients_foods (id, name, min_amount_to_buy, walmart_link)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT(id) DO NOTHING
        """
        
        success_count = 0
        fail_count = 0
        for item in self.ingredients_foods:
            try:
                # Ensure item has 'id'
                if 'id' not in item:
                    print(f"[FAIL] Skipping ingredient - missing 'id': {item.get('name', 'Unknown')}")
                    fail_count += 1
                    continue
                    
                item_name = item["name"]
                item_min_amount = item["min_amount"]
                
                # Item has already been added, so insert it into the ingredients_foods lookup table
                # with its hardcoded ID
                params = (
                    item["id"],
                    item_name,
                    item_min_amount,
                    item.get("walmart_link", "")
                )
                
                try:
                    query = insert_query
                    self.db.execute_query(query, params)
                    success_count += 1
                    print(f"[OK] Added/Checked ingredient: {item_name} (ID: {item['id']})")
                except Exception as e:
                    # If insert fails, try to display details about it
                    failure_count += 1
                    print(f"[ERROR] Failed to add ingredient to ingredients_foods with ID {item['id']}: {e}")
            except Exception as e:
                 print(f"[FAIL] Failed to add ingredient {item.get('name', 'Unknown')} (ID: {item.get('id', '?')}): {e}")
                 fail_count += 1

        print(f"\nFinished loading ingredients foods: {success_count} succeeded, {fail_count} failed.")
    
    def load_saved_meals_instock_ids(self):
        """
        Updates the saved_meals_instock_ids table using meal availability checker.
        Can optionally add missing ingredients to shopping list.
        """
        print("\nUpdating saved meals in stock IDs...")
        
        # Use the meal availability updater
        updater = MealAvailabilityUpdater(self.db)
        available_meals = updater.update_saved_meals_availability(self.add_to_shopping_list)
        
        print(f"[OK] Found {len(available_meals)} saved meals that can be made with current inventory")
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
        
        print(f"[OK] Found {len(available_meal_ideas)} meal ideas that can be made with current inventory")
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
        
        print(f"[OK] Found {len(results['saved_meals'])} saved meals and {len(results['new_meal_ideas'])} meal ideas that can be made with current inventory")
        
        if self.add_to_shopping_list:
            print("  Missing ingredients added to shopping list")
        
        return results
    
    def load_all(self):
        """Loads sample data into all tables."""
        print("Starting complete database load...")
        
        # Load all tables
        # Load ingredients first, as other loads might depend on it for lookups
        self.load_ingredients_foods()
        self.load_saved_meals()
        self.load_new_meal_ideas()
        self.load_taste_profile()
        self.load_inventory()
        self.load_daily_planner()
        self.load_shopping_list()
        
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

    # Snapshot functionality removed per project decision; use reset reload instead

def reset_database():
    """Resets the database by clearing data and reloading sample data (PostgreSQL)."""
    print(f"Attempting to reset data in database: (postgres)")
    db_conn_for_loader = None # Use a different name to avoid confusion
    reset_db_loader = None
    try:
        # We only need to instantiate ResetDB. It handles its own connection
        # and the load_all (via reload_all) will handle clearing first via reload_all.
        print("Initializing ResetDB loader...")
        # Pass add_to_shopping_list=False by default, or make it configurable
        reset_db_loader = ResetDB(add_to_shopping_list=False) 
        db_conn_for_loader = reset_db_loader.db # Get the connection used by the loader
        
        # --- Load Sample Data (which includes clearing first via reload_all) --- 
        print("\nCalling loader to clear and load sample data...")
        reset_db_loader.reload_all() # Use reload_all to ensure clearing happens first
        # ------------------------

        print("\nDatabase reset and sample data loading complete.")
            
    except Exception as e:
        print(f"[ERROR] An error occurred during database reset/load: {e}")
        print(traceback.format_exc())
    finally:
        # Ensure the loader's connection is closed
        if reset_db_loader and reset_db_loader.db and reset_db_loader.db.conn:
            print("Disconnecting loader database connection.")
            reset_db_loader.db.disconnect()

if __name__ == "__main__":
    # Reset and load directly without confirmation
    reset_database()