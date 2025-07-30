#!/usr/bin/env python3
"""
Startup script for ChefByte Dashboard
This script launches the MCP servers and Streamlit dashboard
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import streamlit
        import pandas
        import requests
        import sqlite3
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install streamlit pandas requests")
        return False

def start_mcp_servers():
    """Start the MCP servers in the background."""
    print("🚀 Starting MCP servers...")
    
    # Start push tools server
    push_process = subprocess.Popen([
        sys.executable, "push_tools.py", "--host", "0.0.0.0", "--port", "8010"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Start pull tools server
    pull_process = subprocess.Popen([
        sys.executable, "pull_tools.py", "--host", "0.0.0.0", "--port", "8020"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Start action tools server
    action_process = subprocess.Popen([
        sys.executable, "action_tools.py", "--host", "0.0.0.0", "--port", "8030"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Start main aggregated server
    main_process = subprocess.Popen([
        sys.executable, "mcp_server.py", "--host", "0.0.0.0", "--port", "8000"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait a moment for servers to start
    time.sleep(3)
    
    return {
        'push': push_process,
        'pull': pull_process,
        'action': action_process,
        'main': main_process
    }

def check_server_status(port, name):
    """Check if a server is running on the specified port."""
    import requests
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=2)
        if response.status_code == 200:
            print(f"✅ {name} server is running on port {port}")
            return True
        else:
            print(f"⚠️ {name} server responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print(f"❌ {name} server is not responding on port {port}")
        return False

def start_streamlit():
    """Start the Streamlit dashboard."""
    print("🌐 Starting Streamlit dashboard...")
    
    # Use the direct database access version for better performance
    dashboard_file = "dashboard_direct.py"
    
    if not os.path.exists(dashboard_file):
        print(f"❌ Dashboard file {dashboard_file} not found")
        return None
    
    # Start Streamlit
    streamlit_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", dashboard_file,
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ])
    
    return streamlit_process

def main():
    print("🍳 ChefByte Dashboard Startup")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check if database exists
    db_path = Path("data/chefbyte.db")
    if not db_path.exists():
        print("❌ Database not found. Please ensure the database is initialized.")
        print("You may need to run the application first to create the database.")
        sys.exit(1)
    
    print("✅ Database found")
    
    # Start MCP servers
    servers = start_mcp_servers()
    
    # Check server status
    print("\n🔍 Checking server status...")
    time.sleep(2)
    
    server_status = {
        'Push Tools': check_server_status(8010, "Push Tools"),
        'Pull Tools': check_server_status(8020, "Pull Tools"),
        'Action Tools': check_server_status(8030, "Action Tools"),
        'Main Server': check_server_status(8000, "Main Server")
    }
    
    # Start Streamlit
    streamlit_process = start_streamlit()
    
    if streamlit_process:
        print("\n🎉 Dashboard is starting...")
        print("📊 Dashboard URL: http://localhost:8501")
        print("🔧 MCP Server URLs:")
        print("   - Main: http://localhost:8000")
        print("   - Push Tools: http://localhost:8010")
        print("   - Pull Tools: http://localhost:8020")
        print("   - Action Tools: http://localhost:8030")
        print("\n💡 Press Ctrl+C to stop all servers")
        
        try:
            # Keep the script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down servers...")
            
            # Terminate all processes
            for name, process in servers.items():
                if process:
                    process.terminate()
                    print(f"   Stopped {name} server")
            
            if streamlit_process:
                streamlit_process.terminate()
                print("   Stopped Streamlit dashboard")
            
            print("✅ All servers stopped")
    else:
        print("❌ Failed to start Streamlit dashboard")
        sys.exit(1)

if __name__ == "__main__":
    main()