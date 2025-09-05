### **1. User Initiation**

The user begins by expressing a desire for meal suggestions, typically through a message that outlines their preferences, dietary restrictions, or specific meal types they are interested in.

### **2. Context Generation**

The tool processes the user's message to understand the context better. It gathers relevant information from recent interactions to create a comprehensive context that reflects the user's needs.

### **3. Meal Suggestion Filtering**

Based on the user's intent and the generated context, the tool filters through available meal options to identify the best matches. This ensures that suggestions align with the user's preferences.

### **4. Display of Suggestions**

The tool formats the filtered meal suggestions into a user-friendly output, providing details such as meal names, preparation times, and ingredients. These are then presented to the user.

### **5. User Feedback**

After reviewing the suggestions, the user can respond with further requests—like asking for more details about a specific meal, requesting different options, or confirming their choice. This feedback leads to additional interactions to refine the meal planning.

---

## **Internal Router**

The internal router manages the flow of conversation between the user and the meal suggestion tool. It categorizes the interaction into one of three states:

### **1. LAYER_1_INTENT_GENERATION**

Activated when the user is initiating a meal planning request. The router directs the flow to generate meal intents based on the user's input.

### **2. LAYER_2_MEAL_SELECTION**

Triggered when the user confirms they want to select specific meals based on the intents generated in Layer 1. The router transitions the flow to the meal selection process.

### **3. GENERAL_CHAT**

Covers any conversation not related to meal planning. Used for general inquiries or unrelated discussion.

---

## **Layer Functionality**

### **Layer 1: Intent Generation**

**Purpose**: Extract the user's meal planning intent and generate suitable meal intents based on their preferences.

**Process**:

1. Analyze the user's message to identify key information (e.g., meal types, dietary restrictions, time frame).
2. Generate meal intents like "quick and easy meals" or "vegetarian options."
3. Save the generated intents for future use in guiding meal selection.

---

### **Layer 2: Meal Selection**

**Purpose**: Select specific meals based on the intents generated in Layer 1.

**Process**:

1. Retrieve saved meal intents from Layer 1.
2. Use the meal suggestion context builder to generate a personalized context.
3. Filter through available meals to find the best matches for the user’s intent.
4. Format selected meal IDs into a user-friendly output with details like prep time and ingredients.

---

Let me know if you want it rewritten into a flowchart or turned into a code-ready schema.