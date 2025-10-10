@echo off
REM Luna - Start All Services (Windows)
REM Starts Agent API, MCP Server, and Hub UI

echo Luna - Starting All Services
echo ========================================

REM Change to project root
cd /d %~dp0\..\..

REM Check if .env exists
if not exist ".env" (
    echo Error: .env file not found
    echo Please copy .env.example to .env and configure it
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: python not found
    exit /b 1
)

REM Install all Python dependencies using utility script
echo Installing Python dependencies...
python core\scripts\install_deps.py --quiet
if errorlevel 1 (
    echo Warning: Some dependencies failed to install
    echo Run 'python core\scripts\install_deps.py -v' for details
)

REM Check database connection (optional, skip if it fails)
echo Checking database connection...
python core\scripts\init_db.py 2>nul || (
    echo Warning: Database check failed - continuing without database validation
    echo Make sure to configure database credentials in .env if needed
)

REM Create logs directory
if not exist "logs" mkdir logs

REM Start Agent API
echo Starting Agent API on port 8080...
start /B python core\utils\agent_api.py > logs\agent_api.log 2>&1

REM Wait for Agent API to start
timeout /t 2 /nobreak >nul

REM Start MCP Server
echo Starting MCP Server on port 8765...
start /B python core\utils\mcp_server.py --port 8765 > logs\mcp_server.log 2>&1

REM Wait for MCP Server to start
timeout /t 2 /nobreak >nul

REM Start Automation Memory Backend (if exists)
if exist "extensions\automation_memory\backend" (
    echo Starting Automation Memory Backend on port 3051...
    cd extensions\automation_memory\backend
    
    REM Install dependencies if needed
    if not exist "node_modules" (
        echo Installing backend dependencies...
        call npm install
    )
    
    REM Start backend in background
    start /B node server.js > ..\..\..\logs\am_backend.log 2>&1
    
    cd ..\..\..
    timeout /t 2 /nobreak >nul
) else (
    echo Automation Memory Backend not found, skipping...
)

REM Start Automation Memory UI (if exists)
if exist "extensions\automation_memory\ui" (
    echo Starting Automation Memory UI on port 5200...
    cd extensions\automation_memory\ui
    
    REM Install dependencies if needed
    if not exist "node_modules" (
        echo Installing UI dependencies...
        call npm install
    )
    
    REM Set port and start UI in background
    set PORT=5200
    start /B npm run dev > ..\..\..\logs\am_ui.log 2>&1
    
    cd ..\..\..
    timeout /t 2 /nobreak >nul
) else (
    echo Automation Memory UI not found, skipping...
)

REM Start Hub UI (if exists)
if exist "hub_ui" (
    echo Starting Hub UI on port 5173...
    cd hub_ui
    
    REM Install dependencies if needed
    if not exist "node_modules" (
        echo Installing Hub UI dependencies...
        call npm install
    )
    
    REM Start UI in background
    start /B npm run dev > ..\logs\hub_ui.log 2>&1
    
    cd ..
) else (
    echo Hub UI not found, skipping...
)

echo.
echo All services started successfully!
echo ========================================
echo Agent API:  http://127.0.0.1:8080
echo MCP Server: http://127.0.0.1:8765
if exist "hub_ui" echo Hub UI:     http://127.0.0.1:5173
if exist "extensions\automation_memory" echo Automation Memory: http://127.0.0.1:5200
echo.
echo Logs:
echo   - logs\agent_api.log
echo   - logs\mcp_server.log
if exist "hub_ui" echo   - logs\hub_ui.log
if exist "extensions\automation_memory" (
    echo   - logs\am_backend.log
    echo   - logs\am_ui.log
)
echo.
echo To stop services, close this window or manually kill processes
echo.

pause

