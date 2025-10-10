# Luna Dependency Management

## ✅ Automated Dependency Installation

Luna now has a centralized utility for installing all Python dependencies using `uv` for fast, reliable installs.

---

## 🔧 The Install Utility

### Location
- **Script**: `core/scripts/install_deps.py`
- **Windows Wrapper**: `core/scripts/install_deps.bat`
- **Linux/Mac Wrapper**: `core/scripts/install_deps.sh`

### What It Does

The `install_deps.py` utility:
1. ✅ Checks that `uv` package manager is installed
2. ✅ Installs core Python dependencies from `requirements.txt`
3. ✅ Discovers all extensions with `requirements.txt` files
4. ✅ Installs each extension's Python dependencies
5. ✅ Provides detailed status and summary
6. ✅ Returns proper exit codes for automation

---

## 🚀 Usage

### Standalone Installation

Install all dependencies manually:

```bash
# Windows
python core\scripts\install_deps.py

# Linux/Mac
python3 core/scripts/install_deps.py

# Or use wrappers
core\scripts\install_deps.bat       # Windows
./core/scripts/install_deps.sh      # Linux/Mac
```

### With Options

```bash
# Verbose mode (shows detailed output)
python core\scripts\install_deps.py -v

# Quiet mode (only errors)
python core\scripts\install_deps.py --quiet

# Help
python core\scripts\install_deps.py --help
```

### Automatic Installation

Dependencies are **automatically installed** when you start Luna:

```bash
# Windows
core\scripts\start_all.bat

# Linux/Mac
./core/scripts/start_all.sh
```

The startup scripts now call `install_deps.py --quiet` before starting services.

---

## 📋 Requirements Files

### Core Requirements
**File**: `requirements.txt` (project root)

Contains core dependencies:
- FastAPI, Uvicorn (web framework)
- LangChain, LangGraph (AI agents)
- Pydantic (validation)
- psycopg2 (Postgres)
- FastMCP (MCP server)
- pytest (testing)

### Extension Requirements
**Location**: `extensions/<extension_name>/requirements.txt`

Each extension can have its own Python requirements:
- `extensions/automation_memory/requirements.txt`
- `extensions/home_assistant/requirements.txt`

The install utility automatically finds and installs all of them.

---

## 🧪 Testing

### Test File
**Location**: `tests/test_install_deps.py`

Comprehensive tests covering:
- ✅ Script existence and importability
- ✅ Help option functionality
- ✅ uv detection
- ✅ Extension discovery
- ✅ Requirements file validation

### Run Tests

```bash
# Run install_deps tests
$env:SKIP_SERVICE_CHECK="1" ; pytest tests/test_install_deps.py -v

# Or on Linux/Mac
SKIP_SERVICE_CHECK=1 pytest tests/test_install_deps.py -v
```

**Results**: ✅ **9/9 tests passing**

---

## 📊 Output Example

```
============================================================
Luna Dependency Installation
============================================================

[INFO] Checking for uv package manager...
[OK] uv found: uv 0.8.5

[INFO] Installing Core dependencies...
[OK] Core dependencies installed successfully

[INFO] Found 2 extension(s) with requirements

[INFO] Installing Extension: automation_memory...
[OK] Extension: automation_memory installed successfully

[INFO] Installing Extension: home_assistant...
[OK] Extension: home_assistant installed successfully

============================================================
Installation Summary:
============================================================
  [OK] Core
  [OK] automation_memory
  [OK] home_assistant
============================================================
All dependencies installed successfully!
============================================================
```

---

## 🔍 Key Features

### 1. **uv Package Manager**
Uses `uv` for ultra-fast dependency resolution and installation:
- 10-100x faster than pip
- Better dependency resolution
- Reliable lockfile generation

Install uv:
```bash
pip install uv
```

### 2. **Automatic Discovery**
Scans `extensions/*/requirements.txt` automatically - no configuration needed.

### 3. **Error Handling**
- Graceful failure handling
- Detailed error messages in verbose mode
- Proper exit codes for CI/CD

### 4. **Color-Coded Output**
- 🟢 Green: Success
- 🔴 Red: Error
- 🟡 Yellow: Warning
- 🔵 Blue/Cyan: Info

### 5. **Integrated with Startup**
Runs automatically when you start Luna services, ensuring dependencies are always up to date.

---

## 🛠️ Troubleshooting

### "uv not found"
**Solution**: Install uv
```bash
pip install uv
```

### Permission Errors
If you get permission errors, you may need:
- Run as administrator (Windows)
- Use sudo (Linux/Mac)
- Or better: use a virtual environment

### Version Conflicts
If you see dependency version conflicts:
1. Check `requirements.txt` for conflicting versions
2. Run with `-v` flag to see detailed error
3. Update version constraints as needed

### Extension Not Found
If an extension's requirements aren't installing:
1. Ensure `extensions/<name>/requirements.txt` exists
2. Check file is not empty
3. Run `python core/scripts/install_deps.py -v` to see details

---

## 📝 Adding New Extensions

When creating a new extension:

1. Create extension directory:
   ```
   extensions/my_extension/
   ```

2. Add Python requirements:
   ```
   extensions/my_extension/requirements.txt
   ```

3. The install utility will **automatically discover and install** it!

No configuration needed - it just works! ✨

---

## ✅ Summary

- ✅ **Created**: `core/scripts/install_deps.py` - Centralized dependency installer
- ✅ **Created**: Test suite with 9 passing tests
- ✅ **Updated**: `start_all.bat` and `start_all.sh` to use the utility
- ✅ **Fixed**: Version conflicts in core `requirements.txt`
- ✅ **Automated**: Dependencies install on every startup

**Dependencies are now managed automatically across the entire Luna platform!** 🎉




