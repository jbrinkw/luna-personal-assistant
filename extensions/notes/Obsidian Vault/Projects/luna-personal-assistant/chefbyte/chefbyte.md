---
project_root: true
project_id: chefbyte
project_parent: Luna
status: active
---
[[Projects/luna-personal-assistant/chefbyte/Notes|Notes]]

### `app.py`: Orchestrates data flow and handles user input

---

### **Real-time tasks**

- Handle queries unrelated to ChefByte
- Retrieve basic info from the DB
- Perform basic DB updates
- Handle ad hoc meal suggestions

---

### **Async background tasks**

- Generate new meal ideas
- Determine which meals can/can’t be made with current inventory

---

### **Async tasks with message callback**

- Generate multi-day meal plans (notifies user when complete)
- Create shopping list
- Place Walmart order

---

### **Dataflow & Messaging**

`app.py` controls dataflow and message history.

---

### **Router Agents (triggered in order)**

### `pull_router.py`

- Runs right after user input
- Checks if response requires DB data
- Adds data to `response_context`

### `tool_router.py`

- Also runs right after user input
- Routes to tool if needed
    - If **sync** tool → output goes to `response_context`
    - If **async** tool → runs in background, output goes to `message queue`

### `push_router.py`

- Runs after response is generated
- If updates to DB are needed → data pushed to DB

---

### **Response to User**

- Always starts with a confirmation message
- If a tool takes over, it sends the output
- If not, default model uses message history + `response_context` to generate a reply

---

### **Database Tables**

- `inventory`
    
    [id(int), name(string), quantity (string) , expiration(date)]
    
- `taste_profile`
    
    [id, string]
    
- `saved_meals`
    
    [id(int), name(string), prep time minutes (int),
    
    ingredients tuple (name (string), quantity (string)), recipe(string)]
    
- `new_meal_ideas`
    
    [id(int), name(string), prep time minutes (int),
    
    ingredients tuple (name (string), quantity (string)), recipe(string)]
    
- `saved_meals_instock_ids`
    
    [id(int)]
    
- `new_meal_ideas_instock_ids`
    
    [id(int)]
    
- `daily_planner`
    
    [day(date), notes (string), meal ids (int)]
    
- `shopping_list`
    
    [id(int), amount(float)]
    
- `ingredients_foods`
    
    [id(int), name (string), min_amount_to_buy(int), walmart_link(string)]
    

---

### **Tools**

### `meal_planner.py`

[[Meal Planner Docs]]

Summary:

This tool helps users plan meals by taking their preferences and dietary needs, generating intent (like “quick meals” or “vegetarian”), and then suggesting matching meals. It uses a layered flow: first to understand the user’s request (Layer 1), then to offer specific meals (Layer 2). An internal router manages the conversation flow based on user input.

### `meal_suggestion_gen.py`

[[Meal Suggestion Gen Docs]]

Summary: Helps users plan meals by analyzing their preferences (e.g., dietary needs, meal types) and filtering existing meal options. It uses a layered system: Layer 1 generates meal intents, and Layer 2 selects matching meals. The output includes meal names, prep time, and ingredients.

### `new_meal_ideation.py`

[[New Meal Ideation Docs]]

Summary: Focuses on creating brand-new meal ideas. It starts by generating brief meal descriptions based on user input. If the user is interested, it builds full recipes with ingredients and steps. Users can save recipes for future use. The process is managed in three layers: idea generation, recipe creation, and saving.  
  

### `shopping_list_gen.py`

- **Input:** optional time range (default = today → last planned day)
- **Output:** DB update + confirmation

**Steps:**

1. Gather meal IDs for time range
2. Collect ingredients and quantities
3. Compare with inventory
4. Save missing items and amounts to `shopping_list`

### `place_walmart_order.py`

- **Input:** none
- **Output:** confirmation of placed order

**Steps:**

1. Clone shopping list, standardize units
2. Find items not in `walmart_links`
3. Use browser-enabled AI to find links and update DB
4. Use links to place order

  

  

### **Helper Scripts**

### `db_functions.py`

- Each table has a getter, setter, and formatter

### `db_natural_language_processor.py`

- **Input:** natural language + target table format
- **Output:** structured data ready for DB update

### `instock_checker.py`

- **Input:** list of meal IDs
- **Output:** list of meal IDs that can be made with current inventory

### `prompt_model.py`

- **Input:** model intelligence level (low, med, high) + use local resources (bool)
- **Output:** model object

### `local_model.py`

- Handles requests to local model

### `meal_plan_intent_translator.py`

- **Input:**
    - Initial: time range + meal/taste intent
    - Updated: previous output + changes to make
- **Output:** `[day, notes]`
    - Includes calories/macros (if relevant), new meals inclusion, meal prep times

### `ad_hoc_meal_planner.py`

- **Input:** user intent string
    - Optional bool: limit to inventory
    - Optional bool: include new meals
- **Output:** list of meal IDs

**Process:**

1. If bools are null → spawn mini-agent to infer user preferences
2. Filter available meals based on settings
3. Pick meals matching intent

