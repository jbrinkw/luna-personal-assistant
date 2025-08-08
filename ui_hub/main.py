from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app = FastAPI(title="Agent Hub")

static_dir = os.path.join(BASE_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def parse_agents_from_env() -> list[dict]:
    # Format: AGENT_LINKS="ChefByte:http://localhost:8050,CoachByte:http://localhost:3001"
    raw = os.environ.get("AGENT_LINKS")
    agents: list[dict] = []
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for p in parts:
            if ":" in p:
                name, url = p.split(":", 1)
                slug = slugify(name)
                agents.append({"name": name.strip(), "slug": slug, "url": url.strip()})
    if not agents:
        # defaults
        agents = [
            {"name": "ChefByte", "slug": "chefbyte", "url": "http://localhost:8050"},
            {"name": "CoachByte", "slug": "coachbyte", "url": "http://localhost:3001"},
        ]
    return agents


def slugify(name: str) -> str:
    return "".join(ch.lower() for ch in name if ch.isalnum())


def get_agents():
    # Recompute each request so env changes are picked up in dev
    return parse_agents_from_env()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    agents = get_agents()
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "agents": agents, "current_slug": None},
    )


@app.get("/app/{slug}", response_class=HTMLResponse)
def app_view(slug: str, request: Request):
    agents = get_agents()
    agent = next((a for a in agents if a["slug"] == slug), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return templates.TemplateResponse(
        "app.html",
        {
            "request": request,
            "agents": agents,
            "current_slug": slug,
            "agent": agent,
        },
    )


@app.get("/health")
def health():
    return JSONResponse({"ok": True})



