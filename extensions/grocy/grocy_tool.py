"""Grocy extension — pantry, shopping list, recipes, and meal planning.

Exposes tools backed by the Grocy REST API via `extensions.grocy.backend.GrocyClient`.
Environment variables (dotenv supported):
- GROCY_API_KEY (required)
- GROCY_BASE_URL (default http://192.168.0.185/api)
- GROCY_DEFAULT_LOCATION_ID, GROCY_DEFAULT_QU_ID_PURCHASE, GROCY_DEFAULT_QU_ID_STOCK (optional defaults)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

try:  # pragma: no cover
	from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
	load_dotenv = None  # type: ignore

if load_dotenv is not None:
	load_dotenv()

from pydantic import BaseModel, Field

from extensions.grocy.backend import (
	GrocyClient,
	extract_name,
	extract_quantity,
	extract_expiry,
)


NAME = "Grocy"

SYSTEM_PROMPT = """
Pantry, shopping list, recipes, and meal planning using Grocy.

You can:
- List inventory with simplified name/quantity/expiry.
- Increase/consume product quantities by product_id.
- Manage shopping list (list, add, remove, clear).
- List products (id → name) to help choose ids.
- Ensure a product by name exists (create with sensible defaults if missing).
- Manage meal plan entries and sections (list, create, update, delete).
- List recipes, get a recipe, create/update/delete recipes; manage ingredients.
- Find currently cookable recipes according to Grocy's fulfillment logic.

