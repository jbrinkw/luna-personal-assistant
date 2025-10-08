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


def _build_products_bulleted_list() -> str:
	try:
		client = GrocyClient()
		id_to_name = client.get_product_name_map()
		if not id_to_name:
			return "<no products found>"
		lines = []
		for pid, name in sorted(id_to_name.items(), key=lambda kv: kv[0]):
			try:
				lines.append(f"- {name} (id: {int(pid)})")
			except Exception:
				continue
		return "\n".join(lines)
	except Exception:
		return "<product list unavailable>"


def _system_prompt() -> str:
	base = (
		"Pantry, shopping list, recipes, and meal planning using Grocy.\n\n"
		"You can:\n"
		"- List inventory with simplified name/quantity/expiry.\n"
		"- Increase/consume product quantities by product_id.\n"
		"- Manage shopping list (list, add, remove, clear).\n"
		"- List products (id → name) to help choose ids.\n"
		"- Manage meal plan entries and sections (list, create, update, delete).\n"
		"- List recipes, get a recipe, create/update/delete recipes; manage ingredients.\n"
		"- Find currently cookable recipes according to Grocy's fulfillment logic.\n\n"
		"Safety rules (critical):\n"
		"- ABSOLUTELY DO NOT create a new product unless the user explicitly asks you to.\n"
		"- BEFORE creating any product (including via ensure/create), ASK the user for explicit confirmation.\n"
		"- If you are confused about which product the user is referencing, ASK for confirmation and/or list products.\n\n"
		"Return structured JSON using the provided models.\n\n"
		"Current products (name and id):\n"
	)
	plist = _build_products_bulleted_list()
	return (base + (plist or "<product list unavailable>")).strip()


SYSTEM_PROMPT = _system_prompt()


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

def GROCERY_GET_inventory() -> InventoryList | OperationResult:
	"""List current inventory as name, quantity, expiry.
	Example Prompt: Show pantry inventory.
	Example Response: {"items": [{"name": "Milk", "quantity": 1, "expiry": "2025-09-10"}]}
	"""
	try:
		client = GrocyClient()
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


def GROCERY_ACTION_increase_quantity(product_id: int, quantity: float) -> StatusMessage:
	"""Increase product stock amount by product_id and quantity.
	Example Prompt: Add 2 to product 5.
	Example Response: {"status": "ok", "message": "Increased product 5 by 2.0"}
	Example Args: {"product_id": 5, "quantity": 2}
	"""
	client = GrocyClient()
	client.add_product_quantity(product_id=product_id, quantity=quantity)
	return StatusMessage(status="ok", message=f"Increased product {int(product_id)} by {float(quantity)}")


def GROCERY_ACTION_consume_quantity(product_id: int, quantity: float) -> StatusMessage:
	"""Consume product stock amount by product_id and quantity.
	Example Prompt: Use 1.5 of product 5.
	Example Response: {"status": "ok", "message": "Consumed product 5 by 1.5"}
	"""
	client = GrocyClient()
	client.consume_product_quantity(product_id=product_id, quantity=quantity)
	return StatusMessage(status="ok", message=f"Consumed product {int(product_id)} by {float(quantity)}")


def GROCERY_GET_shopping_list(shopping_list_id: Optional[int] = 1) -> ShoppingList | OperationResult:
	"""List shopping list items with resolved product names.
	Example Prompt: Show shopping list.
	Example Response: {"items": [{"product_id": 5, "name": "Milk", "quantity": 2}]}
	Example Args: {"shopping_list_id": 1}
	"""
	try:
		client = GrocyClient()
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


def GROCERY_ACTION_shopping_list_add(product_id: int, amount: float, shopping_list_id: Optional[int] = 1) -> StatusMessage:
	client = GrocyClient()
	client.shopping_list_add_product(product_id=product_id, amount=amount, shopping_list_id=shopping_list_id)
	return StatusMessage(status="ok", message=f"Added product {int(product_id)} x {float(amount)} to shopping list")


