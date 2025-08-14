from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json
from datetime import datetime
import random
import requests
import psycopg2
import psycopg2.extras
try:
    from core.shared.db_config import get_connection
except ModuleNotFoundError:
    try:
        from db_config import get_connection  # root-level shim
    except ModuleNotFoundError:
        import sys as _sys
        import os as _os
        # Add repo root to sys.path
        _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..', '..')))
        try:
            from core.shared.db_config import get_connection
        except ModuleNotFoundError:
            from db_config import get_connection  # type: ignore

try:
    from extensions.chefbyte.code.chefbyte.db.db_functions import init_tables
except ModuleNotFoundError:
    import sys as _sys2
    import os as _os2
    # Add repo root to sys.path
    _sys2.path.insert(0, _os2.path.abspath(_os2.path.join(_os2.path.dirname(__file__), '..', '..', '..', '..')))
    from extensions.chefbyte.code.chefbyte.db.db_functions import init_tables

# Paths and config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
# Using unified Postgres DB via root db_config.py
PUSH_SERVER_URL = os.environ.get("CHEFBYTE_PUSH_URL", "http://localhost:8010")

app = FastAPI(title="ChefByte Web")

static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


def get_db_connection():
    # RealDictCursor for dict-like rows
    conn = get_connection(autocommit=False)
    return conn


def fetch_table(table_name: str):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(f"SELECT * FROM {table_name}")
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception:
        # Table might not exist yet; return empty list for UI rendering
        return []


def _json_or_none(text: str | None):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def compute_days_until(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None
    return (dt - datetime.now()).days
@app.on_event("startup")
def ensure_schema():
    # Create tables if they don't exist
    try:
        db, _ = init_tables(verbose=False)
        if db and db.conn:
            db.disconnect(verbose=False)
    except Exception:
        # If init fails, routes will still show DB disconnected
        pass

    # ChefByte does not manage workout days; no additional day seeding here



@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return RedirectResponse(url="/stats")


def get_status():
    # DB status
    try:
        with get_db_connection() as conn:
            with conn.cursor() as _:
                pass
        db_status = True
    except Exception:
        db_status = False
    # Push status removed to avoid reliance on push tools
    return {"db": db_status}


@app.get("/stats", response_class=HTMLResponse)
def stats(request: Request):
    tables = [
        "inventory",
        "taste_profile",
        "saved_meals",
        "new_meal_ideas",
        "daily_planner",
        "shopping_list",
        "ingredients_foods",
        "saved_meals_instock_ids",
        "new_meal_ideas_instock_ids",
    ]
    counts: dict[str, int] = {}
    with get_db_connection() as conn:
        cur = conn.cursor()
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
            except Exception:
                counts[t] = 0
    return templates.TemplateResponse(
        "stats.html",
        {"request": request, "counts": counts, "status": get_status(), "page": "stats"},
    )


@app.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request):
    items = fetch_table("inventory")
    for item in items:
        item["days_until_expiry"] = compute_days_until(item.get("expiration"))
    return templates.TemplateResponse(
        "inventory.html",
        {"request": request, "items": items, "status": get_status(), "page": "inventory"},
    )


@app.post("/inventory/add")
def inventory_add(name: str = Form(...), quantity: str = Form(...), expiration: str = Form(None), ingredient_food_id: int | None = Form(None)):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO inventory (name, quantity, expiration, ingredient_food_id) VALUES (%s, %s, %s, %s)",
            (name, quantity, expiration or None, ingredient_food_id if ingredient_food_id else None),
        )
        conn.commit()
    return RedirectResponse(url="/inventory", status_code=303)


@app.post("/inventory/delete/{item_id}")
def inventory_delete(item_id: int):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory WHERE id = %s", (item_id,))
        conn.commit()
    return RedirectResponse(url="/inventory", status_code=303)


