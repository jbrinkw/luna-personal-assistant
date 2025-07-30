# ChefByte Dashboard

A real-time, auto-updating GUI for viewing and managing the ChefByte database. This dashboard provides a comprehensive interface for all database operations with automatic refresh capabilities.

## 🚀 Quick Start

### Option 1: Automatic Startup (Recommended)
```bash
python run_dashboard.py
```

This will:
- Start all MCP servers automatically
- Launch the Streamlit dashboard
- Open the dashboard at http://localhost:8501

### Option 2: Manual Startup
1. Start the MCP servers:
```bash
# Terminal 1: Push Tools
python push_tools.py --host 0.0.0.0 --port 8010

# Terminal 2: Pull Tools  
python pull_tools.py --host 0.0.0.0 --port 8020

# Terminal 3: Action Tools
python action_tools.py --host 0.0.0.0 --port 8030

# Terminal 4: Main Server
python mcp_server.py --host 0.0.0.0 --port 8000
```

2. Start the dashboard:
```bash
streamlit run dashboard_direct.py --server.port 8501
```

## 📊 Dashboard Features

### 🏠 Inventory Management
- **Real-time view** of all pantry items
- **Expiration tracking** with color-coded warnings
- **Add/remove items** with direct database updates
- **Auto-refresh** every 30 seconds (optional)

### 🍽️ Saved Meals
- **Browse all saved recipes** with full details
- **View ingredients** parsed from JSON format
- **Add new meals** with recipe and ingredient details
- **Delete meals** with one-click removal

### 🛒 Shopping List
- **Integrated view** combining shopping list with ingredient details
- **Add items** from available ingredients database
- **Walmart links** for easy online shopping
- **Quantity management** with suggested purchase amounts

### 📅 Daily Planner
- **Calendar-style view** of planned meals
- **Add planner entries** with notes and meal IDs
- **Date-based organization** with automatic sorting
- **Delete entries** with confirmation

### 👅 Taste Profile
- **View current preferences** and dietary restrictions
- **Update profile** with natural language input
- **Real-time editing** with immediate database updates

### 💡 Meal Ideas
- **Browse generated meal suggestions**
- **View full recipes** with ingredients
- **Save ideas** to saved meals with one click
- **Auto-refresh** to see new suggestions

### ✅ In-Stock Meals
- **See what you can cook** with current inventory
- **Recipe details** for each available meal
- **Prep time information** for meal planning

### 📊 Database Statistics
- **Real-time counts** for all database tables
- **Visual metrics** showing data distribution
- **Connection status** for all services

## 🔧 Technical Details

### Architecture
- **Direct database access** for fast, real-time updates
- **MCP tool integration** for complex operations
- **SQLite database** with optimized queries
- **Streamlit interface** with responsive design

### Auto-Update Features
- **Manual refresh buttons** on each section
- **Auto-refresh toggle** (30-second intervals)
- **Real-time database monitoring**
- **Connection status indicators**

### Data Flow
1. **Dashboard** reads directly from SQLite database
2. **Updates** use MCP push tools for consistency
3. **Complex operations** leverage existing action tools
4. **Real-time feedback** for all operations

## 🛠️ Configuration

### Database Path
The dashboard expects the database at `data/chefbyte.db`. This is configurable in `dashboard_direct.py`:

```python
DB_PATH = "data/chefbyte.db"  # Change this if needed
```

### Server URLs
MCP server URLs are configurable:

```python
PUSH_SERVER_URL = "http://localhost:8010"
PULL_SERVER_URL = "http://localhost:8020"  
ACTION_SERVER_URL = "http://localhost:8030"
```

### Port Configuration
- **Dashboard**: http://localhost:8501
- **Main MCP**: http://localhost:8000
- **Push Tools**: http://localhost:8010
- **Pull Tools**: http://localhost:8020
- **Action Tools**: http://localhost:8030

## 📱 Usage Tips

### Navigation
- Use the **sidebar navigation** to switch between sections
- Each section has its own **refresh button**
- **Auto-refresh toggle** in sidebar for continuous updates

### Data Entry
- **Forms** are available in expandable sections
- **Validation** prevents invalid data entry
- **Success messages** confirm successful operations
- **Error handling** shows helpful error messages

### Performance
- **Direct database access** ensures fast loading
- **Lazy loading** for large datasets
- **Connection pooling** for efficient database access
- **Caching** reduces redundant queries

## 🔍 Troubleshooting

### Common Issues

**Dashboard won't start:**
```bash
# Check dependencies
pip install streamlit pandas requests

# Check database exists
ls data/chefbyte.db
```

**MCP servers not responding:**
```bash
# Check if ports are in use
netstat -an | grep 8000
netstat -an | grep 8010
netstat -an | grep 8020
netstat -an | grep 8030
```

**Database connection errors:**
```bash
# Check database file permissions
ls -la data/chefbyte.db

# Verify database integrity
sqlite3 data/chefbyte.db "PRAGMA integrity_check;"
```

### Debug Mode
Enable debug logging by setting environment variables:
```bash
export STREAMLIT_LOG_LEVEL=debug
streamlit run dashboard_direct.py
```

## 🚀 Deployment

### Local Development
```bash
python run_dashboard.py
```

### Production Deployment
1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start servers:**
```bash
python run_dashboard.py
```

3. **Access dashboard:**
Open http://localhost:8501 in your browser

### Docker Deployment (Future)
```dockerfile
# Dockerfile for production deployment
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "dashboard_direct.py", "--server.port", "8501"]
```

## 📈 Future Enhancements

### Planned Features
- **Real-time notifications** for expiring items
- **Barcode scanning** for inventory management
- **Recipe import** from popular cooking sites
- **Mobile-responsive** design improvements
- **Dark mode** theme option
- **Export functionality** for data backup
- **User authentication** and multi-user support

### Performance Optimizations
- **WebSocket connections** for real-time updates
- **Database indexing** for faster queries
- **Caching layer** for frequently accessed data
- **Background tasks** for data processing

## 🤝 Contributing

### Development Setup
1. **Clone the repository**
2. **Install dependencies:** `pip install -r requirements.txt`
3. **Run the dashboard:** `python run_dashboard.py`
4. **Make changes** and test locally
5. **Submit pull request** with detailed description

### Code Style
- **Follow PEP 8** for Python code
- **Use type hints** for function parameters
- **Add docstrings** for all functions
- **Test thoroughly** before submitting

## 📄 License

This dashboard is part of the ChefByte project and follows the same licensing terms.

---

**Happy cooking! 🍳**