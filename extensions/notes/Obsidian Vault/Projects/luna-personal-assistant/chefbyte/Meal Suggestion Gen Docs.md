## **User Interaction Flow with the Meal Suggestion Generator**

### 1. **Initiating a Meal Suggestion Request**

- The user starts by requesting meal suggestions, often including dietary preferences, meal types (e.g., breakfast, dinner), or other specific criteria.

### 2. **Context Generation**

- The tool analyzes recent user messages to build context. This helps it understand the user’s preferences and the type of meals they're seeking.

### 3. **Filtering Meal Suggestions**

- Using the generated context and user intent, the tool filters through available meal options to find the best matches—favoring meals that meet specified criteria (e.g., quick, vegetarian).

### 4. **Formatting the Results**

- After identifying suitable meals, the tool formats them for display. It includes the meal name, preparation time, ingredients, and whether it's a saved recipe or a new idea.

### 5. **Presenting Suggestions to the User**

- The formatted suggestions are shown to the user. The user can review, ask for more info, or request alternative suggestions.

## **Internal Components**

### **MealSuggestionContextBuilder**

- **Purpose**: Builds context from the user’s recent messages to guide meal selection.
- **Function**: Extracts preferences and requirements to inform suggestion logic.

### **MealSuggestionFilter**

- **Purpose**: Filters meals based on user intent and context.
- **Process**:
    - Uses a prompt template to guide AI in selecting relevant meal IDs.
    - Defaults to suggesting three meals unless specified otherwise.
    - Prioritizes meals that match user-defined filters.

### **MealSuggestionFormatter**

- **Purpose**: Formats the selected meals for user display.
- **Process**:
    - Retrieves meal data by ID from the database.
    - Assembles user-friendly output with name, type, prep time, and ingredients.
    - Prompts for more input if no meals are found.

---

## **Functionality Overview**

### **Main Function:** `**generate_meal_suggestions**`

- **Purpose**: Coordinates the entire suggestion pipeline based on the user's message history.
- **Process**:
    1. Extracts user intent from recent messages.
    2. Builds context using `MealSuggestionContextBuilder`.
    3. Filters meals with `MealSuggestionFilter`.
    4. Formats the final output via `MealSuggestionFormatter`.
    5. Returns the completed suggestions to the user.