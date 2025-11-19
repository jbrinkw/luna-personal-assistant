# Featured Extensions

Luna Hub comes with powerful extensions that add AI capabilities to your daily life. Here are the featured extensions that showcase what's possible.

<script>
// Simple responsive image-map scaler.
// Stores original coords in data-origCoords, then rescales on load + resize.
(function() {
  const scaleMaps = () => {
    document.querySelectorAll('img[usemap]').forEach(img => {
      const usemap = img.getAttribute('usemap');
      if (!usemap) return;
      const map = document.querySelector(`map[name="${usemap.replace('#','')}"]`);
      if (!map) return;

      const naturalWidth = img.naturalWidth || img.width;
      const naturalHeight = img.naturalHeight || img.height;
      if (!naturalWidth || !naturalHeight) return;

      const scaleX = img.clientWidth / naturalWidth;
      const scaleY = img.clientHeight / naturalHeight;

      map.querySelectorAll('area').forEach(area => {
        const orig = area.dataset.origCoords || area.getAttribute('coords');
        area.dataset.origCoords = orig;
        const coords = orig.split(',').map(Number);
        const scaled = coords.map((c, i) => Math.round(c * (i % 2 ? scaleY : scaleX)));
        area.coords = scaled.join(',');
      });
    });
  };

  const setup = () => {
    scaleMaps();
    window.addEventListener('resize', scaleMaps);
    document.querySelectorAll('img[usemap]').forEach(img => {
      if (!img.complete) {
        img.addEventListener('load', scaleMaps, { once: true });
      }
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();
</script>

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

### Visual Walkthrough {: #chefbyte-extension }

#### Walmart Manager - Product Database

<div style="position: relative; display: inline-block;">
  <img src="/tutorial_screenshots/annotated/walmart_manager.png" usemap="#walmart-map" style="max-width: 100%; height: auto;" width="2378" height="1462" />
  <map name="walmart-map">
    <area shape="rect" coords="337,406,571,456" href="#missing-links-count" alt="Missing Links Count" />
    <area shape="rect" coords="1968,622,2296,672" href="#not-a-walmart-item-checkbox" alt="Not a Walmart Item Checkbox" />
    <area shape="rect" coords="488,684,854,734" href="#url-paste-vs-product-suggestions" alt="URL Paste vs Product Suggestions" />
  </map>
</div>

##### 1. Missing Links Count {: #missing-links-count }

Shows how many Grocy products don't have Walmart links yet.

**Why it matters:**
- Unlinked products won't have nutrition data
- Shows how much work is left
- Click to filter unlinked products

##### 2. Not a Walmart Item Checkbox {: #not-a-walmart-item-checkbox }

Mark products that aren't sold at Walmart (homemade items, local produce).

**How to use:**
- Check this box to mark as "not linkable"
- Won't count against missing links
- Keeps database organized

##### 3. URL Paste vs Product Suggestions {: #url-paste-vs-product-suggestions }

Two ways to link products:

- **Paste Walmart URL:** Copy from walmart.com and paste directly
- **Product Suggestions:** Type name and pick from autocomplete

**Pro tip:** URL paste is faster if shopping on walmart.com. Suggestions better for bulk linking.

#### Recipe Browser

![Recipe Browser](/tutorial_screenshots/chefbyte/recipe_browser.png)

Browse and search recipes with integrated nutrition data.

#### Scanner - Barcode Scanning & Inventory

<div style="position: relative; display: inline-block;">
  <img src="/tutorial_screenshots/annotated/scanner_io_wizard_with_items.png" usemap="#scanner-map" style="max-width: 100%; height: auto;" width="2879" height="1454" />
  <map name="scanner-map">
    <area shape="rect" coords="1123,616,1369,666" href="#action-mode-selector" alt="Action Mode Selector" />
    <area shape="rect" coords="402,328,659,378" href="#all-vs-incomplete-tabs" alt="All vs Incomplete Tabs" />
    <area shape="rect" coords="683,982,965,1032" href="#status-badges-new-mp" alt="Status Badges (NEW/MP)" />
    <area shape="rect" coords="624,512,856,562" href="#transaction-history" alt="Transaction History" />
  </map>
</div>

##### 1. Action Mode Selector {: #action-mode-selector }

Choose what happens when you scan a barcode:

- **Add to Grocy:** Add product to inventory
- **Track Nutrition:** Log as consumed, add to daily totals
- **Both:** Add to inventory AND track nutrition

**When to use each:**
- Groceries coming home: "Add to Grocy"
- Eating something: "Track Nutrition"
- Meal prep: "Both"

##### 2. All vs Incomplete Tabs {: #all-vs-incomplete-tabs }

Filter your scanned items:

- **All:** Everything you've scanned
- **Incomplete:** Items missing nutrition data or Walmart links

**Use Case:** Focus on "Incomplete" to clean up database after bulk scanning.

##### 3. Status Badges (NEW/MP) {: #status-badges-new-mp }

Quick visual indicators:

- **NEW:** Product just added to Grocy by this scan
- **MP:** "Missing Product" - not found in Grocy or Walmart databases

**What to do with MP items:**
- Manually add to Grocy first
- Then rescan or link in Walmart Manager

##### 4. Transaction History {: #transaction-history }

View past scans organized by date and time.

**Features:**
- Review yesterday's scans
- Check nutrition totals by day
- Undo accidental scans (coming soon)

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

## Automation Memory: Persistent Context & Task Automation {: #automation-memory-extension }

**Automation Memory** gives your AI the ability to remember context across conversations, create multi-step automated workflows, and schedule recurring tasks—making your assistant truly intelligent and proactive.

### What Can You Do?

**Remember Important Information:**
Store facts, preferences, and context that persists between conversations. Your AI can recall information shared days or weeks ago.

**Automate Multi-Step Workflows:**
Create task flows that chain multiple actions together, like "check weather, then adjust thermostat based on forecast."

**Schedule Recurring Tasks:**
Set up automated routines with cron expressions for tasks like "check shopping list every Monday morning."

### Visual Walkthrough

#### Memories Tab

![Memories Tab](/tutorial_screenshots/automation_memory/memories_tab.png)

Store and retrieve context that persists across conversations. Great for remembering user preferences, facts, and notes.

#### Task Flows Tab

![Task Flows Tab](/tutorial_screenshots/automation_memory/task_flows_tab.png)

Create multi-step task flows with tool calls. Chain together actions like "check weather, then set thermostat."

#### Scheduled Tasks Tab

![Scheduled Tasks Tab](/tutorial_screenshots/automation_memory/scheduled_tasks_tab.png)

Schedule recurring or one-time tasks with cron expressions. Example: "Check shopping list every Monday."

---

## CoachByte: Fitness & Workout Tracking {: #coachbyte-ui }

**CoachByte** is Luna Hub's fitness tracking extension that helps you plan, track, and optimize your strength training with intelligent workout management, personal record tracking, and real-time set logging.

### What is CoachByte?

CoachByte transforms Luna Hub into your personal training log and workout assistant. Whether you're following a structured program or logging workouts as you go, CoachByte provides the tools to track progress, manage your weekly split, and monitor personal records—all integrated with Luna's AI capabilities.

### What Can You Do?

#### 🏋️ Live Workout Tracking
**Track sets and reps in real-time during your workout.**

- Log exercises, weights, and reps as you complete them
- Built-in rest timer between sets
- See your set queue and what's coming next
- Track percentage-based or absolute weights
- Automatic plate calculation (shows 45,45,25 format)

#### 📈 Personal Records
**Monitor your progress with automatic PR tracking.**

- Track rep maxes for any exercise (1RM, 5RM, etc.)
- Estimated one-rep max calculations
- Choose which exercises to track
- Historical PR progression

#### 📅 Weekly Split Planning
**Design your training program with flexible workout splits.**

- Configure exercises by day of the week
- Set reps, rest periods, and exercise order
- Use percentage-based loading (% of 1RM)
- Or use absolute weights
- Automatically calculates working weights from your PRs

#### 📊 Workout History
**Review past training sessions.**

- Calendar view of all workouts
- Add summaries to each session
- View detailed set-by-set breakdowns
- Track training frequency and volume

### Visual Walkthrough

#### Workout Tracker - Main View

![Workout Tracker Main](/tutorial_screenshots/coachbyte/workout_tracker_main.png)

Your workout history at a glance. See recent training sessions with summaries and quickly navigate to detailed views. Use "View PRs" to check your personal records or "Edit Split" to modify your weekly training plan.

#### Personal Records

![Personal Records](/tutorial_screenshots/coachbyte/personal_records.png)

Track your strength progress automatically. CoachByte calculates estimated 1RMs and tracks multiple rep ranges for exercises you choose. Add or remove tracked exercises anytime.

**Features shown:**
- Estimated one-rep maxes
- Multiple rep range PRs (4RM, 5RM, etc.)
- Add/remove tracked exercises
- Automatic calculations from logged sets

#### Weekly Split Editor

![Weekly Split Editor](/tutorial_screenshots/coachbyte/weekly_split_editor.png)

Design your training program day by day. Set exercises, rep schemes, rest periods, and loading strategies for each workout. Use percentage-based loads (relative to your PRs) or absolute weights.

**Features shown:**
- Day-by-day workout planning
- Relative loading (0.85 = 85% of 1RM)
- Absolute loading (70 lbs)
- Rest period configuration
- Exercise order management
- Automatic plate calculation display

#### Active Workout

![Active Workout](/tutorial_screenshots/coachbyte/active_workout.png)

Track your workout as it happens. See what set is next, log your reps and weight, and let the rest timer guide your pacing. View your set queue and completed sets all on one screen.

**Features shown:**
- "Next in Queue" with rest timer
- Current set logging interface
- Set queue (remaining exercises)
- Completed sets history
- Plate breakdown for loading
- Real-time workout progression

### How It Works

**Planning Your Split:**
1. Click "Edit Split" from the main tracker
2. Add exercises for each day of the week
3. Configure reps, loading, and rest periods
4. Save your weekly plan

**Tracking a Workout:**
1. Start your workout day (automatically uses your split)
2. CoachByte shows your "Next in Queue"
3. Complete the set, log weight and reps
4. Rest timer starts automatically
5. Move through your queue until complete
6. Add a workout summary when done

**Setting Up PR Tracking:**
1. Go to "View PRs"
2. Add exercises you want to track
3. CoachByte automatically calculates PRs from logged workouts
4. View estimated maxes and rep records

### Real-World Examples

**Planning Your Week:**
> *"I'm running a push/pull/legs split. How should I set up my Monday push day?"*
> → Configure Bench Press (5x5 @ 85%), Overhead Press (3x8 @ 75%), accessories in the split editor

**During Your Workout:**
> *"Logging workout: Just finished 5 reps of squat at 275 pounds"*
> → CoachByte logs the set, starts rest timer, shows next exercise in queue

**Checking Progress:**
> *"What's my current bench press PR?"*
> → CoachByte shows your 1RM estimate and best rep ranges

### Getting Started

**Prerequisites:**
- Luna Hub installed and running

**Installation:**
1. CoachByte comes pre-installed with Luna Hub
2. Navigate to CoachByte UI from Dashboard
3. Start by setting up your weekly split or jump into tracking a workout

**First Steps:**
1. **Configure PRs**: Add tracked exercises (Bench, Squat, Deadlift, etc.)
2. **Plan your split**: Use "Edit Split" to set up your weekly training program
3. **Track a workout**: Log your first training session and add a summary
4. **Review progress**: Check your workout history and personal records

### Tips for Using CoachByte

**Use Percentage Loading:**
Set your exercises as percentages of your 1RM (e.g., 85%) so CoachByte automatically adjusts weights as you get stronger.

**Add Workout Summaries:**
After finishing, add a brief summary of how the workout felt. This helps track subjective progress alongside the numbers.

**Track Core Lifts:**
Set up PR tracking for your main lifts (squat, bench, deadlift, overhead press) to monitor long-term strength gains.

**Consistent Rest Periods:**
Configure appropriate rest times in your split (120-180 seconds for main lifts, 60-90 for accessories) to maintain training consistency.

---

## Quick Chat: Testing Interface {: #quick-chat }

**Quick Chat** is Luna's built-in testing interface for verifying that your agents, MCP servers, and tools work correctly. It's designed for debugging and experimentation, not production use.

### Visual Walkthrough

<div style="position: relative; display: inline-block;">
  <img src="/tutorial_screenshots/annotated/quick_chat_interface.png" usemap="#quick-chat-map" style="max-width: 100%; height: auto;" width="2879" height="1366" />
  <map name="quick-chat-map">
    <area shape="rect" coords="8,476,363,526" href="#agent-mode-vs-mcp-mode-toggle" alt="Agent Mode vs MCP Mode Toggle" />
    <area shape="rect" coords="995,703,1261,753" href="#response-time-tracker" alt="Response Time Tracker" />
  </map>
</div>

#### 1. Agent Mode vs MCP Mode Toggle {: #agent-mode-vs-mcp-mode-toggle }

Switch between two testing modes:

**Agent Mode:**
- Chat with Luna's built-in agents or custom presets
- Full agent workflow with reasoning
- Good for testing complete agent behavior

**MCP Mode:**
- Test MCP server tool calls directly
- Direct tool invocation without agent reasoning
- Good for debugging individual tools

#### 2. Response Time Tracker {: #response-time-tracker }

Displays how long the agent or MCP server took to respond.

**Shows:**
- Total response time
- Time breakdown for tool calls
- Performance bottlenecks

**Why it matters:**
- Debug slow tools
- Compare agent performance
- Optimize configurations

### When to Use Quick Chat

- After installing an extension
- After creating an agent preset
- After adding a remote MCP server
- For debugging tool failures

### Common Testing Workflows

**Testing a new extension:**
1. Install extension and restart
2. Go to Quick Chat
3. Select agent with extension's tools
4. Type message that triggers the tool
5. Verify response

**Testing an agent preset:**
1. Create preset in Tool Manager
2. Restart Luna
3. Select preset in Quick Chat
4. Try enabled and disabled tools
5. Verify filtering works

### Limitations

Quick Chat is for testing only:
- No authentication
- No rate limiting
- No persistence
- Simple UI

For production, use Luna's Agent API with proper clients.

---

## GeneralByte: Essential Assistant Utilities {: #generalbyte-extension }

**GeneralByte** provides core utility tools that every AI assistant needs: phone notifications, web search, and weather information.

### What Can You Do?

#### 📱 Phone Notifications
**Send push notifications to your phone via Home Assistant.**

- *"Send me a reminder to pick up milk"*
- *"Notify me when the laundry is done"*
- Custom notification titles and messages

**Requirements:**
- Home Assistant with configured notify service
- Default service: `mobile_app_jeremys_iphone` (configurable)

#### 🔍 Web Search
**Search the web using Tavily API.**

- *"Search for the latest news on AI"*
- *"Find recipes for chocolate chip cookies"*
- Configurable result count (default: 5)
- Returns titles, URLs, and content snippets

**Powered by:** Tavily search API

#### 🌤️ Weather Information
**Get current weather conditions for any location.**

- *"What's the weather in Charlotte?"*
- *"Check the temperature in New York"*
- Defaults to Charlotte, NC if no location specified

**Features:**
- Current temperature and "feels like" temperature
- Weather conditions (clear, cloudy, rain, etc.)
- Wind speed and direction
- Free Open-Meteo API (no credentials needed)

### Getting Started

**Prerequisites:**
- Home Assistant instance (for notifications)
- Tavily API key (for web search)
- No API key needed for weather

**Installation:**
1. GeneralByte comes pre-installed with Luna Hub
2. Add required keys in **Settings → Environment Keys**:
   - `HA_URL` - Your Home Assistant URL
   - `HA_TOKEN` - Home Assistant access token
   - `TAVILY_API_KEY` - Tavily search API key
   - `DEFAULT_NOTIFY_SERVICE` - Optional (defaults to mobile app)

---

## Obsidian Sync: Knowledge Management Integration {: #obsidian-sync-extension }

**Obsidian Sync** connects your Obsidian vault to Luna Hub, allowing your AI to read, query, and update your personal knowledge base with dated notes and project hierarchies.

### What is Obsidian Sync?

Obsidian is a powerful markdown-based knowledge management tool. Luna's Obsidian Sync extension syncs your vault and provides AI tools to interact with your notes conversationally.

### What Can You Do?

#### 📚 Project Hierarchy Management
**Navigate your project structure with AI assistance.**

- *"Show me my project hierarchy"*
- View parent-child project relationships
- Query project details and notes

#### 📝 Dated Note Queries
**Search notes by date range.**

- *"What did I write last week?"*
- *"Show me notes from January"*
- Query across all project notes
- Results sorted newest-first

#### ✏️ Update Project Notes
**Add dated entries to project notes.**

- *"Add a note to the Luna project: Fixed bug today"*
- Automatically creates today's entry
- Supports markdown section placement
- Creates note files if needed

#### 🔗 Project Text Retrieval
**Get full project content including notes.**

- *"Show me the Luna project page"*
- Returns both project page and Notes.md
- Look up by project ID or display name

### How It Works

**Sync Service:**
- Background service syncs vault every 5 minutes
- Supports local directories or Git repositories
- Handles Git authentication with tokens
- Excludes Obsidian config/cache files

**Data Structure:**
Obsidian Sync uses YAML frontmatter in markdown files:
```yaml
---
project_id: luna-development
project_parent: software-projects
---
```

Notes files link to projects:
```yaml
---
note_project_id: luna-development
---
```

### Getting Started

**Prerequisites:**
- Obsidian vault (local or Git repository)
- GitHub token (if using private Git repo)

**Installation:**
1. Install **Obsidian Sync** from Extensions
2. Add configuration in **Settings → Environment Keys**:
   - `OBSIDIAN_VAULT_LINK` - Path or Git URL to vault
   - `OBSIDIAN_VAULT_GIT_TOKEN` - Optional for private repos
3. Restart Luna to start sync service

**First Steps:**
1. Sync happens automatically every 5 minutes
2. Ask: *"Show me my project hierarchy"*
3. Query notes: *"What notes did I write this week?"*
4. Add entries: *"Add note to [project]: [content]"*

### Tips for Using Obsidian Sync

**Use Consistent Frontmatter:**
Always include `project_id` and `project_parent` fields in project pages for proper hierarchy tracking.

**Dated Note Format:**
Notes are organized by date in MM/DD/YY format. The extension automatically formats today's date when adding entries.

**Git vs Local:**
- Local path: Faster, direct access
- Git repository: Better for remote access, version control

---

## Todo List: Task Management with Todoist {: #todo-list-extension }

**Todo List** integrates Todoist's powerful task management into Luna Hub, giving you AI-powered control over tasks, projects, sections, priorities, and due dates.

### What Can You Do?

#### ✅ Task Management
**Full CRUD operations on your tasks.**

- *"Create a task: Buy groceries"*
- *"What tasks are due today?"*
- *"Complete the 'finish report' task"*
- *"Update task priority to urgent"*

#### 📁 Project & Section Organization
**Manage tasks within projects and sections.**

- *"List all my projects"*
- *"Show tasks in the Work project"*
- *"Add task to Shopping section"*
- *"What's in my Inbox?"*

#### 🔥 Priorities & Due Dates
**Set priorities and deadlines.**

- Priorities: 1 (lowest) to 4 (highest/urgent)
- Natural language dates: "today", "tomorrow", "next monday"
- ISO8601 format: "2025-12-01"
- Due dates and datetimes

#### 🔍 Advanced Filtering
**Use Todoist's filter syntax.**

- *"Show me today | overdue tasks"*
- *"List priority 1 tasks"*
- *"Tasks with @work label"*
- *"Everything in #personal project"*

### Real-World Examples

**Morning Review:**
> *"What's on my list for today?"*
> → Shows all tasks due today

**Adding Tasks:**
> *"Add 'Review documentation' to Work project, due tomorrow, priority 2"*
> → Task created with all metadata

**Completing Work:**
> *"Mark 'finish report' as complete"*
> → Task closed in Todoist

**Advanced Queries:**
> *"Show me all high-priority overdue tasks"*
> → Filter: "priority 4 & overdue"

### How It Works

**Todoist Integration:**
- Uses Todoist REST API v2
- Supports all Todoist filter syntax
- Automatic task enrichment with project/section names
- Real-time synchronization

**Available Tools:**
1. List projects
2. List sections (all or by project)
3. Get task by ID
4. List tasks with filters
5. Create task
6. Update task
7. Complete task

### Getting Started

**Prerequisites:**
- Todoist account (free or premium)
- Todoist API token

**Installation:**
1. Install **Todo List** from Extensions
2. Get API token from Todoist settings
3. Add to **Settings → Environment Keys**:
   - `TODOIST_API_TOKEN` - Your API token
4. Restart Luna

**First Steps:**
1. Ask: *"List my projects"*
2. Create a task: *"Add task: Test Luna integration"*
3. Query: *"What's due today?"*
4. Complete: *"Mark [task] as done"*

### Tips for Using Todo List

**Be Specific with Projects:**
Always specify the project when creating tasks to keep your inbox clean.

**Use Natural Language Dates:**
"today", "tomorrow", "next friday" work perfectly for due dates.

**Leverage Filters:**
Learn Todoist's filter syntax for powerful queries:
- `today` - Tasks due today
- `overdue` - Past-due tasks
- `no date` - Tasks without due dates
- `p1` - Priority 1 tasks
- `##Work` - Tasks in Work project

**Priority Levels:**
- Priority 4 (red flag): Urgent
- Priority 3 (orange): High
- Priority 2 (blue): Medium
- Priority 1 (normal): Low

---

## What's Next?

Luna Hub's extension ecosystem provides powerful integrations for productivity, smart home, fitness, knowledge management, and more. Developers can create extensions for:
- Calendar and task management (like Todo List)
- Note-taking and knowledge bases (like Obsidian Sync)
- Email and messaging
- File management and backups
- Weather and utilities (like GeneralByte)
- Custom integrations for work tools
- Anything with an API!

**Ready to install these extensions?** Visit **Extensions** in your Luna Hub dashboard and browse the store!