@app.post("/inventory/update/{item_id}")
def inventory_update(
    item_id: int,
    name: str = Form(...),
    quantity: str = Form(...),
    expiration: str = Form(None),
    ingredient_food_id: int | None = Form(None),
):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE inventory SET name = %s, quantity = %s, expiration = %s, ingredient_food_id = %s WHERE id = %s",
            (name, quantity, expiration or None, ingredient_food_id if ingredient_food_id else None, item_id),
        )
        conn.commit()
    return RedirectResponse(url="/inventory", status_code=303)


@app.get("/ingredients", response_class=HTMLResponse)
def ingredients_page(request: Request):
    items = fetch_table("ingredients_foods")
    return templates.TemplateResponse(
        "ingredients.html",
        {"request": request, "items": items, "status": get_status(), "page": "ingredients"},
    )


@app.post("/ingredients/add")
def ingredients_add(name: str = Form(...), min_amount_to_buy: float = Form(...), walmart_link: str = Form(None)):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ingredients_foods (name, min_amount_to_buy, walmart_link) VALUES (%s, %s, %s)",
            (name, min_amount_to_buy, walmart_link or None),
        )
        conn.commit()
    return RedirectResponse(url="/ingredients", status_code=303)


@app.post("/ingredients/delete/{food_id}")
def ingredients_delete(food_id: int):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM ingredients_foods WHERE id = %s", (food_id,))
        conn.commit()
    return RedirectResponse(url="/ingredients", status_code=303)


@app.post("/ingredients/update/{food_id}")
def ingredients_update(
    food_id: int,
    name: str = Form(...),
    min_amount_to_buy: float = Form(...),
    walmart_link: str = Form(None),
):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE ingredients_foods SET name = %s, min_amount_to_buy = %s, walmart_link = %s WHERE id = %s",
            (name, min_amount_to_buy, walmart_link or None, food_id),
        )
        conn.commit()
    return RedirectResponse(url="/ingredients", status_code=303)


@app.get("/saved-meals", response_class=HTMLResponse)
def saved_meals_page(request: Request):
    items = fetch_table("saved_meals")
    # parse ingredients JSON for display
    for m in items:
        try:
            m["ingredients_parsed"] = json.loads(m.get("ingredients") or "null") or []
        except Exception:
            m["ingredients_parsed"] = []
    return templates.TemplateResponse(
        "saved_meals.html",
        {"request": request, "items": items, "status": get_status(), "page": "saved-meals"},
    )


@app.post("/saved-meals/add")
def saved_meal_add(name: str = Form(...), prep_time_minutes: int = Form(...), ingredients: str = Form(""), recipe: str = Form(...)):
    try:
        # keep raw JSON string, ensure it parses or store as-is
        if ingredients:
            _ = json.loads(ingredients)
    except Exception:
        raise HTTPException(status_code=400, detail="Ingredients must be valid JSON")
    with get_db_connection() as conn:
        cur = conn.cursor()
        # Generate unique ID in 10000-19999 range
        meal_id = None
        while True:
            candidate = random.randint(10000, 19999)
            cur.execute("SELECT 1 FROM saved_meals WHERE id = %s", (candidate,))
            if cur.fetchone() is None:
                meal_id = candidate
                break
        cur.execute(
            "INSERT INTO saved_meals (id, name, prep_time_minutes, ingredients, recipe) VALUES (%s, %s, %s, %s, %s)",
            (meal_id, name, prep_time_minutes, ingredients or json.dumps([]), recipe),
        )
        conn.commit()
    return RedirectResponse(url="/saved-meals", status_code=303)


@app.post("/saved-meals/delete/{meal_id}")
def saved_meal_delete(meal_id: int):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM saved_meals WHERE id = %s", (meal_id,))
        conn.commit()
    return RedirectResponse(url="/saved-meals", status_code=303)