def GROCERY_ACTION_shopping_list_remove(product_id: int, amount: float, shopping_list_id: Optional[int] = 1) -> StatusMessage:
	client = GrocyClient()
	client.shopping_list_remove_product(product_id=product_id, amount=amount, shopping_list_id=shopping_list_id)
	return StatusMessage(status="ok", message=f"Removed product {int(product_id)} x {float(amount)} from shopping list")


def GROCERY_ACTION_shopping_list_clear(shopping_list_id: Optional[int] = 1) -> StatusMessage:
	client = GrocyClient()
	client.shopping_list_clear(shopping_list_id=shopping_list_id)
	return StatusMessage(status="ok", message=f"Cleared shopping list {int(shopping_list_id) if shopping_list_id is not None else ''}")


def GROCERY_GET_products() -> ProductsList | OperationResult:
	"""List products as id/name pairs, sorted by id."""
	try:
		client = GrocyClient()
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


def GROCERY_ACTION_create_product(product_fields: Dict[str, Any]) -> StatusWithId:
	"""Create a product with sensible defaults.

	Required: product_fields = { name }.
	Optional: location_id, qu_id_purchase, qu_id_stock, and other Grocy product fields.
	Defaults: purchase unit = container, stock unit = serving (unless explicit or via env defaults).

	Example Prompt: Create a product named "Milk 2%".
	Example Args: {"product_fields": {"name": "Milk 2%"}}
	"""
	client = GrocyClient()
	fields: Dict[str, Any] = dict(product_fields or {})
	if not fields.get("name"):
		raise ValueError("'name' is required to create a product")
	fields.setdefault("location_id", int(os.getenv("GROCY_DEFAULT_LOCATION_ID", "2")))
	# Default quantity units: prefer env, else container for purchase and serving for stock
	if "qu_id_purchase" not in fields:
		try:
			fields["qu_id_purchase"] = int(os.getenv("GROCY_DEFAULT_QU_ID_PURCHASE", "")) if os.getenv("GROCY_DEFAULT_QU_ID_PURCHASE", "").isdigit() else client.get_container_unit_id()
		except Exception:
			fields["qu_id_purchase"] = int(os.getenv("GROCY_DEFAULT_QU_ID_PURCHASE", "2"))
	if "qu_id_stock" not in fields:
		try:
			fields["qu_id_stock"] = int(os.getenv("GROCY_DEFAULT_QU_ID_STOCK", "")) if os.getenv("GROCY_DEFAULT_QU_ID_STOCK", "").isdigit() else client.get_serving_unit_id()
		except Exception:
			fields["qu_id_stock"] = int(os.getenv("GROCY_DEFAULT_QU_ID_STOCK", "2"))
	client.validate_product_required_ids(fields)
	resp = client.create_product(fields)
	pid = client._extract_created_id_from_response(resp)
	if not isinstance(pid, int):
		pid = client.find_product_id_by_name(fields["name"]) or None
	return StatusWithId(status="ok", message=f"Created product '{fields['name']}'", id=int(pid) if isinstance(pid, int) else None)


def GROCERY_ACTION_ensure_product_exists(name: str, create_fields: Optional[Dict[str, Any]] = None) -> EnsureProductResult:
	"""Ensure a product by name exists (create if missing).

	Required: name.
	Optional: create_fields object merged into product creation if not found.

	Example Prompt: Ensure product "Milk 2%" exists.
	Example Args: {"name": "Milk 2%", "create_fields": {"location_id": 2}}
	"""
	client = GrocyClient()
	existing = client.find_product_id_by_name(name)
	if isinstance(existing, int):
		return EnsureProductResult(status="ok", message=f"Product '{name}' already exists", product_id=int(existing), created=False)
	new_id = client.ensure_product_exists(name=name, create_fields=create_fields)
	return EnsureProductResult(status="ok", message=f"Created product '{name}'", product_id=int(new_id), created=True)


