# Visual User Guide

Welcome to Luna! This visual guide walks you through the interface using annotated screenshots. Click any numbered marker on the images to jump to its detailed explanation below.

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

## Hub Home Dashboard

<div style="position: relative; display: inline-block;">
  <img src="/tutorial_screenshots/annotated/hub_home_dashboard.png" usemap="#hub-home-map" style="max-width: 100%; height: auto;" width="2088" height="1423" />
  <map name="hub-home-map">
    <area shape="rect" coords="168,473,345,522" href="#extension-store-browse" alt="Browse Store" />
    <area shape="rect" coords="555,476,732,525" href="#tool-mcp-manager" alt="Tool & MCP Manager" />
    <area shape="rect" coords="946,477,1146,526" href="#manage-secrets" alt="Manage Secrets" />
    <area shape="rect" coords="1367,471,1548,520" href="#infrastructure" alt="Infrastructure" />
    <area shape="rect" coords="1772,470,1924,519" href="#extensions" alt="Extensions" />
    <area shape="rect" coords="266,698,418,747" href="../getting-started/featured-extensions.md#quick-chat" alt="Quick Chat" />
    <area shape="rect" coords="240,1095,427,1144" href="#built-in-agents" alt="Built-in Agents" />
    <area shape="rect" coords="177,1325,360,1374" href="#agent-presets" alt="Agent Presets" />
    <area shape="rect" coords="315,643,578,692" href="../getting-started/featured-extensions.md#automation-memory-extension" alt="Automation Memory UI" />
    <area shape="rect" coords="253,753,425,802" href="../getting-started/featured-extensions.md#chefbyte-extension" alt="ChefByte UI" />
    <area shape="rect" coords="242,816,427,865" href="../getting-started/featured-extensions.md#coachbyte-ui" alt="CoachByte UI" />
    <area shape="rect" coords="237,880,378,929" href="#grocy-ui" alt="Grocy UI" />
  </map>
</div>

### 2. Tool & MCP Manager {: #tool-manager }

Configure which tools are available to your MCP servers and AI agent presets. This is where you control what your AI assistants can actually do - toggle tools on/off per server or create specialized agent configurations.

### 3. Manage Secrets

Securely store API keys, tokens, and other environment variables needed by extensions and services. Values are encrypted and masked in the UI. Extensions will tell you which keys they need here.

### 4. Infrastructure

Manage external services like Postgres, Grocy, and other Docker-based infrastructure components. Install, start, stop, and configure services that your extensions depend on.

### 5. Extensions

View, enable/disable, configure, and uninstall your installed extensions. See which extensions are active, check their versions, and manage their lifecycle.

### 6. Quick Chat

