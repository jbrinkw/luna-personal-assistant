#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import json

# Add the project root to Python path so we can import extensions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from extensions.grocy.backend import GrocyClient


def main() -> int:
	base_url = os.getenv("GROCY_BASE_URL") or "http://192.168.0.185/api"
	print(f"Using GROCY_BASE_URL={base_url}")
	client = GrocyClient()

	# Resolve product id for Honey Mustard
	# Priority: explicit env GROCY_TEST_PRODUCT_ID, else fuzzy match by name containing 'honey' and 'mustard'
	env_pid = os.getenv("GROCY_TEST_PRODUCT_ID")
	if isinstance(env_pid, str) and env_pid.isdigit():
		target_pid = int(env_pid)
		print(f"Using explicit GROCY_TEST_PRODUCT_ID={target_pid}")
	else:
		name_map = client.get_product_name_map()
		candidates = []
		for pid, name in name_map.items():
			try:
				low = (name or "").strip().lower()
				if ("honey" in low) and ("mustard" in low):
					candidates.append((int(pid), name))
			except Exception:
				continue
		if candidates:
			candidates.sort(key=lambda x: x[0])
			target_pid = int(candidates[0][0])
			print(f"Selected product by fuzzy match: {candidates[0][1]} (id={target_pid})")
		else:
			target_pid = None
	if not isinstance(target_pid, int):
		print("ERROR: Product containing 'Honey' and 'Mustard' not found. Set GROCY_TEST_PRODUCT_ID to override.")
		return 1

	# Determine serving unit id
	try:
		serving_qu = client.get_serving_unit_id()
	except Exception as e:
		print(f"ERROR: Could not resolve serving unit id: {e}")
		return 1

	# Select recipe id (env override supported)
	env_rid = os.getenv("GROCY_TEST_RECIPE_ID")
	recipe_id = int(env_rid) if isinstance(env_rid, str) and env_rid.isdigit() else 12
	print(f"Using recipe_id={recipe_id}")
	# Print product unit configuration for debug
	prod = client.get_product(int(target_pid))
	print("Product details:", json.dumps({
		"id": prod.get("id"),
		"name": prod.get("name"),
		"qu_id_purchase": prod.get("qu_id_purchase"),
		"qu_id_stock": prod.get("qu_id_stock"),
		"qu_factor_purchase_to_stock": prod.get("qu_factor_purchase_to_stock"),
	}, ensure_ascii=False))

	# Determine servings per container from product userfields
	servings_per_container = None
	try:
		uf_map = client._get(f"/userfields/products/{int(target_pid)}")
		if isinstance(uf_map, dict):
			for key in ["num_servings", "Number of Servings"]:
				val = uf_map.get(key)
				try:
					num = float(val)
					if num > 0:
						servings_per_container = num
						break
				except Exception:
					continue
	except Exception:
		servings_per_container = None
	if not isinstance(servings_per_container, (int, float)) or servings_per_container <= 0:
		print("WARNING: Could not determine servings per container; defaulting to 1")
		servings_per_container = 1.0

	desired_servings = float(os.getenv("GROCY_TEST_SERVINGS") or 1)
	amount_to_save = desired_servings / float(servings_per_container)
	print(f"Adding ingredient: recipe_id={recipe_id}, product_id={target_pid}, desired_servings={desired_servings}, computed containers={amount_to_save:.6f}, unit=serving")
	fields = {"recipe_id": int(recipe_id), "product_id": int(target_pid), "amount": float(amount_to_save), "unit": "serving"}
	try:
		resp = client.add_recipe_ingredient(dict(fields))
		print("Add response:", json.dumps(resp if isinstance(resp, dict) else {"raw": str(resp)}, ensure_ascii=False))
	except Exception as e:
		print("ERROR during add:", str(e))

	# Fetch and print ingredients for the recipe
	try:
		items = client.list_recipe_ingredients(int(recipe_id))
		print("\nRecipe ingredients (raw):")
		for it in items:
			print(json.dumps(it, ensure_ascii=False))
		# Build readable view
		print("\nReadable lines (amount + unit per ingredient):")
		try:
			name_map = client.get_product_name_map()
		except Exception:
			name_map = {}
		def unit_label_for(qid: int) -> str | None:
			try:
				cid = client.get_container_unit_id()
				sid = client.get_serving_unit_id()
				if isinstance(qid, int):
					if isinstance(cid, int) and qid == int(cid):
						return "container"
					if isinstance(sid, int) and qid == int(sid):
						return "serving"
			except Exception:
				return None
			return None
		for it in items:
			pid = it.get("product_id")
			name = name_map.get(int(pid)) if isinstance(pid, (int, float)) else None
			amount = it.get("amount")
			qid = it.get("qu_id")
			ulab = unit_label_for(int(qid)) if isinstance(qid, (int, float, str)) and str(qid).isdigit() else None
			unit_display = ulab if ulab else (f"qu_id={qid}" if qid is not None else "unit=?")
			# Also show servings-equivalent using userfield factor (for debugging UI equivalence)
			try:
				uf_map2 = client._get(f"/userfields/products/{int(pid)}") if isinstance(pid, (int, float)) else {}
				fac = None
				if isinstance(uf_map2, dict):
					v = uf_map2.get("num_servings") or uf_map2.get("Number of Servings")
					fac = float(v) if isinstance(v, (int, float, str)) and str(v).replace(".", "", 1).isdigit() else None
			except Exception:
				fac = None
			serv_eq = (float(amount) * float(fac)) if (isinstance(amount, (int, float)) and isinstance(fac, (int, float))) else None
			if serv_eq is not None:
				print(f"- {name or 'Unknown'}: {amount} {unit_display}  (~ {serv_eq:g} servings via userfield)")
			else:
				print(f"- {name or 'Unknown'}: {amount} {unit_display}")
		# Print product userfields (to compare where large Servings might come from)
		try:
			uf = client._get(f"/userfields/products/{int(target_pid)}")
			print("\nProduct userfields:", json.dumps(uf if isinstance(uf, dict) else {"raw": str(uf)}, ensure_ascii=False))
		except Exception as e:
			print("(Could not read product userfields:", str(e), ")")
		print("\nDone.")
	except Exception as e:
		print("ERROR reading ingredients:", str(e))
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())


