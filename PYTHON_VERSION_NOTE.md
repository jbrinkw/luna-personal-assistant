# Python Version Compatibility

## Current Status

Luna is tested and working with:
- ✅ **Python 3.12** (Recommended)
- ✅ **Python 3.13** (requires psycopg3)

## Database Driver Issue

### Python 3.13+
`psycopg2-binary 2.9.9` does **not work** with Python 3.13 due to C API changes (`_PyInterpreterState_Get` linker errors).

**Solution**: Luna now uses `psycopg[binary]` (psycopg3) which fully supports Python 3.13.

### Python 3.12 and below
Both `psycopg2-binary` and `psycopg[binary]` work fine.

## Installation

The `requirements.txt` has been updated to use `psycopg[binary]>=3.1.0` which supports both Python 3.12 and 3.13.

### If you need psycopg2 specifically

1. Use Python 3.12 or earlier
2. Modify `requirements.txt` to use:
   ```
   psycopg2-binary>=2.9.9
   ```

## Code Compatibility

Psycopg3 has a slightly different API than psycopg2, but the core connection code in Luna has been written to work with both. The main differences:

### Connection
```python
# psycopg2
import psycopg2
conn = psycopg2.connect(...)

# psycopg3
import psycopg
conn = psycopg.connect(...)
```

Both use the same connection string format and similar cursor operations.

## Recommendation

**Use Python 3.12** for maximum compatibility with all packages in the ecosystem. Python 3.13 is very new (released October 2024) and some packages haven't caught up yet.

## Checking Your Python Version

```bash
python --version
# or
python3 --version
```

## Creating a Python 3.12 Environment

### Using venv
```bash
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### Using conda
```bash
conda create -n luna python=3.12
conda activate luna
```





