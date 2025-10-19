# Phase 2: User Interface Layer - Detailed Conceptual Instructions

---

## Overview

### Goal
Build a complete React-based UI that consumes the Phase 1 backend APIs, providing users with visual interfaces for extension management, configuration, and system monitoring.

### Technology Stack
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite (fast dev server, optimized builds)
- **Routing**: React Router v6
- **State Management**: React Context API + hooks (no Redux needed for MVP)
- **Styling**: Tailwind CSS (utility-first, fast development)
- **HTTP Client**: Fetch API or Axios
- **Forms**: React Hook Form (efficient form handling)
- **Icons**: Lucide React (consistent icon set)

### Architecture Principles
1. **Separation of Concerns**: UI components separate from business logic
2. **API Client Layer**: Centralized API calls, not scattered in components
3. **Type Safety**: TypeScript interfaces for all data structures
4. **Component Reusability**: Build generic components, compose complex UIs
5. **Progressive Enhancement**: Core functionality first, polish later
6. **Error Boundaries**: Graceful error handling at component level

---

## Phase 2A: Hub UI Foundation (Week 5)

### Milestone 2A.1: Project Setup & Architecture

#### Conceptual Tasks

**1. Initialize Vite React TypeScript Project**
- Set up new Vite project in `hub_ui/` directory
- Configure TypeScript with strict mode
- Add necessary dependencies (react-router, tailwind, etc.)
- Configure path aliases for clean imports

**2. Project Structure Design**
```
hub_ui/
├── public/              # Static assets
├── src/
│   ├── components/      # Reusable UI components
│   │   ├── layout/      # Layout components (Header, Sidebar, etc.)
│   │   ├── common/      # Generic components (Button, Card, Modal, etc.)
│   │   └── features/    # Feature-specific components
│   ├── pages/           # Top-level page components
│   ├── lib/             # Utilities and helpers
│   │   ├── api/         # API client and endpoints
│   │   ├── types/       # TypeScript type definitions
│   │   └── utils/       # Helper functions
│   ├── context/         # React Context providers
│   ├── hooks/           # Custom React hooks
│   ├── App.tsx          # Root application component
│   └── main.tsx         # Entry point
```

**3. Type System Foundation**
Define core TypeScript interfaces that mirror backend data structures:
- Extension interface (name, version, enabled, source, config, etc.)
- Service interface (name, status, port, pid, etc.)
- Tool interface (name, extension, enabled_in_mcp, passthrough, etc.)
- MasterConfig interface (complete structure)
- QueueOperation interface (type, source, target, etc.)
- PortAssignments interface
- ServiceStatus values as union types