Return structured JSON using the provided models.
""".strip()


class OperationResult(BaseModel):
	success: bool
	message: str


class InventoryItem(BaseModel):
	name: Optional[str]
	quantity: Optional[float]
	expiry: Optional[str]


class InventoryList(BaseModel):
	items: List[InventoryItem] = Field(default_factory=list)


class StatusMessage(BaseModel):
	status: str
	message: str


class StatusWithId(StatusMessage):
	id: Optional[int] = None


class ShoppingListItem(BaseModel):
	product_id: Optional[int]
	name: Optional[str]
	quantity: Optional[float]


class ShoppingList(BaseModel):
	items: List[ShoppingListItem] = Field(default_factory=list)


class Product(BaseModel):
	id: int
	name: str


class ProductsList(BaseModel):
	items: List[Product] = Field(default_factory=list)


class EnsureProductResult(BaseModel):
	status: str
	message: str
	product_id: int
	created: bool


class MealPlanEntry(BaseModel):
	id: Optional[int] = None
	day: Optional[str] = None
	recipe_id: Optional[int] = None
	product_id: Optional[int] = None
	servings: Optional[int] = None
	amount: Optional[float] = None
	qu_id: Optional[int] = None
	meal_plan_section_id: Optional[int] = None
	note: Optional[str] = None


class MealPlan(BaseModel):
	items: List[MealPlanEntry] = Field(default_factory=list)


class MealPlanSection(BaseModel):
	id: Optional[int] = None
	name: Optional[str] = None
	sort_number: Optional[int] = None


class MealPlanSections(BaseModel):
	items: List[MealPlanSection] = Field(default_factory=list)


class CookableRecipe(BaseModel):
	id: int
	name: Optional[str] = None
	possible_servings: Optional[float] = None


class Recipes(BaseModel):
	items: List[CookableRecipe] = Field(default_factory=list)


class Recipe(BaseModel):
	id: int
	name: Optional[str] = None
	base_servings: Optional[int] = None
	description: Optional[str] = None


# Ensure forward refs are resolved
OperationResult.model_rebuild()
InventoryItem.model_rebuild()
InventoryList.model_rebuild()
StatusMessage.model_rebuild()
StatusWithId.model_rebuild()
ShoppingListItem.model_rebuild()
ShoppingList.model_rebuild()
Product.model_rebuild()
ProductsList.model_rebuild()
EnsureProductResult.model_rebuild()
MealPlanEntry.model_rebuild()
MealPlan.model_rebuild()
MealPlanSection.model_rebuild()
MealPlanSections.model_rebuild()
CookableRecipe.model_rebuild()
Recipes.model_rebuild()
Recipe.model_rebuild()


# ---- Tools ----

def GROCERY_GET_inventory(base_url: Optional[str] = None) -> InventoryList | OperationResult:
	"""List current inventory as name, quantity, expiry.
	Example Prompt: Show pantry inventory.
	Example Response: {"items": [{"name": "Milk", "quantity": 1, "expiry": "2025-09-10"}]}
	Example Args: {"base_url": "string[optional override base url]"}
	"""
	try:
		client = GrocyClient(base_url=base_url)
		raw_items = client.get_inventory()
		items: List[InventoryItem] = []
		for it in raw_items:
			items.append(
				InventoryItem(
					name=extract_name(it),
					quantity=extract_quantity(it),
					expiry=extract_expiry(it),
				)
			)
		return InventoryList(items=items)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_ACTION_increase_quantity(product_id: int, quantity: float, base_url: Optional[str] = None) -> StatusMessage:
	"""Increase product stock amount by product_id and quantity.
	Example Prompt: Add 2 to product 5.
	Example Response: {"status": "ok", "message": "Increased product 5 by 2.0"}
	Example Args: {"product_id": 5, "quantity": 2}
	"""
	client = GrocyClient(base_url=base_url)
	client.add_product_quantity(product_id=product_id, quantity=quantity)
	return StatusMessage(status="ok", message=f"Increased product {int(product_id)} by {float(quantity)}")


def GROCERY_ACTION_consume_quantity(product_id: int, quantity: float, base_url: Optional[str] = None) -> StatusMessage:
	"""Consume product stock amount by product_id and quantity.
	Example Prompt: Use 1.5 of product 5.
	Example Response: {"status": "ok", "message": "Consumed product 5 by 1.5"}
	"""
	client = GrocyClient(base_url=base_url)
	client.consume_product_quantity(product_id=product_id, quantity=quantity)
	return StatusMessage(status="ok", message=f"Consumed product {int(product_id)} by {float(quantity)}")


def GROCERY_GET_shopping_list(shopping_list_id: Optional[int] = 1, base_url: Optional[str] = None) -> ShoppingList | OperationResult:
	"""List shopping list items with resolved product names.
	Example Prompt: Show shopping list.
	Example Response: {"items": [{"product_id": 5, "name": "Milk", "quantity": 2}]}
	Example Args: {"shopping_list_id": 1}
	"""
	try:
		client = GrocyClient(base_url=base_url)
		items = client.get_shopping_list_items(shopping_list_id=shopping_list_id)
		try:
			name_map = client.get_product_name_map()
		except Exception:
			name_map = {}
		out: List[ShoppingListItem] = []
		for it in items:
			pid_raw = it.get("product_id")
			quantity_raw = it.get("amount")
			pid = int(pid_raw) if isinstance(pid_raw, (int, float, str)) and str(pid_raw).isdigit() else None
			quantity = float(quantity_raw) if isinstance(quantity_raw, (int, float)) else None
			name = name_map.get(pid) if isinstance(pid, int) else None
			out.append(ShoppingListItem(product_id=pid, name=name, quantity=quantity))
		return ShoppingList(items=out)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_ACTION_shopping_list_add(product_id: int, amount: float, shopping_list_id: Optional[int] = 1, base_url: Optional[str] = None) -> StatusMessage:
	client = GrocyClient(base_url=base_url)
	client.shopping_list_add_product(product_id=product_id, amount=amount, shopping_list_id=shopping_list_id)
	return StatusMessage(status="ok", message=f"Added product {int(product_id)} x {float(amount)} to shopping list")


def GROCERY_ACTION_shopping_list_remove(product_id: int, amount: float, shopping_list_id: Optional[int] = 1, base_url: Optional[str] = None) -> StatusMessage:
	client = GrocyClient(base_url=base_url)
	client.shopping_list_remove_product(product_id=product_id, amount=amount, shopping_list_id=shopping_list_id)
	return StatusMessage(status="ok", message=f"Removed product {int(product_id)} x {float(amount)} from shopping list")


def GROCERY_ACTION_shopping_list_clear(shopping_list_id: Optional[int] = 1, base_url: Optional[str] = None) -> StatusMessage:
	client = GrocyClient(base_url=base_url)
	client.shopping_list_clear(shopping_list_id=shopping_list_id)
	return StatusMessage(status="ok", message=f"Cleared shopping list {int(shopping_list_id) if shopping_list_id is not None else ''}")


def GROCERY_GET_products(base_url: Optional[str] = None) -> ProductsList | OperationResult:
	"""List products as id/name pairs, sorted by id."""
	try:
		client = GrocyClient(base_url=base_url)
		id_to_name = client.get_product_name_map()
		items: List[Product] = []
		for pid, name in sorted(id_to_name.items(), key=lambda kv: kv[0]):
			try:
				items.append(Product(id=int(pid), name=str(name)))
			except Exception:
				continue
		return ProductsList(items=items)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_ACTION_create_product(product_fields: Dict[str, Any], base_url: Optional[str] = None) -> StatusWithId:
	client = GrocyClient(base_url=base_url)
	fields: Dict[str, Any] = dict(product_fields or {})
	if not fields.get("name"):
		raise ValueError("'name' is required to create a product")
	fields.setdefault("location_id", int(os.getenv("GROCY_DEFAULT_LOCATION_ID", "2")))
	fields.setdefault("qu_id_purchase", int(os.getenv("GROCY_DEFAULT_QU_ID_PURCHASE", "2")))
	fields.setdefault("qu_id_stock", int(os.getenv("GROCY_DEFAULT_QU_ID_STOCK", "2")))
	client.validate_product_required_ids(fields)
	resp = client.create_product(fields)
	pid = client._extract_created_id_from_response(resp)
	if not isinstance(pid, int):
		pid = client.find_product_id_by_name(fields["name"]) or None
	return StatusWithId(status="ok", message=f"Created product '{fields['name']}'", id=int(pid) if isinstance(pid, int) else None)


def GROCERY_ACTION_ensure_product_exists(name: str, create_fields: Optional[Dict[str, Any]] = None, base_url: Optional[str] = None) -> EnsureProductResult:
	client = GrocyClient(base_url=base_url)
	existing = client.find_product_id_by_name(name)
	if isinstance(existing, int):
		return EnsureProductResult(status="ok", message=f"Product '{name}' already exists", product_id=int(existing), created=False)
	new_id = client.ensure_product_exists(name=name, create_fields=create_fields)
	return EnsureProductResult(status="ok", message=f"Created product '{name}'", product_id=int(new_id), created=True)


def GROCERY_GET_meal_plan(start: Optional[str] = None, end: Optional[str] = None, base_url: Optional[str] = None) -> MealPlan | OperationResult:
	try:
		client = GrocyClient(base_url=base_url)
		items = client.list_meal_plan()
		def _in_range(day: Optional[str]) -> bool:
			if not isinstance(day, str) or not day:
				return False if (start or end) else True
			if start and day < start:
				return False
			if end and day > end:
				return False
			return True
		out: List[MealPlanEntry] = []
		for it in items:
			if _in_range(it.get("day")):
				out.append(MealPlanEntry(
					id=it.get("id"),
					day=it.get("day"),
					recipe_id=it.get("recipe_id"),
					product_id=it.get("product_id"),
					servings=it.get("servings"),
					amount=it.get("amount"),
					qu_id=it.get("qu_id"),
					meal_plan_section_id=it.get("meal_plan_section_id"),
					note=it.get("note"),
				))
		return MealPlan(items=out)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_ACTION_add_meal(fields: Dict[str, Any], base_url: Optional[str] = None) -> StatusMessage:
	client = GrocyClient(base_url=base_url)
	client.create_meal_plan_entry(dict(fields or {}))
	return StatusMessage(status="ok", message="Meal plan entry created")


def GROCERY_UPDATE_meal_plan(entry_id: int, fields: Dict[str, Any], base_url: Optional[str] = None) -> StatusMessage:
	client = GrocyClient(base_url=base_url)
	client.update_meal_plan_entry(entry_id=int(entry_id), fields=dict(fields or {}))
	return StatusMessage(status="ok", message=f"Meal plan entry {int(entry_id)} updated")


def GROCERY_ACTION_delete_meal(entry_id: int, base_url: Optional[str] = None) -> StatusMessage:
	client = GrocyClient(base_url=base_url)
	client.delete_meal_plan_entry(int(entry_id))
	return StatusMessage(status="ok", message=f"Meal plan entry {int(entry_id)} deleted")


def GROCERY_GET_meal_plan_sections(base_url: Optional[str] = None) -> MealPlanSections | OperationResult:
	try:
		client = GrocyClient(base_url=base_url)
		raw = client.list_meal_plan_sections()
		out: List[MealPlanSection] = []
		for it in raw:
			try:
				out.append(
					MealPlanSection(
						id=(int(it.get("id")) if isinstance(it.get("id"), (int, float)) else None),
						name=(str(it.get("name")) if isinstance(it.get("name"), str) else None),
						sort_number=(int(it.get("sort_number")) if isinstance(it.get("sort_number"), (int, float)) else None),
					)
				)
			except Exception:
				continue
		return MealPlanSections(items=out)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_GET_cookable_recipes(desired_servings: Optional[float] = None, consider_shopping_list: bool = False, base_url: Optional[str] = None) -> Recipes | OperationResult:
	try:
		client = GrocyClient(base_url=base_url)
		items = client.list_cookable_recipes(desired_servings=desired_servings, consider_shopping_list=consider_shopping_list)
		out: List[CookableRecipe] = []
		for it in items:
			try:
				out.append(CookableRecipe(
					id=int(it.get("id")),
					name=it.get("name"),
					possible_servings=(float(it.get("possible_servings")) if isinstance(it.get("possible_servings"), (int, float)) else None),
				))
			except Exception:
				continue
		return Recipes(items=out)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_GET_recipes(base_url: Optional[str] = None) -> Recipes | OperationResult:
	try:
		client = GrocyClient(base_url=base_url)
		items = client.get_recipes()
		out: List[CookableRecipe] = []
		for it in items:
			try:
				out.append(CookableRecipe(
					id=int(it.get("id")) if isinstance(it.get("id"), (int, float)) else 0,
					name=it.get("name") if isinstance(it.get("name"), str) else None,
					possible_servings=None,
				))
			except Exception:
				continue
		return Recipes(items=out)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_GET_recipe(recipe_id: int, base_url: Optional[str] = None) -> Recipe | OperationResult:
	try:
		client = GrocyClient(base_url=base_url)
		raw = client.get_recipe(int(recipe_id))
		return Recipe(
			id=int(raw.get("id")) if isinstance(raw.get("id"), (int, float)) else int(recipe_id),
			name=raw.get("name") if isinstance(raw.get("name"), str) else None,
			base_servings=(int(raw.get("base_servings")) if isinstance(raw.get("base_servings"), (int, float)) else None),
			description=(str(raw.get("description")) if isinstance(raw.get("description"), str) else None),
		)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_ACTION_create_recipe(fields: Dict[str, Any], base_url: Optional[str] = None) -> StatusWithId:
	client = GrocyClient(base_url=base_url)
	payload = dict(fields or {})
	if not payload.get("name"):
		raise ValueError("'name' is required to create a recipe")
	resp = client.create_recipe(payload)
	rid = client._extract_created_id_from_response(resp)
	if not isinstance(rid, int):
		try:
			rid = int(resp.get("id")) if isinstance(resp, dict) and isinstance(resp.get("id"), (int, float)) else None
		except Exception:
			rid = None
	return StatusWithId(status="ok", message=f"Created recipe '{payload['name']}'", id=int(rid) if isinstance(rid, int) else None)


def GROCERY_UPDATE_recipe(recipe_id: int, fields: Dict[str, Any], base_url: Optional[str] = None) -> StatusMessage:
	client = GrocyClient(base_url=base_url)
	client.update_recipe(int(recipe_id), dict(fields or {}))
	return StatusMessage(status="ok", message=f"Recipe {int(recipe_id)} updated")


def GROCERY_ACTION_delete_recipe(recipe_id: int, base_url: Optional[str] = None) -> StatusMessage:
	client = GrocyClient(base_url=base_url)
	client.delete_recipe(int(recipe_id))
	return StatusMessage(status="ok", message=f"Recipe {int(recipe_id)} deleted")


class Ingredient(BaseModel):
	id: Optional[int] = None
	recipe_id: Optional[int] = None
	product_id: Optional[int] = None
	amount: Optional[float] = None
	qu_id: Optional[int] = None
	note: Optional[str] = None


class Ingredients(BaseModel):
	items: List[Ingredient] = Field(default_factory=list)


Ingredient.model_rebuild()
Ingredients.model_rebuild()


def GROCERY_GET_recipe_ingredients(recipe_id: int, base_url: Optional[str] = None) -> Ingredients | OperationResult:
	try:
		client = GrocyClient(base_url=base_url)
		items = client.list_recipe_ingredients(int(recipe_id))
		out: List[Ingredient] = []
		for it in items:
			try:
				out.append(Ingredient(
					id=(int(it.get("id")) if isinstance(it.get("id"), (int, float)) else None),
					recipe_id=(int(it.get("recipe_id")) if isinstance(it.get("recipe_id"), (int, float)) else None),
					product_id=(int(it.get("product_id")) if isinstance(it.get("product_id"), (int, float)) else None),
					amount=(float(it.get("amount")) if isinstance(it.get("amount"), (int, float)) else None),
					qu_id=(int(it.get("qu_id")) if isinstance(it.get("qu_id"), (int, float)) else None),
					note=(str(it.get("note")) if isinstance(it.get("note"), str) else None),
				))
			except Exception:
				continue
		return Ingredients(items=out)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_ACTION_add_recipe_ingredient(fields: Dict[str, Any], base_url: Optional[str] = None) -> StatusWithId:
	client = GrocyClient(base_url=base_url)
	resp = client.add_recipe_ingredient(dict(fields or {}))
	iid = client._extract_created_id_from_response(resp)
	return StatusWithId(status="ok", message="Ingredient added to recipe", id=int(iid) if isinstance(iid, int) else None)


def GROCERY_UPDATE_recipe_ingredient(ingredient_id: int, fields: Dict[str, Any], base_url: Optional[str] = None) -> StatusMessage:
	client = GrocyClient(base_url=base_url)
	client.update_recipe_ingredient(int(ingredient_id), dict(fields or {}))
	return StatusMessage(status="ok", message=f"Ingredient {int(ingredient_id)} updated")


def GROCERY_ACTION_delete_recipe_ingredient(ingredient_id: int, base_url: Optional[str] = None) -> StatusMessage:
	client = GrocyClient(base_url=base_url)
	client.delete_recipe_ingredient(int(ingredient_id))
	return StatusMessage(status="ok", message=f"Ingredient {int(ingredient_id)} deleted")


TOOLS = [
	GROCERY_GET_inventory,
	GROCERY_ACTION_increase_quantity,
	GROCERY_ACTION_consume_quantity,
	GROCERY_GET_shopping_list,
	GROCERY_ACTION_shopping_list_add,
	GROCERY_ACTION_shopping_list_remove,
	GROCERY_ACTION_shopping_list_clear,
	GROCERY_GET_products,
	GROCERY_ACTION_create_product,
	GROCERY_ACTION_ensure_product_exists,
	GROCERY_GET_meal_plan,
	GROCERY_ACTION_add_meal,
	GROCERY_UPDATE_meal_plan,
	GROCERY_ACTION_delete_meal,
	GROCERY_GET_meal_plan_sections,
	GROCERY_GET_cookable_recipes,
	GROCERY_GET_recipes,
	GROCERY_GET_recipe,
	GROCERY_ACTION_create_recipe,
	GROCERY_UPDATE_recipe,
	GROCERY_ACTION_delete_recipe,
	GROCERY_GET_recipe_ingredients,
	GROCERY_ACTION_add_recipe_ingredient,
	GROCERY_UPDATE_recipe_ingredient,
	GROCERY_ACTION_delete_recipe_ingredient,
]
