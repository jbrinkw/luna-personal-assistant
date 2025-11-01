# Featured Extensions

Luna Hub comes with powerful extensions that add AI capabilities to your daily life. Here are the featured extensions that showcase what's possible.

---

## ChefByte: Your AI Kitchen Assistant

**ChefByte** transforms Luna Hub into your personal kitchen manager. By connecting to Grocy (a self-hosted household management app), ChefByte gives you AI-powered control over everything food-related—from tracking what's in your pantry to planning meals and managing shopping lists.

### What is ChefByte?

Think of ChefByte as having a knowledgeable friend who always knows what's in your kitchen, can suggest meals based on what you have, and keeps your shopping organized. Instead of manually logging every item or clicking through menus, you simply talk to your AI assistant and ChefByte handles the rest.

### What Can You Do With ChefByte?

#### 🥫 Inventory Management
**Never wonder "what do I have?" again.**

- **Check your pantry instantly**: *"What's in my inventory?"* or *"Do I have milk?"*
- **Track expiration dates**: See what's about to expire so nothing goes to waste
- **Add items when you shop**: *"I bought 2 cartons of milk and a dozen eggs"*
- **Mark items as used**: *"I used 1 cup of flour for baking"*

ChefByte keeps a real-time count of everything in your kitchen, including:
- Current quantities (2 gallons of milk, 6 eggs remaining, etc.)
- Expiration dates
- Storage locations

#### 🛒 Shopping List Management
**Build and manage shopping lists effortlessly.**

- **Add items by voice**: *"Add milk to my shopping list"*
- **Remove items**: *"Remove bread from the shopping list"*
- **Check what you need**: *"What's on my shopping list?"*
- **Smart restocking**: Automatically add items that are running low
- **Clear completed lists**: Start fresh after shopping

Your AI can intelligently manage multiple shopping lists and even suggest quantities based on your usage patterns.

#### 📅 Meal Planning
**Plan your week's meals with AI assistance.**

- **Add meals to your calendar**: *"Add spaghetti to dinner on Friday"*
- **Use saved recipes**: Link meal plans to your recipe collection
- **Track what you've eaten**: *"Mark today's breakfast as complete"*
- **Plan ahead**: See the whole week's meal plan at a glance
- **Remove or change meals**: *"Delete Tuesday's dinner plan"*

ChefByte connects your meal plans to your inventory, so it knows what ingredients you have and what you'll need.

#### 🍳 Recipe Management
**Store and organize your favorite recipes.**

- **Save recipes with ingredients**: *"Create a recipe for chocolate chip cookies"*
- **Add ingredient lists**: Link recipes to products in your inventory
- **See cookable recipes**: *"What can I make with what I have?"*
- **Get all recipes**: Browse your collection anytime

Recipes in ChefByte automatically check if you have the ingredients, making meal planning effortless.

#### 📊 Nutrition Tracking
**Track calories and macros automatically.**

- **Log meals**: *"I ate 2 eggs and toast for breakfast"*
- **Track macros**: See your daily protein, carbs, fats, and calories
- **Review your day**: *"What did I eat today?"*
- **Monitor progress**: Check nutrition over time

ChefByte integrates with Nutritionix API to automatically calculate nutrition info for common foods, and you can create custom "temporary items" for home-cooked meals.

#### 💰 Price Tracking
**Keep tabs on grocery costs.**

- **Log product prices**: *"Milk costs $4.99"*
- **Compare over time**: See if prices are going up or down
- **Budget better**: Know how much your groceries actually cost

### Real-World Examples

Here's how ChefByte works in everyday situations:

**Morning:**
> *"Good morning! Did I run out of coffee?"*
> → ChefByte checks inventory: "You have 1 cup of coffee left"
> *"Add coffee to my shopping list"*
> → Added to shopping list

**Planning Dinner:**
> *"What can I cook tonight with what I have?"*
> → ChefByte checks cookable recipes: "You can make spaghetti, stir-fry, or chicken tacos"
> *"Add chicken tacos to dinner tonight"*
> → Meal added to today's plan

**After Dinner:**
> *"I made chicken tacos, mark them as done"*
> → Meal marked complete
> *"Log my dinner: 3 tacos with rice and beans"*
> → ChefByte calculates nutrition and logs it

**At the Grocery Store:**
> *"What's on my shopping list?"*
> → ChefByte reads the list: "Coffee, milk, chicken, tortillas..."

**After Shopping:**
> *"I bought 1 pound of coffee, 2 gallons of milk, and 2 pounds of chicken"*
> → ChefByte adds everything to inventory
> *"Clear my shopping list"*
> → List cleared, ready for next week

### How ChefByte Works

ChefByte is an extension that connects Luna Hub to Grocy, a powerful household management web application. Here's how they work together:

1. **Grocy** runs as a Docker container managed by Luna Hub (see Apps/Services)
2. **ChefByte extension** provides AI tools that talk to Grocy's API
3. **Your AI agent** uses ChefByte's tools when you ask kitchen-related questions
4. **Everything syncs** in real-time—changes in Grocy appear in ChefByte and vice versa

You can use Grocy's web interface directly for detailed management, or talk to your AI for quick tasks. ChefByte makes Grocy conversational.

### Getting Started with ChefByte

**Prerequisites:**
- Luna Hub installed and running
- Grocy app/service installed (see Apps/Services in Luna Hub)
- OpenAI API key (for intelligent meal suggestions)

