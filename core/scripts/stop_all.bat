@echo off
REM Stop all Luna services on Windows

echo Stopping Luna services...

REM Kill processes by port
echo.
echo Stopping Agent API (port 8080)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    taskkill /PID %%a /F 2>nul
)

echo Stopping MCP Server (port 8765)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING') do (
    taskkill /PID %%a /F 2>nul
)

echo Stopping Hub UI (port 5173)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /PID %%a /F 2>nul
)

echo Stopping Automation Memory UI (port 5200)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5200 ^| findstr LISTENING') do (
    taskkill /PID %%a /F 2>nul
)

echo Stopping Automation Memory Backend (port 3051)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3051 ^| findstr LISTENING') do (
    taskkill /PID %%a /F 2>nul
)

echo.
echo All services stopped.
pause

