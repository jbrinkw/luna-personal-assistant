#!/usr/bin/env python3
"""
Demo Web Server Service
A simple HTTP server that provides health checks and a demo endpoint.
"""

import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime


class DemoHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Override to provide cleaner logging."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sys.stderr.write(f"[{timestamp}] {format % args}\n")

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/healthz":
            # Health check endpoint
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "healthy", "service": "web_server"}
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == "/" or self.path == "/demo":
            # Demo endpoint
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "message": "Demo Web Server is running!",
                "timestamp": datetime.now().isoformat(),
                "endpoints": [
                    {"path": "/healthz", "description": "Health check endpoint"},
                    {"path": "/demo", "description": "Demo endpoint"},
                    {"path": "/info", "description": "Service information"}
                ]
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        elif self.path == "/info":
            # Service info endpoint
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "service_name": "web_server",
                "extension": "demo_extension",
                "requires_port": True,
                "uptime_start": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        else:
            # 404 for unknown paths
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())


def main():
    if len(sys.argv) < 2:
        print("Error: Port number required as first argument", file=sys.stderr)
        sys.exit(1)
    
    port = int(sys.argv[1])
    server_address = ("0.0.0.0", port)
    
    print(f"Starting Demo Web Server on 0.0.0.0:{port}", file=sys.stderr)
    
    httpd = HTTPServer(server_address, DemoHandler)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...", file=sys.stderr)
        httpd.shutdown()


if __name__ == "__main__":
    main()