def GROCERY_GET_meal_plan(start: Optional[str] = None, end: Optional[str] = None) -> MealPlan | OperationResult:
	try:
		client = GrocyClient()
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


def GROCERY_ACTION_add_meal(fields: Dict[str, Any]) -> StatusMessage:
	"""Add a meal plan entry.

	Required: fields = { day: "YYYY-MM-DD", recipe_id or product_id or note }.
	Optional: servings, amount, qu_id, meal_plan_section_id, note.

	Example Prompt: Add recipe 12 to 2025-09-25 for 2 servings.
	Example Args: {"fields": {"day": "2025-09-25", "recipe_id": 12, "servings": 2}}
	"""
	client = GrocyClient()
	client.create_meal_plan_entry(dict(fields or {}))
	return StatusMessage(status="ok", message="Meal plan entry created")


def GROCERY_UPDATE_meal_plan(entry_id: int, fields: Dict[str, Any]) -> StatusMessage:
	"""Update a meal plan entry by id.

	Required: entry_id and a non-empty fields object.

	Example Prompt: Update meal entry 45 to 3 servings.
	Example Args: {"entry_id": 45, "fields": {"servings": 3}}
	"""
	client = GrocyClient()
	client.update_meal_plan_entry(entry_id=int(entry_id), fields=dict(fields or {}))
	return StatusMessage(status="ok", message=f"Meal plan entry {int(entry_id)} updated")


def GROCERY_ACTION_delete_meal(entry_id: int) -> StatusMessage:
	client = GrocyClient()
	client.delete_meal_plan_entry(int(entry_id))
	return StatusMessage(status="ok", message=f"Meal plan entry {int(entry_id)} deleted")


def GROCERY_GET_meal_plan_sections() -> MealPlanSections | OperationResult:
	try:
		client = GrocyClient()
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


def GROCERY_GET_cookable_recipes(desired_servings: Optional[float] = None, consider_shopping_list: bool = False) -> Recipes | OperationResult:
	try:
		client = GrocyClient()
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


def GROCERY_GET_recipes() -> Recipes | OperationResult:
	try:
		client = GrocyClient()
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


def GROCERY_GET_recipe(recipe_id: int) -> Recipe | OperationResult:
	try:
		client = GrocyClient()
		raw = client.get_recipe(int(recipe_id))
		return Recipe(
			id=int(raw.get("id")) if isinstance(raw.get("id"), (int, float)) else int(recipe_id),
			name=raw.get("name") if isinstance(raw.get("name"), str) else None,
			base_servings=(int(raw.get("base_servings")) if isinstance(raw.get("base_servings"), (int, float)) else None),
			description=(str(raw.get("description")) if isinstance(raw.get("description"), str) else None),
		)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_ACTION_create_recipe(fields: Dict[str, Any]) -> StatusWithId:
	"""Create a new recipe.

	Required: fields = { name }.
	Optional: base_servings, description, and other Grocy recipe fields.

	Example Prompt: Create a recipe named "Greek Salad".
	Example Args: {"fields": {"name": "Greek Salad", "base_servings": 2}}
	"""
	client = GrocyClient()
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


def GROCERY_UPDATE_recipe(recipe_id: int, fields: Dict[str, Any]) -> StatusMessage:
	"""Update a recipe by id.

	Required: recipe_id and a non-empty fields object.

	Example Prompt: Rename recipe 12 to "Greek Salad (Easy)".
	Example Args: {"recipe_id": 12, "fields": {"name": "Greek Salad (Easy)"}}
	"""
	client = GrocyClient()
	client.update_recipe(int(recipe_id), dict(fields or {}))
	return StatusMessage(status="ok", message=f"Recipe {int(recipe_id)} updated")


def GROCERY_ACTION_delete_recipe(recipe_id: int) -> StatusMessage:
	client = GrocyClient()
	client.delete_recipe(int(recipe_id))
	return StatusMessage(status="ok", message=f"Recipe {int(recipe_id)} deleted")


