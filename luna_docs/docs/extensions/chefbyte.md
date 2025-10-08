# ChefByte — User Guide

## Purpose
Nutrition and meal planning powered by Grocy: manage pantry inventory, shopping lists, recipes, and meal plans.

## Prerequisites
- Environment: set `GROCY_API_KEY` (required), `GROCY_BASE_URL` (optional; defaults to `http://192.168.0.185/api`).
- Optional defaults: `GROCY_DEFAULT_LOCATION_ID`, `GROCY_DEFAULT_QU_ID_PURCHASE`, `GROCY_DEFAULT_QU_ID_STOCK`.
- Quantity units (optional): `GROCY_QU_ID_CONTAINER`, `GROCY_QU_ID_SERVING` to pin the ids for the "container" and "serving" units. If not set, the system will auto-resolve by name ("container"/"serving").
- `.env` files are supported.

Unit policy:
- New products default to purchase=container and stock=serving (overridable via explicit `qu_id_*` fields or the above env vars).
- Recipe ingredients accept only the container or serving units (via `unit` label or matching `qu_id`).

## Tools

### `GROCERY_GET_inventory`
- Summary: List current inventory as name, quantity, expiry.
- Example Prompt: Show pantry inventory.
- Example Args: {"base_url": "string(optional override)"}
- Returns: {"items": [{"name": string|null, "quantity": number|null, "expiry": string|null}]}.

### `GROCERY_ACTION_increase_quantity`
- Summary: Increase product stock by `product_id` and `quantity`.
- Example Prompt: Add 2 to product 5.
- Example Args: {"product_id": 5, "quantity": 2}
- Returns: {"status": "ok", "message": string}.

### `GROCERY_ACTION_consume_quantity`
- Summary: Consume product stock by `product_id` and `quantity`.
- Example Prompt: Use 1.5 of product 5.
- Example Args: {"product_id": 5, "quantity": 1.5}
- Returns: {"status": "ok", "message": string}.

### `GROCERY_GET_shopping_list`
- Summary: List shopping list items with resolved product names.
- Example Prompt: Show shopping list.
- Example Args: {"shopping_list_id": 1}
- Returns: {"items": [{"product_id": number|null, "name": string|null, "quantity": number|null}]}.

### `GROCERY_ACTION_shopping_list_add`
- Summary: Add a product to the shopping list.
- Example Prompt: Add 2 of product 5 to my shopping list.
- Example Args: {"product_id": 5, "amount": 2, "shopping_list_id": 1}
- Returns: {"status": "ok", "message": string}.
- Notes: To work by name, first use `GROCERY_ACTION_ensure_product_exists` to get/create the product id.

### `GROCERY_ACTION_shopping_list_remove`
- Summary: Remove an amount of a product from the shopping list.
- Example Prompt: Remove 1 of product 5 from my shopping list.
- Example Args: {"product_id": 5, "amount": 1, "shopping_list_id": 1}
- Returns: {"status": "ok", "message": string}.

### `GROCERY_ACTION_shopping_list_clear`
- Summary: Clear all items from a shopping list.
- Example Prompt: Clear my shopping list.
- Example Args: {"shopping_list_id": 1}
- Returns: {"status": "ok", "message": string}.

### `GROCERY_GET_products`
- Summary: List products as id/name pairs, sorted by id.
- Example Prompt: List my products.
- Example Args: {"base_url": "string(optional)"}
- Returns: {"items": [{"id": number, "name": string}]}.

### `GROCERY_ACTION_create_product`
- Summary: Create a product with sensible defaults.
- Example Prompt: Create a product named "Milk 2%".
- Example Args: {"product_fields": {"name": "Milk 2%"}}
- Returns: {"status": "ok", "message": string, "id": number|null}.
- Notes: Requires `name`. Defaults use `GROCY_DEFAULT_*` env vars when not provided. Quantity units default to container (purchase) and serving (stock); set `GROCY_QU_ID_CONTAINER`/`GROCY_QU_ID_SERVING` or pass explicit `qu_id_purchase`/`qu_id_stock` to override.

### `GROCERY_ACTION_ensure_product_exists`
- Summary: Ensure a product by name exists (create if missing).
- Example Prompt: Ensure product "Milk 2%" exists.
- Example Args: {"name": "Milk 2%", "create_fields": {"location_id": 2}}
- Returns: {"status": "ok", "message": string, "product_id": number, "created": boolean}.