Test your agents and MCP servers with a simple chat interface. Great for debugging tool calls, testing new configurations, and verifying that your agents work correctly. *See [Featured Extensions](../getting-started/featured-extensions.md#quick-chat) for detailed walkthrough with annotated screenshots.*

### 7. Built-in Agents {: #built-in-agents }

Shows the core agent implementations available in Luna (like `passthrough_agent`, `simple_agent`). These are the base agents that come with Luna and can be used directly or as foundations for agent presets.

### 8. Agent Presets {: #agent-presets }

Custom agents you've created with filtered tool access. Each preset is based on a built-in agent but has its own tool configuration. Example: "smart_home_assistant" with only Home Assistant tools enabled.

### 9. Automation Memory UI

Opens the Automation Memory extension UI for managing persistent memories, task flows, and scheduled automations. *See [Featured Extensions](../getting-started/featured-extensions.md#automation-memory-extension) for detailed walkthrough.*

### 10. ChefByte UI {: #chefbyte-ui }

Opens the ChefByte extension UI for nutrition tracking, meal planning, Walmart product linking, and barcode scanning. *See [Featured Extensions](../getting-started/featured-extensions.md#chefbyte-extension) for detailed walkthrough with annotated screenshots.*

### 11. CoachByte UI {: #coachbyte-ui }

Opens the CoachByte extension UI for fitness and workout tracking. *See [Featured Extensions](../getting-started/featured-extensions.md#coachbyte-ui) for more information.*

### 12. Grocy UI {: #grocy-ui }

Opens the Grocy web interface for grocery and household management. This is an external service that must be installed via Infrastructure first. Manage inventory, recipes, shopping lists, and more. Visit <a href="https://grocy.info/" target="_blank" rel="noopener noreferrer">grocy.info</a> to learn more.

---

### About This Page

The Dashboard is your home base in Luna - the first thing you see after logging in with GitHub. It's designed to give you quick access to everything important and show you the current state of your system at a glance.

**Page Layout:**

The Dashboard is organized into several sections:

- **Header:** Contains the Luna logo, navigation breadcrumbs, system controls (Restart button), and the Update Manager badge showing pending changes
- **Quick Stats:** Card showing counts of installed extensions, available tools, configured agents, and running external services
- **Quick Actions:** Navigation tiles for the most common tasks (Browse Store, Tool Manager, Manage Secrets, Infrastructure, Extensions, [Quick Chat](../getting-started/featured-extensions.md#quick-chat))
- **Discovered Agents:** Shows both built-in agents that come with Luna and custom agent presets you've created
- **Active UIs:** Clickable links to extension web interfaces that are currently running

**How to Use the Dashboard:**

When you first log in, use the Quick Stats to verify that your system is healthy. All counts should match what you expect. If something looks wrong (like 0 tools when you have extensions installed), check the logs or try restarting Luna.

The Quick Actions tiles are your primary navigation. Click any tile to jump to that section. These are the pages you'll use most often for configuring and managing Luna.

The Discovered Agents section shows what agents are available for use via the Agent API. Built-in agents are the core implementations that ship with Luna. Agent Presets are custom configurations you create with specific tool subsets - these are useful for creating specialized assistants.

The Active UIs section dynamically updates based on which extensions you have installed and enabled. These are full web applications provided by extensions. Not all extensions provide UIs - some only provide tools or background services.

**Common Workflows from the Dashboard:**

1. **First-time setup:** Click "Manage Secrets" to add required API keys, then "Browse Store" to install extensions, then "Restart" to apply changes
2. **Configuring tools:** Click "Tool Manager" to enable/disable tools for your MCP servers or create agent presets
3. **Testing changes:** Click [Quick Chat](../getting-started/featured-extensions.md#quick-chat) to verify that your agents and tools work correctly after configuration
4. **Installing infrastructure:** Click "Infrastructure" to set up databases, Grocy, or other services that extensions depend on
5. **Accessing extension features:** Click any Active UI tile to open that extension's web interface

**System Status Indicators:**

Pay attention to the Update Manager badge in the header. If it shows a number, you have pending changes queued. Click it to review what's queued, then use the Restart button to apply changes.

The Quick Stats card helps you track your system's configuration:
- **Extensions:** How many you have installed (enabled + disabled)
- **Tools:** Total tools available from all extensions and remote MCP servers
- **Agents:** Built-in agents + your custom presets
- **External Services:** Running Docker services

**Pro Tips:**

- Bookmark the Dashboard URL - it's your starting point
- Use [Quick Chat](../getting-started/featured-extensions.md#quick-chat) frequently to test changes before committing to complex workflows
- Agent Presets are powerful - create specialized agents for different tasks instead of one agent with all tools
- Active UIs open in the same tab by default - right-click to open in new tab if you want to keep the Dashboard visible
- The header is consistent across all pages, so you can always click "Luna" logo to return to Dashboard

---

## Extension Store - Browse {: #extension-store-browse }

![Extension Store Browse](/tutorial_screenshots/core/addon_store_browse.png)

### About This Page

The Extension Store is where you discover and install new capabilities for Luna. Extensions are packaged bundles of tools, UIs, services, and configuration that add specific functionality to your system.

**Page Layout:**

The Browse page shows a grid of available extensions. Each card displays:
- **Extension Name:** The identifier used internally
- **Display Name:** Human-readable name
- **Description:** What the extension does
- **Version:** Current version number
- **Install Button:** Click to begin installation

The page also has a search bar to filter extensions by name or description, and category filters to narrow down by type (Productivity, Smart Home, Nutrition, etc.).

**How Extensions Work:**

Extensions in Luna are self-contained packages that can include:
- **Tools:** Functions that agents and MCP servers can call (e.g., "add_memory", "search_web")
- **UIs:** Web interfaces for human interaction (like ChefByte's scanner)
- **Services:** Background processes (APIs, data processors, etc.)
- **Configuration:** Required secrets, settings, and dependencies

When you install an extension, Luna:
1. Downloads the extension files
2. Queues the installation (doesn't apply immediately)
3. Shows it in the Update Manager badge
4. Waits for you to restart Luna
5. On restart, installs dependencies, configures services, and enables tools

**Types of Extensions:**

- **Built-in Extensions:** Ship with Luna, can't be uninstalled (like automation_memory)
- **Community Extensions:** Created by the Luna community, installed from GitHub
- **Custom Extensions:** Your own extensions, uploaded as ZIP files or installed from private repos

**Installation Methods:**

From this browse page, you can only install featured/curated extensions with a simple click. For more advanced installation options:
- Go to the Extensions page for GitHub URL installation
- Go to the Extensions page for ZIP file upload
- Use monorepo syntax for subdirectory installs: `github:user/repo:path/to/ext`

**What Happens After Clicking Install:**

When you click an Install button:
1. The extension is added to your update queue
2. You're redirected to a configuration page (see next section)
3. You can choose to configure secrets now or skip
4. The installation remains queued until you restart Luna

**Important Notes:**

- Installing extensions doesn't make them active immediately - restart required
- Some extensions depend on external services (like ChefByte needs Grocy) - install those in Infrastructure first
- Extensions can conflict with each other if they use the same ports or tool names - check logs if issues arise
- You can safely browse and queue multiple installations, then restart once to apply all changes

**Pro Tips:**

- Read extension descriptions carefully to understand dependencies
- Check the required secrets before installing - gather API keys first
- Install infrastructure services before extensions that depend on them
- Start with one extension at a time when learning Luna
- Use the search bar to find extensions by capability (e.g., "smart home", "nutrition")

---

## Extension Store - Configure

<div style="position: relative; display: inline-block;">
  <img src="/tutorial_screenshots/annotated/addon_store_configure_extension.png" usemap="#configure-map" style="max-width: 100%; height: auto;" width="2736" height="1483" />
  <map name="configure-map">
    <area shape="rect" coords="1288,1170,1592,1220" href="#skip-vs-configure-workflow" alt="Skip vs Configure Workflow" />
  </map>
</div>

### 1. Skip vs Configure Workflow {: #skip-vs-configure-workflow }

When installing an extension, you have two workflow options:

**Configure Now:**
- Fill out required API keys and settings immediately
- Extension will be ready to use after restart
- Recommended if you have all secrets prepared
- Saves time - no need to revisit Manage Secrets later

**Skip Configuration:**
- Install the extension without setting up secrets
- You can configure them later in Manage Secrets page
- Useful if you don't have API keys ready yet
- Extension will install but tools may fail until configured

Choose based on whether you have the required credentials available right now.

---

### About This Page

The Configure page appears after you click Install on an extension. It's an optional step that lets you set up required secrets and configuration before the extension is installed.

**Page Layout:**

The page shows:
- **Extension Info:** Name, description, and version at the top
- **Configuration Form:** Fields for required secrets and settings
- **Field Types:** Text inputs, dropdowns, checkboxes depending on what the extension needs
- **Help Text:** Gray text under each field explaining what it's for
- **Action Buttons:** "Skip" and "Configure & Install" at the bottom

**How Configuration Works:**

Extensions declare their required secrets in a `config.json` file. Common examples:
- `OPENAI_API_KEY`: For AI model access
- `HA_URL` and `HA_TOKEN`: For Home Assistant integration
- `GROCY_API_KEY`: For Grocy integration
- Extension-specific settings like default values, URLs, etc.

When you fill out this form and click "Configure & Install":
1. Luna validates that all required fields are filled
2. Values are saved to your `.env` file (encrypted)
3. The extension is queued for installation
4. On restart, the extension can access these secrets via environment variables

If you click "Skip":
1. The extension is queued without secret configuration
2. You can configure secrets later in Manage Secrets
3. Extension will install but may not work until secrets are added

**When to Configure vs Skip:**

**Configure Now if:**
- You have all API keys and credentials ready
- The extension is critical to your workflow
- You want to test it immediately after restart
- The form is simple and quick to fill out

**Skip if:**
- You need to create accounts or get API keys first
- You're installing multiple extensions and want to batch secret entry
- You're just exploring and not ready to use the extension yet
- You prefer managing all secrets in one place (Manage Secrets page)

**Field Validation:**

Required fields are marked with asterisks (*). You cannot submit the form without filling them. Optional fields can be left blank - they'll use defaults or can be configured later.

Some fields have validation:
- URLs must start with `http://` or `https://`
- Ports must be numbers between 1-65535
- API keys may have format requirements (shown in help text)

**What Happens After Configuration:**

After clicking "Configure & Install" or "Skip":
1. You're returned to the Extension Store or Extensions page
2. The Update Manager badge increments (showing pending changes)
3. The extension appears in your queue (view in Update Manager)
4. Restart Luna to apply the installation
5. After restart, check the Dashboard to verify the extension is active

**Pro Tips:**

- Keep a password manager or notes file with your API keys for quick copy/paste
- If an extension needs multiple keys, gather them all before starting configuration
- Read the help text carefully - some fields have specific format requirements
- Use "Skip" liberally if you're bulk-installing - configure everything in Manage Secrets afterward

---

## Tool & MCP Manager {: #tool-mcp-manager }

<div style="position: relative; display: inline-block;">
  <img src="/tutorial_screenshots/annotated/tool_mcp_manager.png" usemap="#tool-manager-map" style="max-width: 100%; height: auto;" width="2348" height="4910" />
  <map name="tool-manager-map">
    <area shape="rect" coords="1869,551,2245,601" href="#mcp-vs-agent-presets-mode-toggle" alt="MCP vs Agent Presets Mode Toggle" />
    <area shape="rect" coords="1010,885,1309,935" href="#active-server-selector-pills" alt="Active Server Selector Pills" />
    <area shape="rect" coords="595,1564,973,1614" href="#add-remote-mcp-server-smithery" alt="Add Remote MCP Server (Smithery)" />
  </map>
</div>

### 1. MCP vs Agent Presets Mode Toggle {: #mcp-vs-agent-presets-mode-toggle }

Toggle between two modes at the top right:

**MCP Mode:**
- Manage MCP servers and configure which tools each server can access
- For use with Claude Desktop, Cline, and other MCP clients
- Each server has its own API key and tool selection

**Agent Presets Mode:**
- Create custom agent configurations with filtered tool sets
- For use with Luna's internal Agent API
- All presets share the same API key but have different tool access

Click the toggle to switch between modes. The rest of the page updates to show server pills or preset pills accordingly.

### 2. Active Server Selector Pills {: #active-server-selector-pills }

Click these pills to select which MCP server or agent preset you're currently configuring:

**In MCP Mode:**
- Shows all configured MCP servers (main, research, smarthome, etc.)
- The "main" server uses GitHub OAuth and cannot be deleted
- Additional servers use API keys shown below the pills

**In Agent Presets Mode:**
- Shows all custom agent presets you've created
- Click a preset to see and modify its tool configuration
- No "main" preset - all are user-created

The selected pill is highlighted. All tool toggles below apply to the selected server/preset.

### 3. Add Remote MCP Server (Smithery) {: #add-remote-mcp-server-smithery }

Integrate third-party tools from the Smithery MCP ecosystem:

**How to use:**
1. Get a Smithery MCP server URL from [smithery.ai](https://smithery.ai) (includes API key in URL)
2. Paste the full URL into this field
3. Click the Add button
4. Wait for Luna to connect and discover tools
5. Toggle individual tools from that server on/off

**Popular Smithery Servers:**
- **Exa Search:** Web search optimized for AI agents
- **Context7:** Documentation search with RAG
- **Brave Search:** Alternative web search provider

Once added, remote MCP server tools appear in the "Remote MCP Tools" section below with toggle switches for each tool.

---

### About This Page

The Tool & MCP Manager is one of the most important configuration pages in Luna. It controls which tools are available to your AI agents and MCP clients. Understanding this page is crucial for getting the most out of Luna.

**Page Layout:**

The page has several distinct sections:
- **Mode Toggle:** Top-right button switching between MCP and Agent Presets modes
- **Server/Preset Pills:** Horizontal row of clickable pills showing available servers or presets
- **Quick Actions:** Enable All / Disable All buttons for bulk tool toggling
- **Management Section:** Left side shows rename/delete controls and API key display for selected item
- **Creation Section:** Right side shows forms for creating new servers or presets
- **Add Remote MCP Server:** Field for adding Smithery integrations
- **Remote MCP Tools:** Cards showing tools from Smithery servers with toggles
- **Local Extension Tools:** Cards showing tools from installed Luna extensions with toggles

**Understanding MCP vs Agent Presets:**

Luna has two separate systems for running AI assistants:

**MCP Servers:**
- For external clients (Claude Desktop, Cline, VSCode extensions, etc.)
- Each server is an independent MCP endpoint with its own URL and API key
- Tools are exposed via the Model Context Protocol standard

**Agent Presets:**
- For Luna's internal Agent API (OpenAI-compatible endpoint)
- Custom agent configurations based on built-in agents
- Each preset filters tools to create specialized agents

These systems are independent - configuring one doesn't affect the other.

**Common Workflows:**

**Setting up Claude Desktop:**
1. Stay in MCP mode
2. Select "main" server (uses GitHub OAuth)
3. Enable tools you want Claude to use
4. Restart Luna
5. Configure Claude Desktop to connect to your Luna instance

**Creating a specialized agent:**
1. Switch to Agent Presets mode
2. Enter name (e.g., "home_agent") and select base agent
3. Click Create
4. Select the new preset
5. Click "Disable All" in Quick Actions
6. Enable only Home Assistant tools
7. Restart Luna

**Pro Tips:**

- Create focused agent presets rather than giving every agent all tools
- Use the "main" MCP server for personal use, create additional servers for sharing
- Name presets descriptively (e.g., "smart_home_assistant" not "agent1")
- Test tool configurations in [Quick Chat](../getting-started/featured-extensions.md#quick-chat) before production use

---

## Manage Secrets {: #manage-secrets }

![Manage Secrets](/tutorial_screenshots/core/key_manager_secrets.png)

### About This Page

The Manage Secrets page is where you securely store API keys, tokens, passwords, and other sensitive configuration values that Luna and your extensions need to function.

**Common Environment Variables:**

**Core Luna Secrets:**
- `OPENAI_API_KEY`: For AI model access via OpenAI
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`: For GitHub OAuth authentication

**External Service Secrets:**
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Database connection
- `GROCY_API_KEY`, `GROCY_URL`: For Grocy integration
- `HA_URL`, `HA_TOKEN`: For Home Assistant integration

**Auto-Generated Secrets (Don't Edit Manually):**
- `AGENT_API_KEY`: Generated by Agent API on first run
- `MCP_SERVER_{NAME}_API_KEY`: Generated for non-main MCP servers
- `SERVICE_{EXTENSION}_{SERVICE}_API_KEY`: Generated for extension services

**Adding New Secrets:**

1. Click "Add New" button
2. Enter the key name (e.g., `OPENAI_API_KEY`)
3. Enter the value
4. Click Save

**Security Considerations:**

- Never commit .env to git
- Rotate keys regularly
- Use environment-specific keys
- Delete unused keys

**Pro Tips:**

- Use a password manager to store your API keys
- Keep a backup .env file in encrypted cloud storage
- Document where each key comes from
- Review Required Secrets section before installing extensions

---

## Infrastructure - External Services {: #infrastructure }

![Infrastructure](/tutorial_screenshots/core/infrastructure_external_services.png)

### About This Page

The Infrastructure page is where you manage external services - Docker-based applications like databases, web apps, and other infrastructure components that your Luna extensions depend on.

**Status Indicators:**

Services show color-coded status:
- **🟢 Green (Running):** Service is healthy
- **🟡 Yellow (Starting/Unhealthy):** Service is starting or health check failed
- **🔴 Red (Stopped/Failed):** Service is not running
- **⚪ Gray (Disabled):** Service installed but disabled from auto-start

**Available Services:**

**Postgres:**
- PostgreSQL database server
- Required by: Automation Memory extension
- Default port: 5432

**Grocy:**
- Grocery and household management
- Required by: ChefByte extension
- Default port: 9283
- Provides web UI

**Common Workflows:**

**Setting up Postgres:**
1. Click "Install" on Postgres card
2. Configure database name, username, password
3. Restart Luna
4. Click "Start" on Postgres
5. Add credentials to Manage Secrets

**Setting up Grocy:**
1. Click "Install" on Grocy card
2. Configure port and admin password
3. Restart Luna
4. Click "Start" on Grocy
5. Click "View UI" to access Grocy

**Pro Tips:**

- Install infrastructure services before extensions that need them
- Enable auto-start for critical services
- Back up service data volumes regularly
- Monitor status indicators

---

## Extensions - Managing Installed Extensions {: #extensions }

![Extension Manager](/tutorial_screenshots/core/extension_manager.png)

### About This Page

The Extension Manager page shows all your installed extensions and lets you control their lifecycle - enabling, disabling, configuring, and uninstalling them.

**Enabling and Disabling Extensions:**

**Enable:**
- Toggle switch to green
- Tools become available
- UIs appear in Dashboard
- Restart required

**Disable:**
- Toggle switch to gray
- Tools removed
- UIs disappear
- Restart required

**Installing Extensions from GitHub:**

Standard repository:
```
github:username/repo
```

Monorepo (subdirectory):
```
github:username/repo:path/to/extension
```

**Installing from ZIP:**

1. Package extension as ZIP
2. Click "Upload Extension"
3. Select ZIP file
4. Restart Luna

**Pro Tips:**

- Read extension README before installing
- Disable unused extensions
- Keep extensions updated
- Test in [Quick Chat](../getting-started/featured-extensions.md#quick-chat) after installation

---

## Next Steps

Now that you've seen the interface, here's what to do next:

1. **First-Time Setup:**
   - Add required API keys in [Manage Secrets](#manage-secrets)
   - Install extensions from [Browse Store](#extension-store-browse)
   - Restart Luna to apply changes

2. **Configure Tools:**
   - Go to [Tool Manager](#tool-manager)
   - Create agent presets for specific use cases
   - Add remote MCP servers from Smithery

3. **Explore Extension UIs:**
   - Open [Automation Memory](../getting-started/featured-extensions.md#automation-memory-extension) to set up recurring tasks
   - Try [ChefByte](../getting-started/featured-extensions.md#chefbyte-extension) to scan groceries and track nutrition
   - Check out [Quick Chat](../getting-started/featured-extensions.md#quick-chat) to test your agents

4. **Read More:**
   - [Full Interface Guide](navigating-interface.md) - Detailed text documentation
   - [API Reference](../reference/api.md) - Integrate with Luna programmatically

---

**Need Help?** Check the logs, review extension READMEs, and ensure all required environment variables are set.