class Ingredient(BaseModel):
	id: Optional[int] = None
	recipe_id: Optional[int] = None
	product_id: Optional[int] = None
	amount: Optional[float] = None
	qu_id: Optional[int] = None
	unit: Optional[str] = None
	note: Optional[str] = None


class Ingredients(BaseModel):
	items: List[Ingredient] = Field(default_factory=list)


Ingredient.model_rebuild()
Ingredients.model_rebuild()


def GROCERY_GET_recipe_ingredients(recipe_id: int) -> Ingredients | OperationResult:
	"""List ingredients for a given recipe id.

	Example Prompt: List ingredients for recipe 12.
	Example Args: {"recipe_id": 12}
	Returns: {"items": [{"id", "recipe_id", "product_id", "amount", "qu_id", "unit", "note"}]}

	Notes:
	- The "unit" label is resolved from "qu_id" and will be "container" or "serving" when possible.
	"""
	try:
		client = GrocyClient()
		items = client.list_recipe_ingredients(int(recipe_id))
		# Resolve container/serving unit ids for mapping
		try:
			container_id = client.get_container_unit_id()
		except Exception:
			container_id = None
		try:
			serving_id = client.get_serving_unit_id()
		except Exception:
			serving_id = None
		out: List[Ingredient] = []
		for it in items:
			try:
				unit_label = None
				try:
					qid = int(it.get("qu_id")) if isinstance(it.get("qu_id"), (int, float, str)) and str(it.get("qu_id")).isdigit() else None
					if qid is not None:
						if container_id is not None and qid == int(container_id):
							unit_label = "container"
						elif serving_id is not None and qid == int(serving_id):
							unit_label = "serving"
				except Exception:
					unit_label = None
				out.append(Ingredient(
					id=(int(it.get("id")) if isinstance(it.get("id"), (int, float)) else None),
					recipe_id=(int(it.get("recipe_id")) if isinstance(it.get("recipe_id"), (int, float)) else None),
					product_id=(int(it.get("product_id")) if isinstance(it.get("product_id"), (int, float)) else None),
					amount=(float(it.get("amount")) if isinstance(it.get("amount"), (int, float)) else None),
					qu_id=(int(it.get("qu_id")) if isinstance(it.get("qu_id"), (int, float)) else None),
					unit=unit_label,
					note=(str(it.get("note")) if isinstance(it.get("note"), str) else None),
				))
			except Exception:
				continue
		return Ingredients(items=out)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


class NamedIngredient(BaseModel):
	product_id: Optional[int] = None
	product_name: Optional[str] = None
	amount: Optional[float] = None
	unit: Optional[str] = None


class NamedIngredients(BaseModel):
	items: List[NamedIngredient] = Field(default_factory=list)


NamedIngredient.model_rebuild()
NamedIngredients.model_rebuild()


def GROCERY_GET_recipe_ingredients_readable(recipe_id: int) -> NamedIngredients | OperationResult:
	"""List recipe ingredients with resolved product names and unit labels.

	Example Prompt: Show readable ingredients for recipe 12.
	Example Args: {"recipe_id": 12}
	Returns: {"items": [{"product_id", "product_name", "amount", "unit"}]}

	Notes:
	- Uses the stored recipe ingredient amount and unit. No conversion or inflation is applied.
	"""
	try:
		client = GrocyClient()
		items = client.list_recipe_ingredients(int(recipe_id))
		try:
			name_map = client.get_product_name_map()
		except Exception:
			name_map = {}
		try:
			container_id = client.get_container_unit_id()
		except Exception:
			container_id = None
		try:
			serving_id = client.get_serving_unit_id()
		except Exception:
			serving_id = None
		out: List[NamedIngredient] = []
		for it in items:
			try:
				pid = (int(it.get("product_id")) if isinstance(it.get("product_id"), (int, float)) else None)
				qid = (int(it.get("qu_id")) if isinstance(it.get("qu_id"), (int, float)) else None)
				unit_label = None
				if isinstance(qid, int):
					if container_id is not None and qid == int(container_id):
						unit_label = "container"
					elif serving_id is not None and qid == int(serving_id):
						unit_label = "serving"
				out.append(NamedIngredient(
					product_id=pid,
					product_name=(name_map.get(pid) if isinstance(pid, int) else None),
					amount=(float(it.get("amount")) if isinstance(it.get("amount"), (int, float)) else None),
					unit=unit_label,
				))
			except Exception:
				continue
		return NamedIngredients(items=out)
	except Exception as e:
		return OperationResult(success=False, message=str(e))


