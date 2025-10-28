"""Auth Service for Luna Hub UI - GitHub OAuth Authentication

Provides GitHub OAuth login flow for the Hub UI.
Uses the same GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET as the MCP server.
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
PUBLIC_DOMAIN = os.getenv("PUBLIC_DOMAIN", "localhost:5173")
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
SESSION_DURATION_HOURS = int(os.getenv("SESSION_DURATION_HOURS", "24"))

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

# Validate configuration
if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
    print("[Auth Service] WARNING: GitHub OAuth not configured")
    print("[Auth Service] Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env")
    print("[Auth Service] Auth service will start but OAuth will not work")

if not DATABASE_URL:
    print("[Auth Service] WARNING: DATABASE_URL not set, using in-memory sessions")
    DATABASE_URL = None

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

# ---- In-Memory Session Store (fallback if no DB) ----
SESSIONS: Dict[str, Dict[str, Any]] = {}

# ---- Database Functions ----
def get_db_connection():
    """Get database connection if available"""
    if not DATABASE_URL:
        return None
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"[Auth Service] Database connection failed: {e}")
        return None

def create_or_update_user(github_id: int, username: str, access_token: str) -> Optional[int]:
    """Create or update user in database, return user_id"""
    conn = get_db_connection()
    if not conn:
        # Store in memory
        user_id = github_id
        return user_id
    
    try:
        with conn.cursor() as cur:
            # Upsert user
            cur.execute("""
                INSERT INTO users (github_id, github_username, github_access_token, last_login)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (github_id) DO UPDATE
                SET github_username = EXCLUDED.github_username,
                    github_access_token = EXCLUDED.github_access_token,
                    last_login = NOW()
                RETURNING id
            """, (github_id, username, access_token))
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
    except Exception as e:
        print(f"[Auth Service] Database error: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def create_session(user_id: int, github_username: str) -> str:
    """Create a new session and return session token"""
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    
    conn = get_db_connection()
    if not conn:
        # Store in memory
        SESSIONS[session_token] = {
            "user_id": user_id,
            "github_username": github_username,
            "expires_at": expires_at,
            "created_at": datetime.utcnow()
        }
        return session_token
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sessions (id, user_id, expires_at)
                VALUES (%s, %s, %s)
            """, (session_token, user_id, expires_at))
            conn.commit()
        return session_token
    except Exception as e:
        print(f"[Auth Service] Database error: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def validate_session(session_token: str) -> Optional[Dict[str, Any]]:
    """Validate session and return user info"""
    if not session_token:
        return None
    
    conn = get_db_connection()
    if not conn:
        # Check in-memory
        session = SESSIONS.get(session_token)
        if not session:
            return None
        
        if datetime.utcnow() > session["expires_at"]:
            del SESSIONS[session_token]
            return None
        
        return session
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.user_id, u.github_username, s.expires_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.id = %s AND s.expires_at > NOW()
            """, (session_token,))
            row = cur.fetchone()
            if not row:
                return None
            
            return {
                "user_id": row[0],
                "github_username": row[1],
                "expires_at": row[2]
            }
    except Exception as e:
        print(f"[Auth Service] Database error: {e}")
        return None
    finally:
        conn.close()

def delete_session(session_token: str):
    """Delete a session"""
    if not session_token:
        return
    
    conn = get_db_connection()
    if not conn:
        # Delete from memory
        SESSIONS.pop(session_token, None)
        return
    
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE id = %s", (session_token,))
            conn.commit()
    except Exception as e:
        print(f"[Auth Service] Database error: {e}")
        conn.rollback()
    finally:
        conn.close()

# ---- OAuth Flow ----
@app.get("/auth/login")
async def login(request: Request):
    """Initiate GitHub OAuth flow"""
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
    
    # Create or update user in database
    user_id = create_or_update_user(github_id, github_username, access_token)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    # Create session
    session_token = create_session(user_id, github_username)
    if not session_token:
        raise HTTPException(status_code=500, detail="Failed to create session")
    
    # Redirect to Hub UI with session cookie
    response = RedirectResponse("/")
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_DURATION_HOURS * 3600
    )
    response.delete_cookie("oauth_state")
    
    return response

@app.post("/auth/logout")
async def logout(session: Optional[str] = Cookie(None)):
    """Logout user and delete session"""
    if session:
        delete_session(session)
    
    response = JSONResponse({"success": True})
    response.delete_cookie("session")
    return response

@app.get("/auth/me")
async def get_current_user(session: Optional[str] = Cookie(None)):
    """Get current user info"""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = validate_session(session)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return {
        "user_id": user["user_id"],
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
    print(f"[Auth Service] GitHub OAuth: {'configured' if GITHUB_CLIENT_ID else 'NOT configured'}")
    print(f"[Auth Service] Database: {'connected' if DATABASE_URL else 'in-memory'}")
    print(f"[Auth Service] Session duration: {SESSION_DURATION_HOURS} hours")
    
    uvicorn.run(app, host="127.0.0.1", port=port)