**4. API Client Architecture**
Create centralized API client with:
- Base URL configuration (http://127.0.0.1:9999)
- Request wrapper with error handling
- Response type safety
- HTTP methods (GET, POST, PATCH, DELETE, PUT)
- Automatic JSON parsing
- Error boundary integration

Organize API endpoints by domain:
- ConfigAPI (all /api/config/* endpoints)
- ExtensionsAPI (all /api/extensions/* endpoints)
- QueueAPI (all /api/queue/* endpoints)
- ServicesAPI (all /api/services/* endpoints)
- ToolsAPI (all /api/tools/* endpoints)
- KeysAPI (all /api/keys/* endpoints)
- SystemAPI (/health, /restart, etc.)

---

### Milestone 2A.2: Layout Components

#### Conceptual Components

**1. Layout Component**
- Purpose: Master layout wrapper for all pages
- Structure: Header + Sidebar + MainContent area
- Responsive: Sidebar collapses on mobile (hamburger menu)
- Persistent across navigation
- Provides layout context (sidebar open/closed state)

**2. Header Component**
- Left side: Luna logo and name
- Right side: System health indicator + version number
- Health indicator polls /health endpoint every 10 seconds
- Visual states: Healthy (green dot), Degraded (yellow), Down (red)
- Sticky positioning at top
- Clean, minimal design

**3. Sidebar Component**
- Fixed width on desktop (240px)
- Collapsible on mobile
- Two sections:
  - Static navigation (Dashboard, Extensions, Queue, Store, Secrets)
  - Dynamic extensions (shows enabled extensions with UIs)
- Active route highlighting
- Icons + labels for each item
- Smooth transitions
- Scroll independently if content overflows

**4. MainContent Component**
- Flexible width (fills remaining space)
- Max width constraint for readability (1400px)
- Centered content
- Padding and spacing
- Background color
- Scroll container

---

### Milestone 2A.3: Routing & Navigation

#### Routing Strategy

**Route Structure:**
```
/                           → Dashboard page
/extensions                 → Extension list view
/extensions/:name           → Extension detail view (with tabs)
/queue                      → Queue management
/store                      → Extension store
/secrets                    → Key manager
/ext/:name                  → Extension UI iframe
```

**Navigation Flow:**
- User clicks sidebar item → Route changes → Page component renders
- Browser back/forward buttons work correctly
- Active route highlighted in sidebar
- Page title updates per route
- Deep linking works (can bookmark any page)

**Route Guards (Optional for MVP):**
- No authentication in MVP, but structure should allow future auth
- Could add loading states while checking system health

---

### Milestone 2A.4: Global State Management

#### State Architecture

**What Needs Global State:**
1. System health status (used in header)
2. Master config (used throughout app)
3. Current service statuses (used in multiple views)
4. Pending changes tracking (for queue management)

**Context Providers to Create:**

**SystemContext:**
- Current health status
- Luna version
- System uptime
- Polling mechanism for health checks
- Methods: refreshHealth()

**ConfigContext:**
- Master config (originalState)
- Current working state (currentState)
- Queued state (queuedState)
- Methods: loadMasterConfig(), updateExtension(), updateTool()
- Dirty flag (has unsaved changes)

**ServicesContext:**
- Service status map
- Polling mechanism (every 30 seconds)
- Methods: refreshServices(), restartService(name)

**Usage Pattern:**
- Wrap App in provider stack
- Components consume contexts with useContext hook
- Avoid prop drilling
- Keep context focused (single responsibility)

---

## Phase 2B: Extension Manager UI (Week 5-6)

### Milestone 2B.1: Extension List View

#### Page Architecture

**Data Flow:**
1. Page loads → Call GET /api/extensions
2. Also call GET /api/config/master for config
3. Also call GET /api/services/status for service health
4. Merge data: extensions + configs + service statuses
5. Render grid of extension cards

**State Management:**
- Use ConfigContext for master config
- Use ServicesContext for service statuses
- Local state for view filters (if any)
- Loading state while fetching
- Error state if fetch fails

**Extension Card Component Design:**

Each card displays:
- Extension name and icon (if available)
- Version number
- Enabled/disabled toggle (controls currentState)
- Health status indicator (from services)
- Tool count (from extension config)
- Service count (from extension structure)
- Action buttons: Details (navigates), Delete (updates currentState)

**Interactions:**
- Toggle enabled → Updates ConfigContext currentState → Shows in pending changes
- Click Details → Navigate to /extensions/:name
- Click Delete → Confirmation modal → Updates currentState → Shows in pending changes
- All changes staged, not saved immediately
- Visual indicator when extension has pending changes

**Upload Extension Flow:**
1. User clicks "Upload" button
2. File picker opens
3. User selects .zip file
4. POST /api/extensions/upload with multipart form
5. Backend returns temp filename
6. Extract extension name from original filename
7. Check if extension exists in originalState:
   - Exists → This is UPDATE operation
   - Not exists → This is INSTALL operation
8. Add to currentState with source: "upload:{temp_filename}"
9. Card appears in grid immediately (optimistic UI)
10. Changes appear in pending list

---

### Milestone 2B.2: Extension Detail View

#### Page Structure

**URL Pattern:** `/extensions/:name`

**Data Loading:**
1. Extract :name from URL params
2. Load extension config from ConfigContext
3. Load tools from extension's tool_config.json (via API)
4. Load services from extension's services/ (via API)
5. Load readme content (via API)

**Tab System:**
- Three tabs: Tools, Services, About
- Tab state in URL query param (e.g., ?tab=tools) for deep linking
- Default to Tools tab
- Smooth tab transitions
- Remember last visited tab (localStorage)

---

#### Tools Tab Design

**Purpose:** Configure which tools are exposed to MCP and passthrough mode

**Layout:**
- List of all tools from this extension
- Each tool as a card/row with:
  - Tool name (e.g., NOTES_CREATE_note)
  - Description (extracted from docstring first line)
  - Two checkboxes:
    - "Enabled in MCP" (controls enabled_in_mcp)
    - "Passthrough Mode" (controls passthrough)
  - Expand button to see full docstring

**State Management:**
- Tools configuration stored in ConfigContext currentState
- Checkbox changes update currentState immediately
- No save button on this tab (changes tracked globally)
- Visual dirty indicator per tool if changed from original

**Data Flow:**
1. Load tool_config.json for extension
2. For each tool, render configuration UI
3. User toggles checkbox
4. Update ConfigContext.currentState.tool_configs[tool_name]
5. Change reflected immediately in UI
6. Pending changes counter increments

**Example Tool Card:**
```
┌─────────────────────────────────────────────┐
│ NOTES_CREATE_note                    [▼]    │
│ Create a new note with title and content    │
│                                             │
│ [✓] Enabled in MCP    [○] Passthrough      │
└─────────────────────────────────────────────┘

[Expanded view shows full docstring with examples]
```

---

#### Services Tab Design

**Purpose:** View and control background services for this extension

**Layout:**
- List of services in extension's services/ directory
- Each service as a card showing:
  - Service name
  - Current status (Running/Stopped/Failed/Unhealthy)
  - Port number (if requires_port)
  - Process ID (if running)
  - Uptime (calculated from state.json timestamp)
  - Last health check result
  - Control buttons: Start, Stop, Restart
  - View Logs button (future feature, can stub)

**State Management:**
- Service status from ServicesContext
- Real-time updates every 30 seconds
- Optimistic UI updates when user clicks control buttons

**Control Actions:**
- Start button → POST /api/services/{service_name}/start
- Stop button → POST /api/services/{service_name}/stop
- Restart button → POST /api/services/{service_name}/restart
- All actions call API immediately (not queued)
- Show loading spinner on button while request pending
- Update UI when response received
- Show toast notification on success/error

**Health Status Colors:**
- Green: Running and healthy
- Yellow: Running but health check failing
- Red: Failed (max restarts exceeded)
- Gray: Stopped

**Example Service Card:**
```
┌─────────────────────────────────────────────┐
│ webhook_receiver                            │
│                                             │
│ Status:  ● Running                          │
│ Port:    5300                               │
│ PID:     12845                              │
│ Uptime:  2h 34m                             │
│ Health:  ✓ Last check: 12s ago             │
│                                             │
│ [Stop] [Restart] [View Logs]                │
└─────────────────────────────────────────────┘
```

---

#### About Tab Design

**Purpose:** Display extension metadata and documentation

**Content:**
- Extension name and version
- Author information (if in config)
- Description (from readme or config)
- Source repository link (if github source)
- Required secrets list (from config.json)
  - Visual indicator: set vs not set
  - Link to Secrets page to configure
- Installation date (if tracked)
- Last updated timestamp
- Readme content (rendered markdown)

**Markdown Rendering:**
- Use markdown parser library
- Render readme.md content
- Support headings, lists, code blocks, links
- Syntax highlighting for code
- Sanitize HTML to prevent XSS

**Required Secrets Display:**
```
Required API Keys:
  ✅ OPENAI_API_KEY (configured)
  ❌ NOTION_API_KEY (not set) → [Configure in Secrets]
```

---

### Milestone 2B.3: Three-State Management

#### State Lifecycle Concept

**The Three States:**

**1. originalState (Source of Truth)**
- Loaded from GET /api/config/master on page load
- Never modified during session
- Used for comparison to detect changes
- Reset point when user clicks "Revert All"

**2. currentState (Working Copy)**
- Clone of originalState on load
- All user edits modify currentState
- User toggles extension enabled → updates currentState
- User changes tool config → updates currentState
- User deletes extension → removes from currentState
- User installs extension → adds to currentState

**3. queuedState (Saved for Restart)**
- Contents of update_queue.json
- Loaded from GET /api/queue/current
- Created when user clicks "Save to Queue"
- Represents operations ready to execute on restart
- Can be deleted (revert queue)

**State Relationships:**
```
User makes changes:
  originalState (unchanged)
  currentState (modified) ← user sees this
  queuedState (old queue or null)

User clicks "Save to Queue":
  originalState (unchanged)
  currentState (becomes new baseline)
  queuedState = generated operations ← saved to server

User clicks "Revert All":
  currentState = clone(originalState)
  queuedState (unchanged)

User clicks "Delete Queue":
  originalState (unchanged)
  currentState (unchanged)
  queuedState = null

User clicks "Restart & Apply":
  System restarts with queuedState
  On reload: new originalState reflects applied changes
  currentState = originalState
  queuedState = null (cleared after apply)
```

---

#### Change Detection Algorithm

**How to Detect Changes:**

Compare originalState vs currentState:

**For Extensions:**
- Extension in currentState but not original → INSTALL
- Extension in original but not currentState → DELETE
- Extension in both, but source different → UPDATE
- Extension in both, enabled changed → CONFIG CHANGE (not operation)
- Extension in both, config values changed → CONFIG CHANGE

**For Tools:**
- Tool config different between states → CONFIG CHANGE

**Change Types:**
- INSTALL: New extension to add
- UPDATE: Existing extension source changed
- DELETE: Extension removed
- CONFIG_ONLY: Only configuration changed (no file operations needed)

**Pending Changes Display:**
Show user what will happen when they save to queue:
- "Install notes extension from store"
- "Update automation_memory to latest version"
- "Delete old_weather extension"
- "Enable todos extension"
- "Configure 3 tools"

---

#### Operation Generation

**When User Clicks "Save to Queue":**

**Step 1: Generate Operations Array**
```
operations = []

For each extension in originalState:
  If not in currentState:
    Add {type: "delete", target: extension_name}

For each extension in currentState:
  If not in originalState:
    Add {type: "install", source: extension.source, target: extension_name}
  Else if extension.source != original.source:
    Add {type: "update", source: extension.source, target: extension_name}
  
  (Config changes handled separately in master_config)
```

**Step 2: Package Complete State**
```
queue = {
  operations: [...],
  master_config: currentState  // entire current state
}
```

**Step 3: Save to Server**
```
POST /api/queue/save
Body: queue
```

**Step 4: Update Local State**
```
queuedState = queue
```

This ensures all configuration changes (enabled flags, tool configs) are saved in master_config section of queue, while file operations (install/update/delete) are in operations array.

---

## Phase 2C: Queue Management UI (Week 6)

### Milestone 2C.1: Queue Tab Page

#### Purpose
Central place to review pending changes, save to queue, and trigger system restart.

#### Page Sections

**Section 1: Unsaved Changes**
- Visible when currentState != originalState
- Shows visual diff of what changed
- Grouped by change type:
  - Extensions to install (count)
  - Extensions to update (count)
  - Extensions to delete (count)
  - Configuration changes (count)
- Each item expandable to see details
- Actions:
  - "Save to Queue" button (prominent, primary action)
  - "Revert All Changes" button (secondary, destructive)

**Section 2: Saved Queue**
- Visible when queuedState exists
- Shows contents of update_queue.json
- Lists all operations with details
- Shows when queue was created
- Actions:
  - "Restart & Apply Updates" button (prominent, triggers restart)
  - "Delete Queue" button (secondary, clears queue)
  - View as JSON (expandable for debugging)

**Section 3: Empty States**
- No unsaved changes: "No pending changes"
- No saved queue: "No updates queued"
- Both empty: Encourage user to browse store

---

#### Interaction Flows

**Flow 1: Save Changes to Queue**
1. User has made changes elsewhere (extension manager, tools, etc.)
2. User navigates to Queue tab
3. Sees unsaved changes listed
4. Clicks "Save to Queue"
5. Operation generation happens (see Phase 2B.3)
6. POST /api/queue/save executes
7. Loading indicator during save
8. On success:
   - Toast notification: "Queue saved successfully"
   - queuedState updates
   - Unsaved changes section clears
   - Saved queue section appears
9. On error:
   - Toast notification with error message
   - Retry option

**Flow 2: Revert All Changes**
1. User sees unsaved changes
2. Clicks "Revert All Changes"
3. Confirmation modal: "Discard all pending changes?"
4. User confirms
5. currentState = clone(originalState)
6. All UI throughout app reverts to original
7. Extension toggles reset
8. Tool configs reset
9. Unsaved changes section disappears
10. Toast: "Changes reverted"

**Flow 3: Delete Queue**
1. User has saved queue
2. Wants to clear it without applying
3. Clicks "Delete Queue"
4. Confirmation modal: "Delete queued updates?"
5. User confirms
6. DELETE /api/queue/current executes
7. queuedState = null
8. Saved queue section disappears
9. Toast: "Queue deleted"

**Flow 4: Restart & Apply Updates**
1. User has saved queue
2. Ready to apply changes
3. Clicks "Restart & Apply Updates"
4. Confirmation modal with details:
   - "This will restart Luna"
   - "Estimated time: ~2 minutes"
   - List of what will happen
   - Warning if any services will restart
5. User confirms
6. POST /api/system/restart executes
7. Restart modal appears (see Milestone 2C.2)
8. System begins restart process

---

### Milestone 2C.2: Restart Modal & Monitoring

#### Modal Design

**Full-screen blocking modal** (can't interact with rest of app)

**Phases:**

**Phase 1: Initiating (0-5 seconds)**
- Title: "System Restarting..."
- Message: "Initiating shutdown"
- No progress bar yet
- Spinner animation

**Phase 2: Offline (5-120 seconds)**
- Title: "Applying Updates"
- Progress bar (indeterminate or estimated)
- Status messages:
  - "Stopping services..." (0-10s)
  - "Installing extensions..." (10-60s)
  - "Installing dependencies..." (60-90s)
  - "Restarting services..." (90-120s)
- Estimated time remaining
- Cannot cancel

**Phase 3: Polling for Health (120+ seconds)**
- Title: "Starting Up..."
- Message: "Waiting for system to come online"
- Poll GET /health every 2 seconds
- Show connection attempts count
- Timeout after 5 minutes with error

**Phase 4: Success**
- Health check succeeds
- Brief success message: "System ready!"
- Auto-reload page after 1 second
- Fresh load with new originalState

**Phase 5: Error (if timeout)**
- Title: "Restart Taking Longer Than Expected"
- Message: "System may need manual intervention"
- Actions:
  - "Keep Waiting" (continue polling)
  - "Reload Page" (manual refresh)
  - "View Logs" (future feature)

---

#### Progress Estimation Strategy

**Since we can't directly monitor apply_updates.py progress:**

**Time-based Estimation:**
- Start: 0%
- 10 seconds: 20% (services stopping)
- 30 seconds: 40% (git operations)
- 60 seconds: 60% (installations)
- 90 seconds: 80% (dependencies)
- 120 seconds: 90% (starting services)
- Health check success: 100%

**Better UX with Phases:**
Instead of fake progress bar, show current phase:
- "Stopping services" (with spinner)
- "Downloading extensions" (with spinner)
- "Installing dependencies" (with spinner)
- "Starting services" (with spinner)
- "Performing health checks" (with spinner)

Change phase every ~20-30 seconds based on typical timing.

---

#### Error Handling

**Network Errors During Restart:**
- Health check fails to connect → Expected (system is down)
- Don't show error immediately
- Only show error after timeout (5 minutes)

**Restart Trigger Failure:**
- POST /api/system/restart fails → Show error immediately
- Don't show restart modal
- Allow retry

**Stuck Restart:**
- After 5 minutes, assume something went wrong
- Provide troubleshooting steps
- Suggest checking system manually
- Provide option to force reload

---

## Phase 2D: Extension Store UI (Week 6)

### Milestone 2D.1: Store Page Layout

#### Data Source

**Registry Loading:**
1. Page loads
2. Fetch external registry:
   ```
   GET https://raw.githubusercontent.com/luna-extensions/luna-extensions/main/registry.json
   ```
3. Parse registry
4. Store in local state
5. Use for filtering and display

**Registry Structure Reminder:**
```
{
  "version": "10-17-25",
  "extensions": [
    {
      "id": "notes",
      "name": "Notes",
      "type": "embedded|external",
      "path": "embedded/notes" (if embedded),
      "source": "github:user/repo" (if external),
      "version": "10-17-25",
      "description": "...",
      "author": "...",
      "category": "productivity",
      "has_ui": true|false,
      "tool_count": 3,
      "service_count": 0,
      "required_secrets": ["..."],
      "tags": ["..."]
    }
  ],
  "categories": [...]
}
```

---

#### Page Components

**Header Section:**
- Title: "Extension Store"
- Search bar (filters by name, description, tags)
- Filter dropdown:
  - All Categories
  - Productivity
  - Development
  - Communication
  - Automation
  - etc.
- Additional filters (checkboxes):
  - Has UI
  - No external dependencies
  - Free (no API keys required)

**Grid Section:**
- Grid layout (3-4 columns on desktop, 1-2 on tablet, 1 on mobile)
- Extension cards with store-specific info
- Lazy loading (if many extensions)
- Smooth scroll

**Extension Card Design (Store Version):**
```
┌──────────────────────────────┐
│ 📝 Notes        v10-17-25    │
│ by Luna Team                 │
│                              │
│ Simple note-taking with      │
│ tags and search              │
│                              │
│ 3 tools • No UI              │
│ Productivity                 │
│                              │
│ Requires:                    │
│ • OPENAI_API_KEY             │
│                              │
│ [Install] or [✓ Installed]   │
└──────────────────────────────┘
```

**Install Status Indicators:**
- Not installed: "Install" button (primary action)
- Installed: "✓ Installed" (grayed out, no action)
- Installed, update available: "Update Available" (primary action)

---

#### Search and Filter Logic

**Search Algorithm:**
1. User types in search box
2. Debounce input (300ms delay)
3. Filter extensions where:
   - Name includes search term (case-insensitive)
   - OR description includes search term
   - OR any tag includes search term
4. Update displayed cards
5. Show "X results" count

**Category Filter:**
- Dropdown or button group
- Select category → filter extensions.category == selected
- "All Categories" shows everything
- Combine with search (AND logic)

**Additional Filters:**
- Each checkbox filter is independent
- All active filters combined with AND
- Example: "Has UI" AND "Productivity" AND search:"notes"

**No Results State:**
- Show friendly message: "No extensions found"
- Suggest: "Try different search terms" or "Browse all categories"
- Link to request new extension (future: community forum)

---

### Milestone 2D.2: Extension Detail Modal

#### Trigger
User clicks extension card → Modal opens with full details

#### Modal Content

**Header:**
- Extension name and icon
- Version number
- Author
- Category badge
- Close button

**Tabs (within modal):**

**Overview Tab:**
- Full description (markdown rendered)
- Screenshots (if available in registry)
- Feature list
- Links to repository, documentation, demo

**Requirements Tab:**
- Required secrets (with check marks if already configured)
- System requirements (future: min Luna version)
- Dependencies (other extensions, if any)
- Installation size estimate

**Tools Tab:**
- List of tools this extension provides
- Each tool with description
- Preview of tool capabilities
- MCP compatibility indicator

**Services Tab:**
- List of background services (if any)
- What each service does
- Port requirements

**Footer:**
- "Install" button (primary)
- "View Source" button (links to GitHub)
- "Cancel" button (closes modal)

---

#### Install Flow from Store

**User Clicks "Install" Button:**

1. **Pre-check:**
   - Check if extension already exists in currentState
   - If exists with different source → This is UPDATE
   - If exists with same source → Already installed, disable button
   - If not exists → This is INSTALL

2. **Generate Source String:**
   - If type: "embedded" → `github:luna-extensions/luna-extensions:embedded/{path}`
   - If type: "external" → Use registry `source` field directly

3. **Add to CurrentState:**
   ```
   currentState.extensions[extension_id] = {
     enabled: true,
     source: generated_source,
     config: {} // Empty config, will populate on install
   }
   ```

4. **UI Feedback:**
   - Button changes to "✓ Added to Queue"
   - Toast notification: "Added {name} to pending changes"
   - Pending changes counter increments
   - Modal stays open (user might want to read more)

5. **User Must Save:**
   - Extension not actually installed yet
   - Just added to currentState
   - User must go to Queue tab
   - Click "Save to Queue"
   - Then "Restart & Apply" to actually install

**This Prevents Accidental Installs:**
- User can browse store, add multiple extensions
- Review all additions in Queue tab
- Apply all at once with single restart

---

#### Update Detection

**Show "Update Available" Badge:**

1. Check if extension installed (exists in originalState)
2. Compare versions:
   - Installed version from extension's config.json
   - Available version from registry
3. If available > installed → Show update badge
4. If user clicks "Update":
   - Add UPDATE operation to currentState
   - Change source to new version's source
   - Rest of flow same as install

**Version Comparison:**
- Parse MM-DD-YY format
- Convert to comparable numbers
- Later date = higher version
- Simple string comparison works for same year

---

## Phase 2E: Key Manager UI (Week 6)

### Milestone 2E.1: Secrets Page Layout

#### Purpose
Manage API keys and secrets without restart, see what each extension needs.

#### Page Structure

**Section 1: Upload .env File**
- File input (styled as button)
- Drag-and-drop zone (optional enhancement)
- Upload button
- Help text: "Upload .env file to merge with existing secrets. No restart required."

**Section 2: Required by Extensions**
- Grouped by extension
- Each extension as collapsible section
- Shows required_secrets from config.json
- Visual indicator: set (green checkmark) or missing (red X)
- Inline edit for each secret

**Section 3: Custom Secrets**
- List of secrets not required by any extension
- User-added keys
- Each with edit/delete actions

**Section 4: Add New Secret**
- Form: key + value inputs
- Add button
- Validates key format (uppercase, underscores only)

---

#### Components Design

**Extension Secret Group:**
```
┌─────────────────────────────────────┐
│ 📝 notes                       [▼]  │
├─────────────────────────────────────┤
│ ✅ OPENAI_API_KEY                   │
│    sk-proj-...abc123      [Edit]   │
│                                     │
│ ❌ NOTION_API_KEY (not set)        │
│    [Add Secret]                     │
└─────────────────────────────────────┘
```

**Secret Row (Set):**
- Key name (bold)
- Value (masked: `sk-proj-...abc123` - show first few, last few chars)
- Edit button → Opens edit modal
- Delete button (for custom secrets only)

**Secret Row (Not Set):**
- Key name (bold)
- "(not set)" text in red/warning color
- "Add Secret" button → Opens add modal

---

#### Upload .env Flow

**User Selects File:**
1. Click "Choose File" or drag file to drop zone
2. File selected (validate: must be .env or .txt)
3. "Upload & Merge" button becomes enabled
4. User clicks upload

**Processing:**
1. Read file contents (FileReader API in browser)
2. Parse key=value lines
3. POST /api/keys/upload-env with multipart/form-data
4. Server merges with existing .env
5. Server returns: `{updated_count: 5}`
6. Frontend refreshes secret list
7. Toast: "{count} secrets updated"
8. Visual indicators update (checkmarks appear)

**Security Note:**
- File never sent as plain text over network if local
- Use HTTPS in production
- Warn user if uploading over HTTP

---

#### Add/Edit Secret Flow

**Add Secret Modal:**
1. User clicks "Add Secret" for missing key or "+ Add Custom Secret"
2. Modal opens with form:
   - Key input (if custom) or pre-filled (if from extension)
   - Value input (password field with show/hide toggle)
   - Optional description field
3. User enters value
4. Clicks "Save"
5. POST /api/keys/set with `{key, value}`
6. Server updates .env file
7. Server hot reloads environment
8. Modal closes
9. UI updates immediately (checkmark appears)
10. Toast: "Secret added successfully"

**Edit Secret Modal:**
1. User clicks "Edit" on existing secret
2. Modal opens with current value (masked or shown)
3. User can change value
4. Same save flow as add
5. Toast: "Secret updated successfully"

**Delete Secret Flow:**
1. User clicks "Delete" on custom secret
2. Confirmation dialog: "Delete {KEY_NAME}?"
3. User confirms
4. POST /api/keys/delete with `{key}`
5. Server removes from .env
6. Secret row disappears
7. Toast: "Secret deleted"

---

#### Required Secrets Check

**Loading Required Secrets:**
1. Page loads
2. GET /api/config/master to get all extensions
3. For each extension, read `required_secrets` array from config
4. Aggregate unique set of all required secrets
5. GET /api/keys/required (or parse .env locally if API provides it)
6. For each required secret:
   - If exists in .env → Mark as set ✅
   - If missing → Mark as not set ❌

**Auto-Grouping:**
- Group secrets by which extensions need them
- If secret needed by multiple extensions, list it under each
- Show count: "Required by 3 extensions"

**Visual Hierarchy:**
```
Extension Name
  ✅ SECRET_ONE (set)
  ❌ SECRET_TWO (not set) ← draws attention
  ✅ SECRET_THREE (set)
```

User can immediately see what's missing.

---

#### Hot Reload Explanation

**Why No Restart Needed:**
- When secret added/updated, server calls `load_dotenv(override=True)`
- Updates process environment variables
- Services that read secrets on-demand get new values immediately
- Services that cache secrets at startup need manual restart (edge case)

**UI Messaging:**
- After secret update, show info tooltip:
  - "Updated successfully. Most services will use new value immediately."
  - "If service doesn't recognize change, restart it from the Services tab."

**Future Enhancement:**
- After secret update, show which services might need restart
- Offer "Restart Affected Services" button

---

## Phase 2F: Extension UI Aggregation (Week 7)

### Milestone 2F.1: Dynamic Navigation

#### Concept

**Extension UIs in Sidebar:**
- After static navigation items, show divider
- Below divider, list enabled extensions that have UIs
- Each extension as sidebar item with icon + name
- Clicking navigates to `/ext/{extension_name}`

**Determining Which Extensions Have UIs:**
1. Load master config
2. For each enabled extension
3. Check if extension has `ui/` directory
4. Can detect by:
   - API endpoint: GET /api/extensions/{name}/has-ui
   - Or check port_assignments.extensions (if extension has UI port, it has UI)
5. If has UI, add to sidebar

**Sidebar Example:**
```
🏠 Dashboard
📦 Extensions
📋 Queue
🏪 Store
🔑 Secrets
───────────────
📝 Notes          ← Extension UIs
✅ Todos          ← (dynamic)
🔄 GitHub Sync    ←
```

---

#### Active Route Highlighting

**Current page highlighting:**
- Check current URL
- If URL is /ext/notes → Highlight "Notes" in sidebar
- If URL is /extensions → Highlight "Extensions"
- Visual: Background color change, bold text, left border indicator

**Sub-routes:**
- /extensions/notes is still under "Extensions" parent
- Highlight "Extensions" in sidebar
- Optionally show breadcrumb in main content

---

### Milestone 2F.2: Extension UI IFrame Integration

#### Route Setup

**Pattern:** `/ext/:name`

**Component:** ExtensionFrame page component

**Responsibilities:**
1. Extract extension name from URL
2. Look up extension's assigned port from ConfigContext or GET /ports
3. Render iframe with `src=http://127.0.0.1:{port}`
4. Handle iframe loading states
5. Handle iframe errors

---

#### IFrame Component Design

**Basic Structure:**
```
<div style="width: 100%, height: 100vh">
  <iframe
    src={`http://127.0.0.1:${port}`}
    style="width: 100%, height: 100%, border: none"
    sandbox="allow-same-origin allow-scripts allow-forms"
    title={extensionName}
  />
</div>
```

**Security Considerations:**
- Use `sandbox` attribute for basic isolation
- Extensions run on different ports (already isolated)
- Same origin (127.0.0.1) so can communicate if needed
- HTTPS not needed for localhost in MVP

**Loading State:**
1. Show loading spinner while iframe loads
2. Listen for iframe `load` event
3. Hide spinner, show iframe
4. Timeout after 10 seconds if not loaded

**Error Handling:**
1. Listen for iframe `error` event
2. Also use timeout (if load never fires)
3. Show friendly error:
   - "Failed to load {extension} UI"
   - "Extension may not be running"
   - "Check extension status in Services tab"
   - "Try restarting the service"
4. Button: "Go to Services" → Navigate to extension detail services tab

---

#### Communication Between Hub and Extension UIs (Optional)

**PostMessage API:**
- Hub can send messages to extension iframe
- Extension can send messages back
- Use for:
  - Passing auth tokens (future)
  - Notifying of theme changes
  - Coordinating actions

**Example:**
```javascript
// Hub sends theme to extension
extensionIframe.contentWindow.postMessage(
  { type: 'THEME_CHANGE', theme: 'dark' },
  'http://127.0.0.1:5200'
)

// Extension receives
window.addEventListener('message', (event) => {
  if (event.data.type === 'THEME_CHANGE') {
    applyTheme(event.data.theme)
  }
})
```

**Not Required for MVP**, but good to design iframe wrapper to support it.

---

#### Height Management

**Challenge:** Extension UIs might have different content heights

**Solutions:**

**Option 1: Full Height (Recommended for MVP)**
- Iframe always 100vh (full viewport height)
- Extension UI handles its own scrolling
- Simple, no coordination needed

**Option 2: Dynamic Height (Future Enhancement)**
- Extension reports its content height via postMessage
- Hub resizes iframe accordingly
- More complex, better UX

For MVP, use Option 1.

---

#### Multiple Extension UIs Open

**Tab Behavior:**
- Each extension UI is separate route
- User can open in new tab (if they copy URL)
- Browser back/forward works normally
- No special multi-window coordination needed

**State:**
- Each extension UI manages its own state
- Hub doesn't share state with extension UIs
- Extensions use their own APIs/storage

---

## Phase 2G: System Dashboard (Week 7)

### Milestone 2G.1: Dashboard Page

#### Purpose
Landing page that gives overview of system health and quick access to common actions.

#### Layout Sections

**Section 1: System Status Cards**

Three cards in a row (responsive: stack on mobile):

**Card 1: Core Services**
- Title: "Core Services"
- List:
  - Hub UI (status + port)
  - Agent API (status + port)
  - MCP Server (status + port)
- Visual: Green/yellow/red indicators
- All running = green card border
- Any unhealthy = yellow card border

**Card 2: Extension Services**
- Title: "Extension Services"
- Count: "X running, Y stopped, Z failed"
- Visual status indicators
- Button: "View All" → Navigate to service list

**Card 3: Extensions**
- Title: "Extensions"
- Count: "X installed, Y enabled"
- Button: "Manage" → Navigate to extensions page

---

**Section 2: Quick Actions**

Grid of action buttons (2x2 on desktop, 2x1 on tablet, 1x1 on mobile):

- **Browse Store** → Navigate to /store
- **Check for Updates** → Trigger update check (future feature, or just link to Queue)
- **Manage Secrets** → Navigate to /secrets
- **View Logs** → Future feature, can stub or link to external logs

Each button:
- Icon
- Label
- Optional badge (e.g., "3 updates" on Check Updates)

---

**Section 3: Recent Activity**

Timeline or list of recent events:
- Extension installed
- Extension updated
- System restarted
- Configuration changed
- Service restarted

**Data Source:**
- Store activity in localStorage or
- Backend API endpoint (future: GET /api/activity)
- For MVP, can track in frontend only

**Event Examples:**
```
● Installed "notes" extension        2m ago
● Updated automation_memory          1h ago
● System restart completed           3h ago
● Added OPENAI_API_KEY secret       5h ago
```

Limit to last 10 events.

---

**Section 4: System Information**

Small info panel:
- Luna version
- Uptime (calculate from state.json)
- Total extensions
- Total tools available
- Port assignments count

---

#### Health Check Visual Design

**Overall Health Indicator:**
- Calculate from all services
- All healthy → Green: "All Systems Operational"
- Some unhealthy → Yellow: "Degraded Performance"
- Critical failure → Red: "System Issues Detected"

**Health Badge in Header:**
- Persistent across all pages
- Small colored dot + text
- Matches overall health
- Clickable → Dropdown showing quick status

---

### Milestone 2G.2: Real-time Updates

#### Polling Strategy

**What to Poll:**
1. System health (every 10 seconds)
2. Service statuses (every 30 seconds)
3. Extension statuses (only when on relevant pages)

**Implementation:**
- Use `setInterval` in context providers
- Only poll when app is active (use Page Visibility API)
- Stop polling when user leaves page
- Resume when user returns

**Optimizations:**
- Combine multiple API calls into single endpoint if backend supports
- Use WebSocket in future for real-time updates (not MVP)
- Cache results, only update on change

---

#### Status Change Notifications

**When Service Status Changes:**
1. Polling detects change (e.g., service went from running to failed)
2. Update ServicesContext
3. Components re-render with new status
4. Show toast notification:
   - "⚠️ webhook_receiver service has stopped"
   - Action button: "Restart" (inline action)

**When Extension Installed (During Queue Processing):**
1. After restart completes
2. Page reloads
3. Show welcome notification:
   - "✅ Successfully installed 2 extensions"
   - List installed extensions
   - Button: "View Extensions"

---

## Testing Strategy for Phase 2

### Manual Testing Approach

Since UI automated testing is complex and not required for MVP, use structured manual testing:

#### Test Checklist Per Milestone

**For Each Page:**
- [ ] Page loads without errors
- [ ] All data displays correctly
- [ ] Loading states work
- [ ] Error states display properly
- [ ] Actions trigger correct API calls
- [ ] Navigation works
- [ ] Responsive on mobile
- [ ] Browser back/forward works

**For Each Form:**
- [ ] All fields editable
- [ ] Validation works
- [ ] Submit triggers API
- [ ] Success shows feedback
- [ ] Errors show messages
- [ ] Can cancel/reset

**For Each Modal:**
- [ ] Opens correctly
- [ ] Closes correctly
- [ ] Backdrop click closes
- [ ] ESC key closes
- [ ] Form submission works
- [ ] Cannot interact with background

-

VISAULIZTOIN
# Hub UI Page Visualizations

---

## 1. Dashboard (Home Page)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  🌙 Luna                                                    [●] Healthy  v10-17-25 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Sidebar ──────┐  ┌─ Main Content ────────────────────────────────────┐  │
│  │                │  │                                                     │  │
│  │ 🏠 Dashboard   │  │  System Status                                      │  │
│  │ 📦 Extensions  │  │  ┌──────────────────────────────────────────────┐  │  │
│  │ 📋 Queue       │  │  │  Core Services                    ●●●         │  │  │
│  │ 🏪 Store       │  │  │  ─────────────────────────────────────────   │  │  │
│  │ 🔑 Secrets     │  │  │  ● Hub UI             Running    :5173       │  │  │
│  │                │  │  │  ● Agent API          Running    :8080       │  │  │
│  │ ───────────    │  │  │  ● MCP Server         Running    :8765       │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │ Extensions     │  │                                                     │  │
│  │ ─────────      │  │  ┌──────────────────────────────────────────────┐  │  │
│  │ 📝 Notes       │  │  │  Extension Services               ●●○         │  │  │
│  │ ✅ Todos       │  │  │  ─────────────────────────────────────────   │  │  │
│  │ 🔄 GitHub      │  │  │  ● automation_memory.worker    Running :5300 │  │  │
│  │                │  │  │  ● github_sync.webhook         Running :5301 │  │  │
│  │                │  │  │  ○ email_processor.queue       Stopped       │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  Quick Actions                                      │  │
│  │                │  │  ┌─────────────────┐  ┌─────────────────┐         │  │
│  │                │  │  │ 📦 Browse Store │  │ 🔄 Check Updates│         │  │
│  │                │  │  └─────────────────┘  └─────────────────┘         │  │
│  │                │  │  ┌─────────────────┐  ┌─────────────────┐         │  │
│  │                │  │  │ 🔑 Manage Keys  │  │ 📊 View Logs    │         │  │
│  │                │  │  └─────────────────┘  └─────────────────┘         │  │
│  │                │  │                                                     │  │
│  │                │  │  Recent Activity                                    │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │  • Installed "notes" extension     2m ago    │  │  │
│  │                │  │  │  • Updated automation_memory       1h ago    │  │  │
│  │                │  │  │  • System restart completed        3h ago    │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  └────────────────┘  └─────────────────────────────────────────────────┘  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Extension Manager - List View

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  🌙 Luna                                                    [●] Healthy  v10-17-25 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Sidebar ──────┐  ┌─ Extensions ──────────────────────────────────────┐  │
│  │                │  │                                                     │  │
│  │ 🏠 Dashboard   │  │  My Extensions                    [+ Upload]       │  │
│  │ 📦 Extensions  │  │  ─────────────────────────────────────────────     │  │
│  │ 📋 Queue       │  │                                                     │  │
│  │ 🏪 Store       │  │  ┌──────────────────────┐  ┌───────────────────┐  │  │
│  │ 🔑 Secrets     │  │  │ 📝 Notes  v10-17-25  │  │ ✅ Todos v10-15-25│  │  │
│  │                │  │  │ ● Running       [◉] │  │ ● Running     [◉] │  │  │
│  │                │  │  │ 3 tools             │  │ 5 tools           │  │  │
│  │                │  │  │ No services         │  │ 1 service         │  │  │
│  │                │  │  │                     │  │                   │  │  │
│  │                │  │  │ [Details] [Delete]  │  │ [Details] [Delete]│  │  │
│  │                │  │  └──────────────────────┘  └───────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────┐  ┌───────────────────┐  │  │
│  │                │  │  │ 🔄 GitHub Sync       │  │ 🤖 Automation     │  │  │
│  │                │  │  │    v10-12-25         │  │    Memory         │  │  │
│  │                │  │  │ ● Running       [◉] │  │    v10-17-25      │  │  │
│  │                │  │  │ 12 tools            │  │ ● Running     [◉] │  │  │
│  │                │  │  │ 1 service           │  │ 8 tools           │  │  │
│  │                │  │  │                     │  │ 1 service         │  │  │
│  │                │  │  │ [Details] [Delete]  │  │ [Details] [Delete]│  │  │
│  │                │  │  └──────────────────────┘  └───────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────┐                          │  │
│  │                │  │  │ 🌤️  Weather          │                          │  │
│  │                │  │  │    v10-10-25         │                          │  │
│  │                │  │  │ ○ Stopped       [○] │  (Disabled)              │  │
│  │                │  │  │ 2 tools             │                          │  │
│  │                │  │  │ No services         │                          │  │
│  │                │  │  │                     │                          │  │
│  │                │  │  │ [Details] [Delete]  │                          │  │
│  │                │  │  └──────────────────────┘                          │  │
│  │                │  │                                                     │  │
│  └────────────────┘  └─────────────────────────────────────────────────┘  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Extension Manager - Detail View (Tools Tab)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  🌙 Luna                                                    [●] Healthy  v10-17-25 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Sidebar ──────┐  ┌─ Notes Extension ─────────────────────────────────┐  │
│  │                │  │                                                     │  │
│  │ 🏠 Dashboard   │  │  ← Back to Extensions                              │  │
│  │ 📦 Extensions  │  │                                                     │  │
│  │ 📋 Queue       │  │  📝 Notes                    v10-17-25    [◉] Enabled │  │
│  │ 🏪 Store       │  │  ● Running                                          │  │
│  │ 🔑 Secrets     │  │                                                     │  │
│  │                │  │  ┌─────────────────────────────────────────────┐   │  │
│  │                │  │  │ [Tools] Services  About                     │   │  │
│  │                │  │  └─────────────────────────────────────────────┘   │  │
│  │                │  │                                                     │  │
│  │                │  │  Tools Configuration                                │  │
│  │                │  │  ───────────────────────────────────────────        │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ NOTES_CREATE_note                            │  │  │
│  │                │  │  │ Create a new note with title and content     │  │  │
│  │                │  │  │                                              │  │  │
│  │                │  │  │ [✓] Enabled in MCP    [○] Passthrough        │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ NOTES_UPDATE_note                            │  │  │
│  │                │  │  │ Update an existing note's content            │  │  │
│  │                │  │  │                                              │  │  │
│  │                │  │  │ [✓] Enabled in MCP    [✓] Passthrough        │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ NOTES_DELETE_note                            │  │  │
│  │                │  │  │ Delete a note by ID                          │  │  │
│  │                │  │  │                                              │  │  │
│  │                │  │  │ [○] Enabled in MCP    [○] Passthrough        │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │                            [Save Changes]          │  │
│  │                │  │                                                     │  │
│  └────────────────┘  └─────────────────────────────────────────────────┘  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Extension Manager - Services Tab

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  🌙 Luna                                                    [●] Healthy  v10-17-25 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Sidebar ──────┐  ┌─ GitHub Sync Extension ───────────────────────────┐  │
│  │                │  │                                                     │  │
│  │ 🏠 Dashboard   │  │  ← Back to Extensions                              │  │
│  │ 📦 Extensions  │  │                                                     │  │
│  │ 📋 Queue       │  │  🔄 GitHub Sync             v10-12-25    [◉] Enabled │  │
│  │ 🏪 Store       │  │  ● Running                                          │  │
│  │ 🔑 Secrets     │  │                                                     │  │
│  │                │  │  ┌─────────────────────────────────────────────┐   │  │
│  │                │  │  │ Tools  [Services]  About                    │   │  │
│  │                │  │  └─────────────────────────────────────────────┘   │  │
│  │                │  │                                                     │  │
│  │                │  │  Background Services                                │  │
│  │                │  │  ───────────────────────────────────────────        │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ webhook_receiver                             │  │  │
│  │                │  │  │                                              │  │  │
│  │                │  │  │ Status:  ● Running                           │  │  │
│  │                │  │  │ Port:    5300                                │  │  │
│  │                │  │  │ PID:     12845                               │  │  │
│  │                │  │  │ Uptime:  2h 34m                              │  │  │
│  │                │  │  │ Health:  ✓ Last check: 12s ago              │  │  │
│  │                │  │  │                                              │  │  │
│  │                │  │  │ [Stop] [Restart] [View Logs]                 │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ sync_worker                                  │  │  │
│  │                │  │  │                                              │  │  │
│  │                │  │  │ Status:  ○ Stopped                           │  │  │
│  │                │  │  │ Port:    None (background worker)            │  │  │
│  │                │  │  │ PID:     -                                   │  │  │
│  │                │  │  │ Uptime:  -                                   │  │  │
│  │                │  │  │ Health:  -                                   │  │  │
│  │                │  │  │                                              │  │  │
│  │                │  │  │ [Start] [View Logs]                          │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  └────────────────┘  └─────────────────────────────────────────────────┘  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Queue Management

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  🌙 Luna                                                    [●] Healthy  v10-17-25 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Sidebar ──────┐  ┌─ Update Queue ───────────────────────────────────┐  │
│  │                │  │                                                     │  │
│  │ 🏠 Dashboard   │  │  Pending Changes                      ⚠️  3 pending │  │
│  │ 📦 Extensions  │  │  ─────────────────────────────────────────────     │  │
│  │ 📋 Queue       │  │                                                     │  │
│  │ 🏪 Store       │  │  You have unsaved changes:                          │  │
│  │ 🔑 Secrets     │  │                                                     │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ ➕ Install Extension                          │  │  │
│  │                │  │  │    notes (from store)                        │  │  │
│  │                │  │  │    Source: github:luna/luna-ext:embedded/notes  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ 🔄 Update Extension                           │  │  │
│  │                │  │  │    automation_memory                         │  │  │
│  │                │  │  │    Current: v10-15-25 → Latest: v10-17-25    │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ 🗑️  Delete Extension                          │  │  │
│  │                │  │  │    old_weather_extension                     │  │  │
│  │                │  │  │    (No longer needed)                        │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  Actions                                            │  │
│  │                │  │  ┌─────────────────────┐  ┌──────────────────┐    │  │
│  │                │  │  │  Save to Queue      │  │  Revert All      │    │  │
│  │                │  │  └─────────────────────┘  └──────────────────┘    │  │
│  │                │  │                                                     │  │
│  │                │  │  ─────────────────────────────────────────────     │  │
│  │                │  │                                                     │  │
│  │                │  │  Saved Queue                            ✓ Saved    │  │
│  │                │  │  ─────────────────────────────────────────────     │  │
│  │                │  │                                                     │  │
│  │                │  │  3 operations ready to apply on next restart        │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ [🔄 Restart & Apply Updates]                 │  │  │
│  │                │  │  │                                              │  │  │
│  │                │  │  │  This will restart Luna and apply all        │  │  │
│  │                │  │  │  queued changes. Estimated time: ~2 minutes  │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  [Delete Queue]                                     │  │
│  │                │  │                                                     │  │
│  └────────────────┘  └─────────────────────────────────────────────────┘  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Extension Store

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  🌙 Luna                                                    [●] Healthy  v10-17-25 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Sidebar ──────┐  ┌─ Extension Store ─────────────────────────────────┐  │
│  │                │  │                                                     │  │
│  │ 🏠 Dashboard   │  │  Browse Extensions                                  │  │
│  │ 📦 Extensions  │  │                                                     │  │
│  │ 📋 Queue       │  │  ┌───────────────────────────────────────────────┐ │  │
│  │ 🏪 Store       │  │  │ 🔍 Search extensions...          [🔽 Filter] │ │  │
│  │ 🔑 Secrets     │  │  └───────────────────────────────────────────────┘ │  │
│  │                │  │                                                     │  │
│  │                │  │  Categories: [All] Productivity  Development       │  │
│  │                │  │              Communication  Automation             │  │
│  │                │  │  ─────────────────────────────────────────────     │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────┐  ┌───────────────────┐  │  │
│  │                │  │  │ 📝 Notes  v10-17-25  │  │ ✅ Tasks v10-16-25│  │  │
│  │                │  │  │ Simple note-taking   │  │ Task management   │  │  │
│  │                │  │  │ with tags & search   │  │ with priorities   │  │  │
│  │                │  │  │                     │  │                   │  │  │
│  │                │  │  │ 3 tools • No UI     │  │ 5 tools • UI      │  │  │
│  │                │  │  │ Productivity        │  │ Productivity      │  │  │
│  │                │  │  │                     │  │                   │  │  │
│  │                │  │  │ Requires:           │  │ Requires:         │  │  │
│  │                │  │  │ • OPENAI_API_KEY    │  │ • None            │  │  │
│  │                │  │  │                     │  │                   │  │  │
│  │                │  │  │     [Install]       │  │  [✓ Installed]    │  │  │
│  │                │  │  └──────────────────────┘  └───────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────┐  ┌───────────────────┐  │  │
│  │                │  │  │ 🔄 GitHub Sync       │  │ 📧 Email          │  │  │
│  │                │  │  │    v10-15-25         │  │    Processor      │  │  │
│  │                │  │  │ Sync GitHub issues,  │  │    v10-14-25      │  │  │
│  │                │  │  │ PRs, and repos       │  │ Process emails    │  │  │
│  │                │  │  │                     │  │ with AI           │  │  │
│  │                │  │  │ 12 tools • UI       │  │ 6 tools • Service │  │  │
│  │                │  │  │ 1 service           │  │ Development       │  │  │
│  │                │  │  │ Development         │  │                   │  │  │
│  │                │  │  │                     │  │ Requires:         │  │  │
│  │                │  │  │ Requires:           │  │ • EMAIL_HOST      │  │  │
│  │                │  │  │ • GITHUB_TOKEN      │  │ • EMAIL_PASSWORD  │  │  │
│  │                │  │  │ • GITHUB_WEBHOOK    │  │                   │  │  │
│  │                │  │  │                     │  │                   │  │  │
│  │                │  │  │  [✓ Installed]      │  │     [Install]     │  │  │
│  │                │  │  └──────────────────────┘  └───────────────────┘  │  │
│  │                │  │                                                     │  │
│  └────────────────┘  └─────────────────────────────────────────────────┘  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Key Manager (Secrets)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  🌙 Luna                                                    [●] Healthy  v10-17-25 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Sidebar ──────┐  ┌─ Secret Management ───────────────────────────────┐  │
│  │                │  │                                                     │  │
│  │ 🏠 Dashboard   │  │  API Keys & Secrets                                 │  │
│  │ 📦 Extensions  │  │  ─────────────────────────────────────────────     │  │
│  │ 📋 Queue       │  │                                                     │  │
│  │ 🏪 Store       │  │  Upload .env File                                   │  │
│  │ 🔑 Secrets     │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ [Choose File]  [Upload & Merge]              │  │  │
│  │                │  │  │                                              │  │  │
│  │                │  │  │ Upload a .env file to merge with existing    │  │  │
│  │                │  │  │ secrets. No restart required.                │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  Required by Extensions                             │  │
│  │                │  │  ───────────────────────────────────────────        │  │
│  │                │  │                                                     │  │
│  │                │  │  📝 notes                                            │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ ✅ OPENAI_API_KEY                            │  │  │
│  │                │  │  │    sk-proj-...abc123              [Edit]    │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  🔄 github_sync                                      │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ ✅ GITHUB_TOKEN                              │  │  │
│  │                │  │  │    ghp_...xyz789                  [Edit]    │  │  │
│  │                │  │  │                                              │  │  │
│  │                │  │  │ ❌ GITHUB_WEBHOOK_SECRET (not set)  [Add]   │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  🤖 automation_memory                                │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ ✅ DATABASE_URL                              │  │  │
│  │                │  │  │    postgresql://...               [Edit]    │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  Custom Secrets                                     │  │
│  │                │  │  ───────────────────────────────────────────        │  │
│  │                │  │                                                     │  │
│  │                │  │  ┌──────────────────────────────────────────────┐  │  │
│  │                │  │  │ ✅ MY_CUSTOM_API_KEY                         │  │  │
│  │                │  │  │    abc...123                 [Edit] [Delete] │  │  │
│  │                │  │  └──────────────────────────────────────────────┘  │  │
│  │                │  │                                                     │  │
│  │                │  │  [+ Add Custom Secret]                              │  │
│  │                │  │                                                     │  │
│  └────────────────┘  └─────────────────────────────────────────────────┘  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Extension UI (iframed)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  🌙 Luna                                                    [●] Healthy  v10-17-25 │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─ Sidebar ──────┐  ┌─ Notes Extension UI ──────────────────────────────┐  │
│  │                │  │ ┌────────────────────────────────────────────────┐ │  │
│  │ 🏠 Dashboard   │  │ │  http://127.0.0.1:5200                         │ │  │
│  │ 📦 Extensions  │  │ └────────────────────────────────────────────────┘ │  │
│  │ 📋 Queue       │  │ ┌────────────────────────────────────────────────┐ │  │
│  │ 🏪 Store       │  │ │                                                │ │  │
│  │ 🔑 Secrets     │  │ │  📝 My Notes                     [+ New Note]  │ │  │
│  │                │  │ │  ───────────────────────────────────────────   │ │  │
│  │ ───────────    │  │ │                                                │ │  │
│  │                │  │ │  ┌──────────────────────────────────────────┐ │ │  │
│  │ Extensions     │  │ │  │ 💡 Project Ideas           📅 Today       │ │ │  │
│  │ ─────────      │  │ │  │                                          │ │ │  │
│  │ 📝 Notes       │  │ │  │ - Build Luna extension store           │ │ │  │
│  │ ✅ Todos       │  │ │  │ - Add authentication system             │ │ │  │
│  │ 🔄 GitHub      │  │ │  │ - Create mobile app                     │ │ │  │
│  │                │  │ │  │                                          │ │ │  │
│  │                │  │ │  │ #ideas #planning                         │ │ │  │
│  │                │  │ │  └──────────────────────────────────────────┘ │ │  │
│  │                │  │ │                                                │ │  │
│  │                │  │ │  ┌──────────────────────────────────────────┐ │ │  │
│  │                │  │ │  │ 🛒 Shopping List        📅 Yesterday    │ │ │  │
│  │                │  │ │  │                                          │ │ │  │
│  │                │  │ │  │ - Milk                                   │ │ │  │
│  │                │  │ │  │ - Eggs                                   │ │ │  │
│  │                │  │ │  │ - Bread                                  │ │ │  │
│  │                │  │ │  │                                          │ │ │  │
│  │                │  │ │  │ #personal #shopping                      │ │ │  │
│  │                │  │ │  └──────────────────────────────────────────┘ │ │  │
│  │                │  │ │                                                │ │  │
│  │                │  │ │  ┌──────────────────────────────────────────┐ │ │  │
│  │                │  │ │  │ 📚 Reading List         📅 Oct 15        │ │ │  │
│  │                │  │ │  │                                          │ │ │  │
│  │                │  │ │  │ - The Pragmatic Programmer              │ │ │  │
│  │                │  │ │  │ - Clean Code                            │ │ │  │
│  │                │  │ │  │                                          │ │ │  │
│  │                │  │ │  │ #books #development                      │ │ │  │
│  │                │  │ │  └──────────────────────────────────────────┘ │ │  │
│  │                │  │ │                                                │ │  │
│  │                │  │ │                                                │ │  │
│  │                │  │ │  (This is the extension's own UI, running     │ │  │
│  │                │  │ │   on port 5200, displayed in an iframe)       │ │  │
│  │                │  │ │                                                │ │  │
│  │                │  │ └────────────────────────────────────────────────┘ │  │
│  └────────────────┘  └─────────────────────────────────────────────────┘  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Restart Modal (During Updates)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  🌙 Luna                                                    [○] Restarting...     │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│                                                                                │
│                                                                                │
│                      ┌───────────────────────────────────┐                    │
│                      │                                   │                    │
│                      │  🔄 System Restarting             │                    │
│                      │                                   │                    │
│                      │  Applying updates...              │                    │
│                      │                                   │                    │
│                      │  ● Stopping services              │                    │
│                      │  ● Installing extensions          │                    │
│                      │  ○ Installing dependencies        │                    │
│                      │  ○ Restarting system              │                    │
│                      │                                   │                    │
│                      │  [████████░░░░░░░░░░] 45%         │                    │
│                      │                                   │                    │
│                      │  Estimated time: ~90 seconds      │                    │
│                      │                                   │                    │
│                      │  Please wait...                   │                    │
│                      │                                   │                    │
│                      └───────────────────────────────────┘                    │
│                                                                                │
│                                                                                │
│                                                                                │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Design Notes

### Color Scheme (Example)
- **Primary**: Blue (#3B82F6)
- **Success**: Green (#10B981)
- **Warning**: Yellow (#F59E0B)
- **Error**: Red (#EF4444)
- **Background**: Dark (#1F2937) or Light (#F9FAFB)
- **Text**: White (#FFFFFF) or Dark Gray (#111827)

### Status Indicators
- **●** Green = Running/Healthy
- **●** Yellow = Unhealthy/Warning
- **○** Gray = Stopped/Disabled
- **●** Red = Failed/Error

### Icons
- 🏠 Dashboard
- 📦 Extensions
- 📋 Queue
- 🏪 Store
- 🔑 Secrets/Keys
- 📝 Notes
- ✅ Todos/Tasks
- 🔄 Sync/Refresh
- 🤖 AI/Automation
- ⚠️ Warning
- ✓ Success/Checkmark

### Layout
- **Sidebar**: 240px fixed width
- **Main Content**: Flexible, max-width 1400px
- **Cards**: Rounded corners, shadow on hover
- **Responsive**: Collapse sidebar on mobile
- **Spacing**: 16px/24px grid system

### Components to Build
1. Layout (Header, Sidebar, MainContent)
2. Cards (ExtensionCard, ServiceCard, ToolCard)
3. Forms (Input, Checkbox, Button, FileUpload)
4. Modals (RestartModal, DeleteConfirm, ExtensionDetail)
5. Lists (ExtensionList, ToolList, ServiceList)
6. Status (HealthIndicator, StatusBadge)
7. Navigation (Sidebar, Tabs)

This gives you a complete visual reference for building the Phase 2 UI!