def GROCERY_ACTION_add_recipe_ingredient(fields: Dict[str, Any]) -> StatusWithId:
	"""Add an ingredient to a recipe.

	Required: fields = { recipe_id, product_id, amount }.
	Units: pass either unit="container"|"serving" OR qu_id matching those units. Other units are rejected.
	Optional: fields.note

	Serving semantics:
	- If unit="serving", the provided amount is interpreted as desired servings.
	- You may also pass fields.servings as an alias for amount when unit="serving".
	- The tool normalizes the stored amount using the product userfield "Number of Servings"/"num_servings" so the UI shows the correct equivalence.

	Example Prompt: Add 1 serving of product 235 to recipe 10.
	Example Args: {"fields": {"recipe_id": 10, "product_id": 235, "amount": 1, "unit": "serving"}}
	Alternative Args (alias): {"fields": {"recipe_id": 10, "product_id": 235, "servings": 1, "unit": "serving"}}
	Alternative Args: {"fields": {"recipe_id": 10, "product_id": 235, "amount": 1, "qu_id": 123}}
	"""
	client = GrocyClient()
	payload = dict(fields or {})
	try:
		if (payload.get("unit") or payload.get("unit_label") or payload.get("qu_label")) in ("serving", "Serving", "SERVING"):
			if "amount" not in payload and isinstance(payload.get("servings"), (int, float)):
				payload["amount"] = float(payload.get("servings"))
	except Exception:
		pass
	resp = client.add_recipe_ingredient(payload)
	iid = client._extract_created_id_from_response(resp)
	return StatusWithId(status="ok", message="Ingredient added to recipe", id=int(iid) if isinstance(iid, int) else None)


def GROCERY_UPDATE_recipe_ingredient(ingredient_id: int, fields: Dict[str, Any]) -> StatusMessage:
	"""Update an existing recipe ingredient by id.

	Required: ingredient_id, and fields is a non-empty object.
	Units: pass unit="container"|"serving" or qu_id matching those units. Other units are rejected.

	Serving semantics:
	- If unit="serving", the provided amount is interpreted as desired servings (or pass fields.servings as an alias).
	- The tool normalizes the stored amount using the product userfield "Number of Servings"/"num_servings".

	Example Prompt: Change ingredient 77 to 2 containers.
	Example Args: {"ingredient_id": 77, "fields": {"amount": 2, "unit": "container"}}
	"""
	client = GrocyClient()
	payload = dict(fields or {})
	try:
		if (payload.get("unit") or payload.get("unit_label") or payload.get("qu_label")) in ("serving", "Serving", "SERVING"):
			if "amount" not in payload and isinstance(payload.get("servings"), (int, float)):
				payload["amount"] = float(payload.get("servings"))
	except Exception:
		pass
	client.update_recipe_ingredient(int(ingredient_id), payload)
	return StatusMessage(status="ok", message=f"Ingredient {int(ingredient_id)} updated")


def GROCERY_ACTION_delete_recipe_ingredient(ingredient_id: int) -> StatusMessage:
	client = GrocyClient()
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
	GROCERY_GET_recipe_ingredients_readable,
	GROCERY_ACTION_add_recipe_ingredient,
	GROCERY_UPDATE_recipe_ingredient,
	GROCERY_ACTION_delete_recipe_ingredient,
]