**Installation:**
1. Navigate to **Extensions** in Luna Hub
2. Find **ChefByte** in the store (currently listed as "grocy")
3. Click **Install**
4. Add required API keys in **Settings → Environment Keys**:
   - `GROCY_BASE_URL` - Your Grocy instance URL (auto-configured)
   - `GROCY_API_KEY` - Grocy API key
   - `OPENAI_API_KEY` - For meal planning intelligence

**Configuration:**
ChefByte needs a few Grocy settings:
- `GROCY_DEFAULT_LOCATION_ID` - Where items are stored (e.g., "Pantry")
- `GROCY_DEFAULT_QU_ID_PURCHASE` - Default purchase unit (e.g., "piece")
- `GROCY_DEFAULT_QU_ID_STOCK` - Default stock unit (e.g., "piece")

Luna Hub's installer can set these up automatically when you install Grocy.

**First Steps:**
1. Open Grocy's web UI (at `/apps_services/grocy/` in Luna Hub)
2. Add a few products manually to get familiar
3. Ask your AI: *"What's in my inventory?"*
4. Start adding to shopping lists and planning meals!

### Tips for Using ChefByte

**Be Natural:**
ChefByte understands conversational language. You don't need to be precise:
- ✅ *"Do I have any milk?"*
- ✅ *"Add a couple avocados to shopping list"*
- ✅ *"What's for dinner this week?"*

**Use Product Names Consistently:**
ChefByte works best when you use the same product names. "Milk" vs "Whole Milk" vs "2% Milk" are different products.

**Plan Your Week:**
Set aside 10 minutes on Sunday to:
1. Check what you have
2. Plan the week's meals
3. Generate a shopping list
4. Let ChefByte add missing ingredients automatically

**Log As You Go:**
After meals, quickly tell your AI what you ate. This builds a nutrition history over time.

**Review Regularly:**
Ask periodic questions like:
- *"What's about to expire?"*
- *"What am I low on?"*
- *"What did I spend on groceries this month?"*

### Advanced Features

**Placeholders:**
Create "placeholder" items for ingredients you don't have exact counts for (like "1 onion" or "fresh basil"). ChefByte can add these to shopping lists without tracking exact inventory.

**Temporary Nutrition Items:**
Log one-off meals that aren't in your inventory:
- *"Log a burger and fries, estimate 800 calories"*
- ChefByte creates a temporary entry for that day

**Recipe-Based Meal Planning:**
Link meal plans to saved recipes, and ChefByte will:
1. Check if you have all ingredients
2. Add missing items to shopping list
3. Mark ingredients as consumed when you cook

**Batch Operations:**
ChefByte can handle multiple requests at once:
- *"Add milk, eggs, and bread to my shopping list"*
- *"I bought 2 pounds of chicken, 1 pound of beef, and 3 apples"*

---

## Home Assistant: Voice-Controlled Smart Home

**Home Assistant** is Luna Hub's smart home extension, giving you voice control over lights, switches, thermostats, and more through natural conversation with your AI.

### What is Home Assistant?

Home Assistant is one of the most popular open-source smart home platforms. Luna Hub's Home Assistant extension connects your AI to your home automation setup, letting you control everything with natural language instead of apps and switches.

### What Can You Do?

**Device Control:**
- *"Turn on the living room lights"*
- *"Set the thermostat to 72 degrees"*
- *"Turn off all the lights"*

**Status Checks:**
- *"Is the garage door open?"*
- *"What's the temperature in the bedroom?"*
- *"Are any lights on downstairs?"*

**Media Control:**
- *"Play music in the kitchen"*
- *"Pause the TV"*
- *"Set volume to 50%"*

**Scenes and Automation:**
- *"Set movie mode"* (dims lights, closes blinds, starts TV)
- *"I'm going to bed"* (locks doors, turns off lights, sets alarm)

### How It Works

The Home Assistant extension provides tools that connect to your Home Assistant instance:
- **Get device status**: Check if lights are on, doors locked, etc.
- **Control devices**: Turn things on/off, adjust settings
- **Run scenes**: Trigger complex automation with one command

You need a running Home Assistant instance (separate from Luna Hub). Once connected, your AI can control anything Home Assistant manages.

### Real-World Example: Private Alexa Alternative

Combine Luna Hub's Home Assistant extension with the Agent API, and you've built your own privacy-focused voice assistant:

1. Install Luna Hub on a home server
2. Connect the Home Assistant extension
3. Use a voice interface on your phone to talk to Luna's Agent API
4. Ask natural questions like:
   - *"Turn on the lights and tell me what's on my shopping list"*
   - *"Lock the doors and set the alarm"*
   - *"What's in my pantry? And is the garage door closed?"*

Unlike Alexa or Google Home, your conversations never leave your network. You control the data, the tools, and the privacy.

### Getting Started

**Prerequisites:**
- Home Assistant running (locally or remotely)
- Home Assistant API token

**Installation:**
1. Install **Home Assistant extension** from Luna Hub's store
2. Add credentials in **Settings → Environment Keys**:
   - `HA_URL` - Your Home Assistant URL
   - `HA_TOKEN` - Long-lived access token from Home Assistant

**First Steps:**
1. Ask: *"What devices do you see?"*
2. Test control: *"Turn on the kitchen light"*
3. Build scenes and automation in Home Assistant
4. Control everything with your voice!

---

## What's Next?

These are just two examples of what Luna Hub extensions can do. Developers can create extensions for:
- Calendar and task management
- Email and messaging
- File management and backups
- Weather and news
- Custom integrations for work tools
- Anything with an API!

**Want to build your own extension?** Check out the [Developer Guide](../developer-guide/creating-extensions.md).

**Ready to install these extensions?** Visit **Extensions** in your Luna Hub dashboard and browse the store!
