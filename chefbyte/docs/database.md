# Database Schema

This page lists the PostgreSQL tables used by ChefByte along with their columns and types.

| Table | Columns | Description |
|-------|---------|-------------|
| `inventory` | `id SERIAL PRIMARY KEY`, `name TEXT`, `quantity TEXT`, `expiration TEXT`, `ingredient_food_id INTEGER REFERENCES ingredients_foods(id)` | Pantry items. `ingredient_food_id` links to `ingredients_foods`. |
| `taste_profile` | `profile TEXT PRIMARY KEY` | Single row describing likes, dislikes and dietary notes. |
| `saved_meals` | `id INTEGER PRIMARY KEY`, `name TEXT`, `prep_time_minutes INTEGER`, `ingredients TEXT`, `recipe TEXT` | User-added recipes. `ingredients` is JSON list `[food_id, name, qty]`. |
| `new_meal_ideas` | `id INTEGER PRIMARY KEY`, `name TEXT`, `prep_time INTEGER`, `ingredients TEXT`, `recipe TEXT` | Generated meal ideas not yet saved. |
| `saved_meals_instock_ids` | `id INTEGER PRIMARY KEY` | IDs of saved meals that can be cooked with current inventory. |
| `new_meal_ideas_instock_ids` | `id INTEGER PRIMARY KEY` | IDs of new meal ideas cookable with current inventory. |
| `daily_planner` | `day TEXT PRIMARY KEY`, `notes TEXT`, `meal_ids TEXT` | Planner entries keyed by day. `meal_ids` is JSON list of meal IDs. |
| `shopping_list` | `id INTEGER PRIMARY KEY`, `amount REAL` | Quantities of ingredients to purchase (`id` refers to `ingredients_foods`). |
| `ingredients_foods` | `id SERIAL PRIMARY KEY`, `name TEXT`, `min_amount_to_buy INTEGER`, `walmart_link TEXT` | Reference ingredients with a suggested purchase amount and store link. |

Each tool in the project interacts with these tables via the helper classes in `db/db_functions.py`.