### `GROCERY_GET_meal_plan`
- Summary: List meal plan entries (optionally filter by date range).
- Example Prompt: Show my meal plan for this week.
- Example Args: {"start": "2025-09-22", "end": "2025-09-28"}
- Returns: {"items": [{"id", "day", "recipe_id", "product_id", "servings", "amount", "qu_id", "meal_plan_section_id", "note"}]}.

### `GROCERY_ACTION_add_meal`
- Summary: Add a meal plan entry.
- Example Prompt: Add recipe 12 to 2025-09-25 for 2 servings.
- Example Args: {"fields": {"day": "2025-09-25", "recipe_id": 12, "servings": 2}}
- Returns: {"status": "ok", "message": string}.

### `GROCERY_UPDATE_meal_plan`
- Summary: Update a meal plan entry by id.
- Example Prompt: Update meal entry 45 to 3 servings.
- Example Args: {"entry_id": 45, "fields": {"servings": 3}}
- Returns: {"status": "ok", "message": string}.

### `GROCERY_ACTION_delete_meal`
- Summary: Delete a meal plan entry by id.
- Example Prompt: Delete meal entry 45.
- Example Args: {"entry_id": 45}
- Returns: {"status": "ok", "message": string}.

### `GROCERY_GET_meal_plan_sections`
- Summary: List meal plan sections.
- Example Prompt: Show meal plan sections.
- Example Args: {}
- Returns: {"items": [{"id": number|null, "name": string|null, "sort_number": number|null}]}.

### `GROCERY_GET_cookable_recipes`
- Summary: List recipes you can cook now, with possible servings.
- Example Prompt: What can I cook for 2 servings?
- Example Args: {"desired_servings": 2, "consider_shopping_list": true}
- Returns: {"items": [{"id": number, "name": string|null, "possible_servings": number|null}]}.

### `GROCERY_GET_recipes`
- Summary: List all recipes (id and name).
- Example Prompt: List all recipes.
- Example Args: {}
- Returns: {"items": [{"id": number, "name": string|null}]}.

### `GROCERY_GET_recipe`
- Summary: Get a recipe by id.
- Example Prompt: Get recipe 12.
- Example Args: {"recipe_id": 12}
- Returns: {"id": number, "name": string|null, "base_servings": number|null, "description": string|null}.

### `GROCERY_ACTION_create_recipe`
- Summary: Create a new recipe.
- Example Prompt: Create a recipe named "Greek Salad".
- Example Args: {"fields": {"name": "Greek Salad", "base_servings": 2}}
- Returns: {"status": "ok", "message": string, "id": number|null}.

### `GROCERY_UPDATE_recipe`
- Summary: Update a recipe by id.
- Example Prompt: Rename recipe 12 to "Greek Salad (Easy)".
- Example Args: {"recipe_id": 12, "fields": {"name": "Greek Salad (Easy)"}}
- Returns: {"status": "ok", "message": string}.

### `GROCERY_ACTION_delete_recipe`
- Summary: Delete a recipe by id.
- Example Prompt: Delete recipe 12.
- Example Args: {"recipe_id": 12}
- Returns: {"status": "ok", "message": string}.

### `GROCERY_GET_recipe_ingredients`
- Summary: List ingredients for a recipe.
- Example Prompt: List ingredients for recipe 12.
- Example Args: {"recipe_id": 12}
- Returns: {"items": [{"id": number|null, "recipe_id": number|null, "product_id": number|null, "amount": number|null, "qu_id": number|null, "unit": "container"|"serving"|null, "note": string|null}]}.

### `GROCERY_ACTION_add_recipe_ingredient`
- Summary: Add an ingredient to a recipe (units restricted to container or serving).
- Example Prompt: Add 2 servings of product 5 to recipe 12.
- Example Args: {"fields": {"recipe_id": 12, "product_id": 5, "amount": 2, "unit": "serving"}}
- Returns: {"status": "ok", "message": string, "id": number|null}.
- Notes: You may pass `unit`: "container"|"serving" or a numeric `qu_id` that matches those units. Other units are rejected.

### `GROCERY_UPDATE_recipe_ingredient`
- Summary: Update a recipe ingredient by id (units restricted to container or serving).
- Example Prompt: Update ingredient 77 note to "finely chopped".
- Example Args: {"ingredient_id": 77, "fields": {"note": "finely chopped"}}
- Returns: {"status": "ok", "message": string}.
- Notes: To change the unit, pass `unit`: "container"|"serving" (or a matching `qu_id`).

### `GROCERY_ACTION_delete_recipe_ingredient`
- Summary: Delete a recipe ingredient by id.
- Example Prompt: Delete ingredient 77.
- Example Args: {"ingredient_id": 77}
- Returns: {"status": "ok", "message": string}.
