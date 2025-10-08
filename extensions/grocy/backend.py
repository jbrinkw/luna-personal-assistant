"""Grocy backend client and helpers.

Provides a thin client for the Grocy REST API and helper methods used by the tool layer.
Reads configuration from environment variables and supports dotenv by default.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import requests

try:  # pragma: no cover
	from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
	load_dotenv = None  # type: ignore

if load_dotenv is not None:  # Load .env if present
	load_dotenv(override=False)


class GrocyClient:
	"""Minimal client for the Grocy REST API.

	Reads configuration from environment variables by default:
	- GROCY_API_KEY: required API key
	- GROCY_BASE_URL: optional base URL, defaults to http://192.168.0.185/api
	"""

	def __init__(
		self,
		base_url: Optional[str] = None,
		api_key: Optional[str] = None,
		request_timeout_seconds: float = 15.0,
	) -> None:
		configured_base_url = base_url or os.getenv("GROCY_BASE_URL") or "http://192.168.0.185/api"
		normalized_base_url = configured_base_url.rstrip("/")

		configured_api_key = api_key or os.getenv("GROCY_API_KEY")
		if not configured_api_key:
			raise RuntimeError("GROCY_API_KEY environment variable is required but not set")

		self.base_url: str = normalized_base_url
		self.request_timeout_seconds: float = request_timeout_seconds

		self._session = requests.Session()
		self._session.headers.update(
			{
				"GROCY-API-KEY": configured_api_key,
				"Accept": "application/json",
			}
		)

	def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
		url = f"{self.base_url}{path}"
		response = self._session.get(
			url,
			params=params,
			timeout=self.request_timeout_seconds,
		)
		response.raise_for_status()
		if response.headers.get("Content-Type", "").startswith("application/json"):
			return response.json()
		return response.text

	def _post(self, path: str, json_body: Optional[Dict[str, Any]] = None) -> Any:
		url = f"{self.base_url}{path}"
		response = self._session.post(
			url,
			json=json_body or {},
			timeout=self.request_timeout_seconds,
		)
		try:
			response.raise_for_status()
		except requests.HTTPError as error:
			try:
				details = response.json()
			except Exception:
				try:
					details = response.text
				except Exception:
					details = None
			raise requests.HTTPError(f"{error} - {details}") from error
		if response.headers.get("Content-Type", "").startswith("application/json"):
			return response.json()
		return response.text

	def _put(self, path: str, json_body: Optional[Dict[str, Any]] = None) -> Any:
		url = f"{self.base_url}{path}"
		response = self._session.put(
			url,
			json=json_body or {},
			timeout=self.request_timeout_seconds,
		)
		try:
			response.raise_for_status()
		except requests.HTTPError as error:
			try:
				details = response.json()
			except Exception:
				try:
					details = response.text
				except Exception:
					details = None
			raise requests.HTTPError(f"{error} - {details}") from error
		if response.headers.get("Content-Type", "").startswith("application/json"):
			return response.json()
		return response.text

	def _delete(self, path: str) -> Any:
		url = f"{self.base_url}{path}"
		response = self._session.delete(
			url,
			timeout=self.request_timeout_seconds,
		)
		try:
			response.raise_for_status()
		except requests.HTTPError as error:
			try:
				details = response.json()
			except Exception:
				try:
					details = response.text
				except Exception:
					details = None
			raise requests.HTTPError(f"{error} - {details}") from error
		if response.headers.get("Content-Type", "").startswith("application/json"):
			return response.json()
		return response.text

	# ---- Stock / Inventory ----
	def get_inventory(self) -> List[Dict[str, Any]]:
		"""Return current stock per product with compatibility across Grocy versions."""
		candidate_paths = [
			"/stock/overview",
			"/stock/overview/",
			"/stock",
			"/stock/",
			"/objects/products",
			"/objects/products/",
			"/stock/products",
			"/stock/products/",
		]
		last_error: Optional[Exception] = None
		for path in candidate_paths:
			try:
				data = self._get(path)
				if isinstance(data, list):
					return data
				if isinstance(data, dict):
					if "data" in data and isinstance(data["data"], list):
						return data["data"]
					if any(isinstance(v, (dict, list)) for v in data.values()):
						return [
							{"key": key, "value": value} for key, value in data.items()
						]
			except requests.HTTPError as error:  # noqa: PERF203
				status = getattr(error.response, "status_code", None)
				if status in {404, 405}:
					last_error = error
					continue
				raise
			except Exception as error:  # noqa: BLE001
				last_error = error
				continue
		if last_error:
			raise last_error
		raise ValueError("Failed to retrieve inventory: no suitable endpoint found")

	def add_product_quantity(self, product_id: int, quantity: float) -> Any:
		if quantity <= 0:
			raise ValueError("quantity must be > 0 to add stock")
		payload = {"amount": float(quantity)}
		return self._post(f"/stock/products/{int(product_id)}/add", json_body=payload)

	def consume_product_quantity(self, product_id: int, quantity: float) -> Any:
		if quantity <= 0:
			raise ValueError("quantity must be > 0 to consume stock")
		payload = {"amount": float(quantity)}
		return self._post(f"/stock/products/{int(product_id)}/consume", json_body=payload)

	# ---- Product helpers ----
	def _object_exists(self, object_name: str, object_id: int) -> bool:
		try:
			data = self._get(f"/objects/{object_name}/{int(object_id)}")
			return isinstance(data, (dict, list)) or bool(data)
		except requests.HTTPError as error:
			status = getattr(error.response, "status_code", None)
			if status == 404:
				return False
			raise

	def validate_product_required_ids(self, fields: Dict[str, Any]) -> None:
		def _as_int(value: Any, key: str) -> int:
			if isinstance(value, (int, float)):
				return int(value)
			if isinstance(value, str) and value.isdigit():
				return int(value)
			raise ValueError(
				f"Missing or invalid required field '{key}'. Provide it explicitly or set the GROCY_DEFAULT_* env vars."
			)

		location_id = _as_int(fields.get("location_id"), "location_id")
		if not self._object_exists("locations", location_id):
			raise ValueError(
				f"Invalid location_id={location_id}: No such location. Use GET /objects/locations to list valid ids, "
				f"then set GROCY_DEFAULT_LOCATION_ID or pass a valid 'location_id'."
			)

		qu_id_purchase = _as_int(fields.get("qu_id_purchase"), "qu_id_purchase")
		if not self._object_exists("quantity_units", qu_id_purchase):
			raise ValueError(
				f"Invalid qu_id_purchase={qu_id_purchase}: No such quantity unit. Use GET /objects/quantity_units to list valid ids, "
				f"then set GROCY_DEFAULT_QU_ID_PURCHASE or pass a valid 'qu_id_purchase'."
			)

		qu_id_stock = _as_int(fields.get("qu_id_stock"), "qu_id_stock")
		if not self._object_exists("quantity_units", qu_id_stock):
			raise ValueError(
				f"Invalid qu_id_stock={qu_id_stock}: No such quantity unit. Use GET /objects/quantity_units to list valid ids, "
				f"then set GROCY_DEFAULT_QU_ID_STOCK or pass a valid 'qu_id_stock'."
			)

		if "qu_factor_purchase_to_stock" in fields:
			raw_factor = fields.get("qu_factor_purchase_to_stock")
			factor = float(raw_factor)  # may raise
			if factor <= 0:
				raise ValueError("'qu_factor_purchase_to_stock' must be > 0")

	def create_product(self, product_fields: Dict[str, Any]) -> Any:
		if not isinstance(product_fields, dict) or not product_fields.get("name"):
			raise ValueError("product_fields must be a dict and include 'name'")
		return self._post("/objects/products", json_body=product_fields)

	def _extract_created_id_from_response(self, response: Any) -> Optional[int]:
		try:
			if isinstance(response, dict):
				for key in [
					"created_object_id",
					"id",
					"last_inserted_id",
					"last_inserted_row_id",
					"rowid",
					"row_id",
				]:
					if key in response:
						raw = response.get(key)
						if isinstance(raw, (int, float)):
							return int(raw)
						if isinstance(raw, str) and raw.isdigit():
							return int(raw)
			if isinstance(response, (int, float)):
				return int(response)
			if isinstance(response, str) and response.isdigit():
				return int(response)
		except Exception:
			return None
		return None

	def get_product_name_map(self) -> Dict[int, str]:
		candidate_paths = [
			"/objects/products",
			"/objects/products/",
		]
		last_error: Optional[Exception] = None
		for path in candidate_paths:
			try:
				data = self._get(path)
				products: List[Dict[str, Any]]
				if isinstance(data, list):
					products = data
				elif isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
					products = data["data"]
				else:
					continue
				id_to_name: Dict[int, str] = {}
				for p in products:
					pid = p.get("id")
					name = p.get("name")
					if isinstance(pid, (int, float)) and isinstance(name, str):
						id_to_name[int(pid)] = name
				return id_to_name
			except requests.HTTPError as error:
				status = getattr(error.response, "status_code", None)
				if status in {404, 405}:
					last_error = error
					continue
				raise
			except Exception as error:  # noqa: BLE001
				last_error = error
				continue
		if last_error:
			raise last_error
		raise ValueError("Failed to retrieve products list for name mapping")

	def find_product_id_by_name(self, name: str) -> Optional[int]:
		if not name:
			return None
		name_map = self.get_product_name_map()
		lowered = name.strip().lower()
		for pid, pname in name_map.items():
			if isinstance(pname, str) and pname.strip().lower() == lowered:
				return int(pid)
		return None

	def _get_quantity_units(self) -> List[Dict[str, Any]]:
		data = self._get("/objects/quantity_units")
		if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
			return data["data"]
		if isinstance(data, list):
			return data
		return []

	def _get_quantity_unit_maps(self) -> tuple[Dict[int, str], Dict[str, int]]:
		rows = self._get_quantity_units()
		id_to_name: Dict[int, str] = {}
		name_to_id: Dict[str, int] = {}
		for r in rows:
			rid = r.get("id")
			name = r.get("name")
			if isinstance(rid, (int, float)) and isinstance(name, str):
				id_to_name[int(rid)] = name
				name_to_id[name.strip().lower()] = int(rid)
		return (id_to_name, name_to_id)

	def get_container_unit_id(self) -> int:
		val = os.getenv("GROCY_QU_ID_CONTAINER")
		if isinstance(val, str) and val.isdigit():
			return int(val)
		_id_to_name, name_to_id = self._get_quantity_unit_maps()
		for key in ["container", "containers"]:
			if key in name_to_id:
				return name_to_id[key]
		raise ValueError("No quantity unit named 'container' found. Set GROCY_QU_ID_CONTAINER or create it in Grocy.")

	def get_serving_unit_id(self) -> int:
		val = os.getenv("GROCY_QU_ID_SERVING")
		if isinstance(val, str) and val.isdigit():
			return int(val)
		_id_to_name, name_to_id = self._get_quantity_unit_maps()
		for key in ["serving", "servings"]:
			if key in name_to_id:
				return name_to_id[key]
		raise ValueError("No quantity unit named 'serving' found. Set GROCY_QU_ID_SERVING or create it in Grocy.")

	def _normalize_recipe_ingredient_units(self, fields: Dict[str, Any]) -> Dict[str, Any]:
		"""Ensure ingredient 'qu_id' corresponds to 'container' or 'serving'.

		Accepts optional 'unit'|'unit_label'|'qu_label' string (container|serving) and maps to qu_id.
		If a numeric 'qu_id' is provided, validates it matches container or serving.
		Removes helper string keys before sending.
		"""
		if not isinstance(fields, dict):
			return fields
		unit_raw = fields.get("unit") or fields.get("unit_label") or fields.get("qu_label")
		container_id = None
		serving_id = None
		try:
			container_id = self.get_container_unit_id()
			serving_id = self.get_serving_unit_id()
		except Exception:
			# Defer strict enforcement if units are not resolvable
			container_id = None
			serving_id = None
		if isinstance(unit_raw, str) and unit_raw.strip():
			label = unit_raw.strip().lower()
			if label not in {"container", "serving"}:
				raise ValueError("'unit' must be 'container' or 'serving'")
			if label == "container":
				if container_id is None:
					raise ValueError("Container unit id could not be determined; set GROCY_QU_ID_CONTAINER or create the unit in Grocy")
				fields["qu_id"] = int(container_id)
			else:
				if serving_id is None:
					raise ValueError("Serving unit id could not be determined; set GROCY_QU_ID_SERVING or create the unit in Grocy")
				fields["qu_id"] = int(serving_id)
				# When unit is 'serving', interpret 'amount' as desired number of servings.
				# Convert to container-equivalent so Grocy shows the correct relationship (UI shows X servings == Y containers).
				try:
					if isinstance(fields.get("amount"), (int, float)) and fields.get("product_id") is not None:
						pid_int = int(fields.get("product_id"))
						factor = self._servings_per_container_from_userfields(pid_int)
						if isinstance(factor, (int, float)) and factor > 0:
							fields["amount"] = float(fields["amount"]) / float(factor)
				except Exception:
					pass
		# If explicit qu_id provided, validate it if we can resolve units
		if fields.get("qu_id") is not None and (container_id is not None or serving_id is not None):
			try:
				qid = int(fields.get("qu_id"))
			except Exception:
				raise ValueError("'qu_id' must be an integer")
			allowed: List[int] = []
			if container_id is not None:
				allowed.append(int(container_id))
			if serving_id is not None:
				allowed.append(int(serving_id))
			if qid not in allowed:
				raise ValueError("'qu_id' must correspond to the 'container' or 'serving' quantity unit")
		# Convert amount to product stock unit if needed to prevent server-side multiplication
		try:
			if isinstance(fields.get("amount"), (int, float)) and fields.get("product_id") is not None and fields.get("qu_id") is not None:
				pid_int = int(fields.get("product_id"))
				qid_int = int(fields.get("qu_id"))
				amount_num = float(fields.get("amount"))
				converted = self._convert_amount_to_product_stock_units(product_id=pid_int, amount=amount_num, from_qu_id=qid_int)
				if isinstance(converted, (int, float)):
					fields["amount"] = float(converted)
		except Exception:
			# Non-fatal; leave amount as-is
			pass

		# Strip helper keys to avoid Grocy rejecting unknown fields
		for k in ("unit", "unit_label", "qu_label"):
			if k in fields:
				try:
					fields.pop(k)
				except Exception:
					pass
		return fields

	def get_product(self, product_id: int) -> Dict[str, Any]:
		pid = int(product_id)
		data = self._get(f"/objects/products/{pid}")
		return data if isinstance(data, dict) else {"id": pid}

	def get_product_userfields(self, product_id: int) -> Dict[str, Any]:
		pid = int(product_id)
		data = self._get(f"/userfields/products/{pid}")
		return data if isinstance(data, dict) else {}

	def _servings_per_container_from_userfields(self, product_id: int) -> Optional[float]:
		try:
			uf = self.get_product_userfields(int(product_id))
			if not isinstance(uf, dict):
				return None
			for key in ("num_servings", "Number of Servings"):
				val = uf.get(key)
				if isinstance(val, (int, float)):
					return float(val)
				if isinstance(val, str):
					try:
						return float(val)
					except Exception:
						continue
			return None
		except Exception:
			return None

	def _convert_amount_to_product_stock_units(self, product_id: int, amount: float, from_qu_id: int) -> float:
		"""Convert an amount expressed in from_qu_id into the product's stock unit amount.

		We use the product's purchase↔stock conversion factor when applicable.
		If from_qu_id already equals stock unit, return the amount unchanged.
		Falls back to no conversion on missing data.
		"""
		try:
			prod = self.get_product(product_id)
			qu_id_stock = int(prod.get("qu_id_stock")) if isinstance(prod.get("qu_id_stock"), (int, float, str)) and str(prod.get("qu_id_stock")).isdigit() else None
			qu_id_purchase = int(prod.get("qu_id_purchase")) if isinstance(prod.get("qu_id_purchase"), (int, float, str)) and str(prod.get("qu_id_purchase")).isdigit() else None
			factor_raw = prod.get("qu_factor_purchase_to_stock")
			pfactor = float(factor_raw) if isinstance(factor_raw, (int, float, str)) and str(factor_raw).replace(".", "", 1).isdigit() else None
			if not isinstance(qu_id_stock, int) or qu_id_stock <= 0:
				return float(amount)
			if int(from_qu_id) == int(qu_id_stock):
				return float(amount)
			if isinstance(qu_id_purchase, int) and isinstance(pfactor, float) and pfactor > 0:
				# purchase -> stock
				if int(from_qu_id) == int(qu_id_purchase) and int(qu_id_stock) == int(qu_id_stock):
					return float(amount) * float(pfactor)
				# stock -> purchase
				if int(from_qu_id) == int(qu_id_stock) and int(qu_id_purchase) == int(qu_id_purchase):
					return float(amount) / float(pfactor)
				# from other (e.g., serving) to stock when purchase/stock swapped
				# If from_qu_id equals stock, handled above; else if from equals purchase, handled above.
				# For other pairs, fall back to no-op.
			return float(amount)
		except Exception:
			return float(amount)

	def ensure_product_exists(self, name: str, create_fields: Optional[Dict[str, Any]] = None) -> int:
		existing = self.find_product_id_by_name(name)
		if isinstance(existing, int):
			return existing
		# Determine default units: prefer env overrides, else 'container' for purchase and 'serving' for stock
		def _env_int(key: str) -> Optional[int]:
			val = os.getenv(key)
			return int(val) if isinstance(val, str) and val.isdigit() else None
		purchase_qu = _env_int("GROCY_DEFAULT_QU_ID_PURCHASE")
		stock_qu = _env_int("GROCY_DEFAULT_QU_ID_STOCK")
		if purchase_qu is None:
			try:
				purchase_qu = self.get_container_unit_id()
			except Exception:
				purchase_qu = None
		if stock_qu is None:
			try:
				stock_qu = self.get_serving_unit_id()
			except Exception:
				stock_qu = None
		defaults: Dict[str, Any] = {
			"name": name,
			"location_id": int(os.getenv("GROCY_DEFAULT_LOCATION_ID", "2")),
			"qu_id_purchase": int(purchase_qu) if isinstance(purchase_qu, int) else int(os.getenv("GROCY_DEFAULT_QU_ID_PURCHASE", "2")),
			"qu_id_stock": int(stock_qu) if isinstance(stock_qu, int) else int(os.getenv("GROCY_DEFAULT_QU_ID_STOCK", "2")),
		}
		payload = {**defaults, **(create_fields or {})}
		self.validate_product_required_ids(payload)
		resp = self.create_product(payload)
		created_id = self._extract_created_id_from_response(resp)
		if isinstance(created_id, int):
			return created_id
		refreshed = self.find_product_id_by_name(name)
		if isinstance(refreshed, int):
			return refreshed
		raise RuntimeError("Product creation succeeded but new id could not be determined")

	# ---- Shopping list ----
	def get_shopping_list_items(self, shopping_list_id: Optional[int] = None) -> List[Dict[str, Any]]:
		candidate_paths = [
			"/stock/shoppinglist",
			"/stock/shoppinglist/",
			"/objects/shopping_list",
			"/objects/shopping_list/",
		]
		last_error: Optional[Exception] = None
		for path in candidate_paths:
			try:
				data = self._get(path)
				if isinstance(data, list):
					items = data
				elif isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
					items = data["data"]
				else:
					continue
				if shopping_list_id is not None:
					sid = int(shopping_list_id)
					filtered: List[Dict[str, Any]] = []
					for item in items:
						item_sid = item.get("shopping_list_id")
						if isinstance(item_sid, (int, float)):
							if int(item_sid) == sid:
								filtered.append(item)
						else:
							nested = item.get("shopping_list")
							if isinstance(nested, dict) and int(nested.get("id", -1)) == sid:
								filtered.append(item)
					return filtered
				return items
			except requests.HTTPError as error:
				status = getattr(error.response, "status_code", None)
				if status in {404, 405}:
					last_error = error
					continue
				raise
			except Exception as error:  # noqa: BLE001
				last_error = error
				continue
		if last_error:
			raise last_error
		raise ValueError("Failed to retrieve shopping list: no suitable endpoint found")

	def shopping_list_add_product(self, product_id: int, amount: float, shopping_list_id: Optional[int] = 1) -> Any:
		if amount <= 0:
			raise ValueError("amount must be > 0 to add to shopping list")
		payload: Dict[str, Any] = {
			"product_id": int(product_id),
			"amount": float(amount),
		}
		if shopping_list_id is not None:
			payload["shopping_list_id"] = int(shopping_list_id)
		return self._post("/stock/shoppinglist/add-product", json_body=payload)

	def shopping_list_remove_product(self, product_id: int, amount: float, shopping_list_id: Optional[int] = 1) -> Any:
		if amount <= 0:
			raise ValueError("amount must be > 0 to remove from shopping list")
		payload: Dict[str, Any] = {
			"product_id": int(product_id),
			"amount": float(amount),
		}
		if shopping_list_id is not None:
			payload["shopping_list_id"] = int(shopping_list_id)
		return self._post("/stock/shoppinglist/remove-product", json_body=payload)

	def shopping_list_clear(self, shopping_list_id: Optional[int] = 1) -> Any:
		payload: Dict[str, Any] = {}
		if shopping_list_id is not None:
			payload["shopping_list_id"] = int(shopping_list_id)
		return self._post("/stock/shoppinglist/clear", json_body=payload)

	# ---- Recipes CRUD ----
	def get_recipes(self) -> List[Dict[str, Any]]:
		data = self._get("/objects/recipes")
		if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
			return data["data"]
		if isinstance(data, list):
			return data
		return []

	def get_recipe(self, recipe_id: int) -> Dict[str, Any]:
		rid = int(recipe_id)
		data = self._get(f"/objects/recipes/{rid}")
		return data if isinstance(data, dict) else {"id": rid}

	def create_recipe(self, fields: Dict[str, Any]) -> Any:
		if not isinstance(fields, dict) or not fields.get("name"):
			raise ValueError("recipe fields must include 'name'")
		return self._post("/objects/recipes", json_body=fields)

	def update_recipe(self, recipe_id: int, fields: Dict[str, Any]) -> Any:
		if not isinstance(fields, dict) or not fields:
			raise ValueError("update fields must be a non-empty object")
		rid = int(recipe_id)
		return self._put(f"/objects/recipes/{rid}", json_body=fields)

	def delete_recipe(self, recipe_id: int) -> Any:
		rid = int(recipe_id)
		return self._delete(f"/objects/recipes/{rid}")

	# ---- Recipe Ingredients ----
	def list_recipe_ingredients(self, recipe_id: int) -> List[Dict[str, Any]]:
		rid = int(recipe_id)
		data = self._get("/objects/recipes_pos")
		if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
			items = data["data"]
		elif isinstance(data, list):
			items = data
		else:
			items = []
		result: List[Dict[str, Any]] = []
		for item in items:
			if int(item.get("recipe_id", -1)) == rid:
				result.append(item)
		return result

	def add_recipe_ingredient(self, fields: Dict[str, Any]) -> Any:
		if not isinstance(fields, dict):
			raise ValueError("ingredient fields must be an object")
		rid = fields.get("recipe_id")
		pid = fields.get("product_id")
		amount = fields.get("amount")
		if not isinstance(rid, (int, float, str)):
			raise ValueError("'recipe_id' is required")
		if not isinstance(pid, (int, float, str)):
			raise ValueError("'product_id' is required")
		if not isinstance(amount, (int, float)):
			raise ValueError("'amount' is required and must be a number")
		rid_int = int(rid)
		pid_int = int(pid)
		if not self._object_exists("recipes", rid_int):
			raise ValueError(f"Invalid recipe_id={rid_int}: No such recipe")
		if not self._object_exists("products", pid_int):
			raise ValueError(f"Invalid product_id={pid_int}: No such product")
		# Normalize/validate unit to enforce container/serving only
		fields = self._normalize_recipe_ingredient_units(dict(fields))
		qu_id = fields.get("qu_id")
		if qu_id is not None:
			qu_int = int(qu_id)
			if not self._object_exists("quantity_units", qu_int):
				raise ValueError(f"Invalid qu_id={qu_int}: No such quantity unit")
		return self._post("/objects/recipes_pos", json_body=fields)

	def update_recipe_ingredient(self, ingredient_id: int, fields: Dict[str, Any]) -> Any:
		if not isinstance(fields, dict) or not fields:
			raise ValueError("update fields must be a non-empty object")
		# Normalize/validate unit to enforce container/serving only if unit/qu_id provided
		fields = self._normalize_recipe_ingredient_units(dict(fields))
		iid = int(ingredient_id)
		return self._put(f"/objects/recipes_pos/{iid}", json_body=fields)

	def delete_recipe_ingredient(self, ingredient_id: int) -> Any:
		iid = int(ingredient_id)
		return self._delete(f"/objects/recipes_pos/{iid}")

	# ---- Meal Plan ----
	def list_meal_plan(self) -> List[Dict[str, Any]]:
		data = self._get("/objects/meal_plan")
		if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
			return data["data"]
		if isinstance(data, list):
			return data
		return []

	def create_meal_plan_entry(self, fields: Dict[str, Any]) -> Any:
		if not isinstance(fields, dict):
			raise ValueError("fields must be an object")
		day = fields.get("day")
		if not isinstance(day, str) or not day.strip():
			raise ValueError("'day' (YYYY-MM-DD) is required")
		if not (fields.get("recipe_id") or fields.get("product_id") or fields.get("note")):
			raise ValueError("Provide one of 'recipe_id', 'product_id', or 'note'")
		if fields.get("recipe_id") is not None:
			rid = int(fields["recipe_id"])
			if not self._object_exists("recipes", rid):
				raise ValueError(f"Invalid recipe_id={rid}: No such recipe")
		if fields.get("product_id") is not None:
			pid = int(fields["product_id"])
			if not self._object_exists("products", pid):
				raise ValueError(f"Invalid product_id={pid}: No such product")
		if fields.get("qu_id") is not None:
			qid = int(fields["qu_id"])
			if not self._object_exists("quantity_units", qid):
				raise ValueError(f"Invalid qu_id={qid}: No such quantity unit")
		if fields.get("meal_plan_section_id") is not None:
			sid = int(fields["meal_plan_section_id"])
			if not self._object_exists("meal_plan_sections", sid):
				raise ValueError(f"Invalid meal_plan_section_id={sid}: No such section")
		return self._post("/objects/meal_plan", json_body=fields)

	def update_meal_plan_entry(self, entry_id: int, fields: Dict[str, Any]) -> Any:
		if not isinstance(fields, dict) or not fields:
			raise ValueError("update fields must be a non-empty object")
		eid = int(entry_id)
		return self._put(f"/objects/meal_plan/{eid}", json_body=fields)

	def delete_meal_plan_entry(self, entry_id: int) -> Any:
		eid = int(entry_id)
		return self._delete(f"/objects/meal_plan/{eid}")

	def list_meal_plan_sections(self) -> List[Dict[str, Any]]:
		data = self._get("/objects/meal_plan_sections")
		if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
			return data["data"]
		if isinstance(data, list):
			return data
		return []


# ---- Lightweight extraction helpers used by tool layer ----

def extract_name(item: Dict[str, Any]) -> Optional[str]:
	product = item.get("product")
	if isinstance(product, dict) and "name" in product:
		return product.get("name")
	if "name" in item:
		return item.get("name")
	if "product_name" in item:
		return item.get("product_name")
	return None


def extract_quantity(item: Dict[str, Any]) -> Optional[float]:
	for key in [
		"amount",
		"stock_amount",
		"quantity",
		"amount_aggregated",
		"available_amount",
	]:
		value = item.get(key)
		if isinstance(value, (int, float)):
			return float(value)
	product = item.get("product")
	if isinstance(product, dict):
		for key in ["stock_amount", "amount", "quantity"]:
			value = product.get(key)
			if isinstance(value, (int, float)):
				return float(value)
	return None


def extract_expiry(item: Dict[str, Any]) -> Optional[str]:
	for key in [
		"best_before_date",
		"due_date",
		"next_due_date",
		"best_before",
		"expiry_date",
	]:
		value = item.get(key)
		if isinstance(value, str) and value:
			return value
	return None

