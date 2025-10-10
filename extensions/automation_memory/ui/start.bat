@echo off
REM Start automation_memory UI on specified port
set PORT=%1
if "%PORT%"=="" set PORT=5200
npm run dev

