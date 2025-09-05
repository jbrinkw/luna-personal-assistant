## **User Interaction Flow with the New Meal Ideation Tool**

### 1. **Initiating a Meal Ideation Request**

- The user starts by requesting new meal ideas, possibly including dietary preferences, desired ingredients, or other criteria.

### 2. **Analyzing User Intent**

- The tool reviews the user’s recent messages to understand their preferences and requirements. This determines what kind of meals to suggest.

### 3. **Generating Meal Descriptions**

- Based on user intent, the tool creates a list of meal descriptions. Each includes a meal name and a short summary.

### 4. **Reviewing Meal Descriptions**

- The user reviews the list and selects the meals they’re interested in.

### 5. **Generating Full Recipes**

- For selected meals, the tool generates detailed recipes including ingredients, prep time, and step-by-step instructions.

### 6. **Saving Recipes**

- Users can save their favorite recipes. The tool handles the save operation and confirms successful storage.

---

## **Internal Components**

### **MealIdeationEngine**

- **Purpose**: Main engine managing the ideation workflow and AI interaction.
- **Functionality**:
    - Initializes with database connections.
    - Uses prompts to generate both meal descriptions and recipes.

### **Router**

- **Purpose**: Manages conversation flow based on message history.
- **Functionality**:
    - Routes between generating meal descriptions, recipes, or saving.
    - Detects user inventory limits and specific meal selections.

### **Meal Description & Recipe Models**

- **Purpose**: Define structure and validation rules for meal data.
- **Functionality**:
    - `MealDescription`: Holds meal name and summary.
    - `MealRecipe`: Stores ingredients, prep time, and cooking steps.

---

## **Functionality Overview**

### **Main Function:** `**generate_meal_ideas**`

- **Purpose**: Central function to initiate the ideation process.
- **Process**:
    1. Initializes `MealIdeationEngine`.
    2. Uses router to determine next step.
    3. Generates descriptions, full recipes, or saves based on flow state.

---

## **Layered Functionality**

### **Layer 1: Generating Meal Descriptions**

- **Purpose**: Create initial meal ideas aligned with user preferences.
- **Process**:
    - Generates 3 unique meals (avoids duplicates).
    - Returns list for user to review.

### **Layer 2: Generating Full Recipes**

- **Purpose**: Provide complete cooking instructions for selected meals.
- **Process**:
    - Generates full recipes based on selected descriptions.
    - Includes ingredients, prep time, and instructions.

### **Layer 3: Saving Recipes**

- **Purpose**: Persist selected recipes for later access.
- **Process**:
    - Checks for duplicates by name.
    - Saves new recipes and confirms success.