@app.post("/saved-meals/update/{meal_id}")
def saved_meal_update(
    meal_id: int,
    name: str = Form(...),
    prep_time_minutes: int = Form(...),
    ingredients: str = Form(""),
    recipe: str = Form(...),
):
    # Validate ingredients JSON
    if ingredients:
        try:
            json.loads(ingredients)
        except Exception:
            raise HTTPException(status_code=400, detail="Ingredients must be valid JSON")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE saved_meals SET name = %s, prep_time_minutes = %s, ingredients = %s, recipe = %s WHERE id = %s",
            (name, prep_time_minutes, ingredients or json.dumps([]), recipe, meal_id),
        )
        conn.commit()
    return RedirectResponse(url="/saved-meals", status_code=303)


@app.get("/shopping-list", response_class=HTMLResponse)
def shopping_list_page(request: Request):
    shopping = fetch_table("shopping_list")
    ingredients = fetch_table("ingredients_foods")
    idx = {i["id"]: i for i in ingredients}
    rows = []
    for s in shopping:
        info = idx.get(s["id"]) or {}
        rows.append(
            {
                "id": s["id"],
                "name": info.get("name", f"ID {s['id']}"),
                "amount": s["amount"],
                "min_amount": info.get("min_amount_to_buy"),
                "walmart_link": info.get("walmart_link"),
            }
        )
    return templates.TemplateResponse(
        "shopping_list.html",
        {"request": request, "items": rows, "ingredients": ingredients, "status": get_status(), "page": "shopping"},
    )


@app.post("/shopping-list/add")
def shopping_list_add(ingredient_id: int = Form(...), amount: float = Form(...)):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO shopping_list (id, amount) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET amount = EXCLUDED.amount",
            (ingredient_id, amount),
        )
        conn.commit()
    return RedirectResponse(url="/shopping-list", status_code=303)


@app.post("/shopping-list/delete/{ingredient_id}")
def shopping_list_delete(ingredient_id: int):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM shopping_list WHERE id = %s", (ingredient_id,))
        conn.commit()
    return RedirectResponse(url="/shopping-list", status_code=303)


@app.post("/shopping-list/update/{ingredient_id}")
def shopping_list_update(ingredient_id: int, amount: float = Form(...)):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE shopping_list SET amount = %s WHERE id = %s", (amount, ingredient_id))
        conn.commit()
    return RedirectResponse(url="/shopping-list", status_code=303)


@app.get("/planner", response_class=HTMLResponse)
def planner_page(request: Request):
    items = fetch_table("daily_planner")
    # sort by day asc
    try:
        items.sort(key=lambda r: r["day"])  # YYYY-MM-DD strings sort lexically
    except Exception:
        pass
    return templates.TemplateResponse(
        "planner.html",
        {"request": request, "items": items, "status": get_status(), "page": "planner"},
    )


@app.post("/planner/add")
def planner_add(day: str = Form(...), notes: str = Form(""), meal_ids: str = Form("")):
    try:
        meal_ids_list = [int(x.strip()) for x in meal_ids.split(",") if x.strip()] if meal_ids else []
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid meal IDs format")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO daily_planner (day, notes, meal_ids) VALUES (%s, %s, %s) ON CONFLICT (day) DO UPDATE SET notes = EXCLUDED.notes, meal_ids = EXCLUDED.meal_ids",
            (day, notes, json.dumps(meal_ids_list)),
        )
        conn.commit()
    return RedirectResponse(url="/planner", status_code=303)


@app.post("/planner/delete/{day}")
def planner_delete(day: str):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM daily_planner WHERE day = %s", (day,))
        conn.commit()
    return RedirectResponse(url="/planner", status_code=303)


@app.post("/planner/update/{day}")
def planner_update(day: str, notes: str = Form(""), meal_ids: str = Form("")):
    try:
        meal_ids_list = [int(x.strip()) for x in meal_ids.split(",") if x.strip()] if meal_ids else []
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid meal IDs format")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE daily_planner SET notes = %s, meal_ids = %s WHERE day = %s",
            (notes, json.dumps(meal_ids_list), day),
        )
        conn.commit()
    return RedirectResponse(url="/planner", status_code=303)


