"""Auth Service for Luna Hub UI - GitHub OAuth Authentication

Provides GitHub OAuth login flow for the Hub UI.
Uses stateless JWT authentication (no database required).
"""
import os
import sys
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Cookie, Response, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import jwt

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optional .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---- Configuration ----
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
ALLOWED_GITHUB_USERNAME = os.getenv("ALLOWED_GITHUB_USERNAME")
PUBLIC_DOMAIN = os.getenv("PUBLIC_DOMAIN", "localhost:5173")
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
SESSION_DURATION_HOURS = int(os.getenv("SESSION_DURATION_HOURS", "24"))
DEMO_MODE = os.getenv("DEMO_MODE", "").lower() in ("true", "1", "yes")

# Validate configuration
if DEMO_MODE:
    print("[Auth Service] ⚠️  DEMO MODE ENABLED - Authentication is BYPASSED")
    print("[Auth Service] This should ONLY be used for demonstrations and testing")
    print("[Auth Service] Set DEMO_MODE=false or remove it for production use")
elif not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
    print("[Auth Service] WARNING: GitHub OAuth not configured")
    print("[Auth Service] Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env")
    print("[Auth Service] Auth service will start but OAuth will not work")

if not DEMO_MODE:
    if not ALLOWED_GITHUB_USERNAME:
        print("[Auth Service] WARNING: ALLOWED_GITHUB_USERNAME not set")
        print("[Auth Service] Any GitHub user will be able to log in")
    else:
        print(f"[Auth Service] Access restricted to GitHub user: {ALLOWED_GITHUB_USERNAME}")

# ---- FastAPI App ----
app = FastAPI(title="Luna Auth Service")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- JWT Functions ----
def create_jwt_token(github_id: int, github_username: str) -> str:
    """Create a JWT token for the user"""
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=SESSION_DURATION_HOURS)
    
    payload = {
        "github_id": github_id,
        "github_username": github_username,
        "iat": now,
        "exp": expires_at
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token

def validate_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate JWT token and return payload"""
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {
            "github_id": payload["github_id"],
            "github_username": payload["github_username"]
        }
    except jwt.ExpiredSignatureError:
        print("[Auth Service] Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"[Auth Service] Invalid token: {e}")
        return None

# ---- OAuth Flow ----
@app.get("/auth/login")
async def login(request: Request):
    """Initiate GitHub OAuth flow"""
    # Demo mode: skip OAuth and set demo user directly
    if DEMO_MODE:
        jwt_token = create_jwt_token(0, "demo_user")
        response = RedirectResponse("/")
        response.set_cookie(
            key="session",
            value=jwt_token,
            httponly=True,
            secure=False,  # Allow HTTP in demo mode
            samesite="lax",
            max_age=SESSION_DURATION_HOURS * 3600
        )
        return response

    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)

    # Build GitHub OAuth URL
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": f"https://{PUBLIC_DOMAIN}/auth/callback",
        "scope": "read:user",
        "state": state
    }
    github_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"

    # Store state in session for validation
    response = RedirectResponse(github_url)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600  # 10 minutes
    )

    return response

@app.get("/auth/callback")
async def callback(
    code: str,
    state: str,
    oauth_state: Optional[str] = Cookie(None)
):
    """Handle GitHub OAuth callback"""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    # Validate state (CSRF protection)
    if state != oauth_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"https://{PUBLIC_DOMAIN}/auth/callback"
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
        
        # Get user info from GitHub
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_data = user_response.json()
        github_id = user_data.get("id")
        github_username = user_data.get("login")
        
        if not github_id or not github_username:
            raise HTTPException(status_code=400, detail="Invalid user data from GitHub")
        
        # Check if user is allowed
        if ALLOWED_GITHUB_USERNAME and github_username != ALLOWED_GITHUB_USERNAME:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. Only '{ALLOWED_GITHUB_USERNAME}' is allowed to access this Luna instance."
            )
    
    # Create JWT token
    jwt_token = create_jwt_token(github_id, github_username)
    
    # Redirect to Hub UI with JWT cookie
    response = RedirectResponse("/")
    response.set_cookie(
        key="session",
        value=jwt_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_DURATION_HOURS * 3600
    )
    response.delete_cookie("oauth_state")
    
    return response

@app.post("/auth/logout")
async def logout(session: Optional[str] = Cookie(None)):
    """Logout user (clear JWT cookie)"""
    response = JSONResponse({"success": True})
    response.delete_cookie("session")
    return response

@app.get("/auth/me")
async def get_current_user(session: Optional[str] = Cookie(None)):
    """Get current user info from JWT"""
    # Demo mode: always return authenticated demo user
    if DEMO_MODE:
        return {
            "github_id": 0,
            "username": "demo_user",
            "authenticated": True,
            "demo_mode": True
        }

    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = validate_jwt_token(session)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "github_id": user["github_id"],
        "username": user["github_username"],
        "authenticated": True
    }

@app.get("/healthz")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

# ---- Startup ----
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("AUTH_SERVICE_PORT", "8765"))

    print(f"[Auth Service] Starting on port {port}")
    if DEMO_MODE:
        print(f"[Auth Service] ⚠️  DEMO MODE: Authentication BYPASSED")
    else:
        print(f"[Auth Service] GitHub OAuth: {'configured' if GITHUB_CLIENT_ID else 'NOT configured'}")
        print(f"[Auth Service] Authentication: Stateless JWT (no database)")
    print(f"[Auth Service] Session duration: {SESSION_DURATION_HOURS} hours")

    uvicorn.run(app, host="127.0.0.1", port=port)

