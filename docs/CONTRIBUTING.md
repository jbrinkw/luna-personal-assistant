# Luna Hub Documentation

This directory contains the official documentation for Luna Hub, built with [MkDocs](https://www.mkdocs.org/) and the [Material theme](https://squidfunk.github.io/mkdocs-material/).

## Building the Docs

### Prerequisites

Install MkDocs dependencies (already included in `requirements.txt`):

```bash
source .venv/bin/activate
pip install mkdocs mkdocs-material
```

### Local Development

Serve the docs locally with live reload:

```bash
mkdocs serve
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### Building Static Site

Build the documentation as static HTML:

```bash
mkdocs build
```

Output will be in the `site/` directory.

### Deploying to GitHub Pages

Deploy directly to GitHub Pages:

```bash
mkdocs gh-deploy
```

This builds the docs and pushes them to the `gh-pages` branch.

## Documentation Structure

```
docs/
├── index.md                          # What Luna Hub Can Do For You
├── installation.md                   # Complete installation guide
├── getting-started/
│   └── featured-extensions.md       # ChefByte, Home Assistant examples
├── user-guide/
│   ├── navigating-interface.md      # Hub UI overview
│   ├── extensions.md                # Managing extensions
│   ├── external-services.md         # Docker service management
│   ├── agent-api.md                 # Using the Agent API
│   └── mcp-servers.md               # MCP configuration
└── developer-guide/
    ├── creating-extensions.md       # Extension development
    ├── tool-development.md          # Writing tools
    └── external-services.md         # Creating service definitions
```

## Contributing to Docs

1. **Edit Markdown files** in the `docs/` directory
2. **Preview changes** with `mkdocs serve`
3. **Commit changes** to the main branch
4. **Deploy** with `mkdocs gh-deploy` (if you have write access)

### Writing Style Guidelines

- Use **clear, concise language**
- Include **code examples** where applicable
- Add **admonitions** for warnings, tips, and notes:
  ```markdown
  !!! warning "Important"
      This is a warning message.

  !!! tip "Pro Tip"
      This is a helpful tip.

  !!! note "Note"
      This is additional context.
  ```
- Use **tabs** for multi-option examples:
  ````markdown
  === "Option 1"
      ```bash
      command-for-option-1
      ```

  === "Option 2"
      ```bash
      command-for-option-2
      ```
  ````

## Current Status

**Completed:**
- ✅ Main index page (What Luna Hub Can Do For You)
- ✅ Complete installation guide with all deployment modes
- ✅ Featured extensions showcase (ChefByte, Home Assistant)

**TODO:**
- ⬜ User guides for extensions, services, agents, MCP
- ⬜ Developer guides for creating extensions and tools