@app.get("/taste", response_class=HTMLResponse)
def taste_page(request: Request):
    rows = fetch_table("taste_profile")
    profile = rows[0]["profile"] if rows else ""
    return templates.TemplateResponse(
        "taste.html",
        {"request": request, "profile": profile, "status": get_status(), "page": "taste"},
    )


@app.post("/taste/update")
def taste_update(profile: str = Form(...)):
    # Direct DB update to avoid push tools dependency
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO taste_profile (profile) VALUES (%s) ON CONFLICT (profile) DO UPDATE SET profile = EXCLUDED.profile",
            (profile,)
        )
        conn.commit()
    return RedirectResponse(url="/taste", status_code=303)


@app.get("/ideas", response_class=HTMLResponse)
def ideas_page(request: Request):
    items = fetch_table("new_meal_ideas")
    for m in items:
        try:
            m["ingredients_parsed"] = json.loads(m.get("ingredients") or "null") or []
        except Exception:
            m["ingredients_parsed"] = []
    return templates.TemplateResponse(
        "ideas.html",
        {"request": request, "items": items, "status": get_status(), "page": "ideas"},
    )


@app.post("/ideas/save/{idea_id}")
def idea_save(idea_id: int):
    # Copy a new idea into saved_meals directly
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, name, prep_time, ingredients, recipe FROM new_meal_ideas WHERE id = %s", (idea_id,))
        row = cur.fetchone()
        if row:
            # generate a unique saved_meal id in [10000,19999]
            while True:
                candidate = random.randint(10000, 19999)
                cur2 = conn.cursor()
                cur2.execute("SELECT 1 FROM saved_meals WHERE id = %s", (candidate,))
                exists = cur2.fetchone()
                cur2.close()
                if not exists:
                    break
            cur.execute(
                "INSERT INTO saved_meals (id, name, prep_time_minutes, ingredients, recipe) VALUES (%s, %s, %s, %s, %s)",
                (candidate, row["name"], row["prep_time"], row["ingredients"], row["recipe"]),
            )
            conn.commit()
    return RedirectResponse(url="/ideas", status_code=303)


@app.get("/instock", response_class=HTMLResponse)
def instock_page(request: Request):
    saved_instock = fetch_table("saved_meals_instock_ids")
    ideas_instock = fetch_table("new_meal_ideas_instock_ids")
    saved_meals = {row["id"]: row for row in fetch_table("saved_meals")}
    ideas = {row["id"]: row for row in fetch_table("new_meal_ideas")}

    for row in saved_meals.values():
        try:
            row["ingredients_parsed"] = json.loads(row.get("ingredients") or "null") or []
        except Exception:
            row["ingredients_parsed"] = []
    for row in ideas.values():
        try:
            row["ingredients_parsed"] = json.loads(row.get("ingredients") or "null") or []
        except Exception:
            row["ingredients_parsed"] = []

    return templates.TemplateResponse(
        "instock.html",
        {
            "request": request,
            "saved_instock": saved_instock,
            "ideas_instock": ideas_instock,
            "saved_meals": saved_meals,
            "ideas": ideas,
            "status": get_status(),
            "page": "instock",
        },
    )


@app.post("/instock/saved/remove/{meal_id}")
def instock_saved_remove(meal_id: int):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM saved_meals_instock_ids WHERE id = %s", (meal_id,))
        conn.commit()
    return RedirectResponse(url="/instock", status_code=303)


@app.post("/instock/ideas/remove/{idea_id}")
def instock_ideas_remove(idea_id: int):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM new_meal_ideas_instock_ids WHERE id = %s", (idea_id,))
        conn.commit()
    return RedirectResponse(url="/instock", status_code=303)


@app.get("/health")
def health():
    return JSONResponse({"ok": True})


