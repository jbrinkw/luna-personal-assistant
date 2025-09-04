import asyncio
import os
import time
from typing import Any, Dict, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from .schema_local import build_light_schema_text
from .agents_local import run_general, run_homeassistant, run_chefbyte, run_coachbyte, make_llm, DEFAULT_MODEL_NAME


 


async def route(user_input: str, light_schema: str, model_name: str = DEFAULT_MODEL_NAME) -> Dict[str, Optional[str]]:
    model = make_llm(model_name)
    system = SystemMessage(
        content=(
            "You are an orchestrator. Split the user input into per-domain instructions (general, ha, chefbyte, coachbyte).\n"
            "Only assign instruction if appropriate based on the light schema. Use null otherwise.\n"
            "Output JSON with keys: general, ha, chefbyte, coachbyte. Values are strings or null.\n"
            "WHEN SENDING INSTRUCTIONS TO A DOMAIN YOU MUST INCLUDE ALL REQUIRED CONTEXT.\n\n"
            f"Light schema:\n{light_schema}\n"
        )
    )
    human = HumanMessage(content=user_input)
    resp = await model.ainvoke([system, human])
    content = str(resp.content)
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        # naive fallback: route to general
        return {"general": user_input, "ha": None, "chefbyte": None, "coachbyte": None}
    import json

    try:
        data = json.loads(content[start : end + 1])
        general = data.get("general")
        ha = data.get("ha")
        chef = data.get("chefbyte")
        coach = data.get("coachbyte")
        return {
            "general": general if isinstance(general, str) else None,
            "ha": ha if isinstance(ha, str) else None,
            "chefbyte": chef if isinstance(chef, str) else None,
            "coachbyte": coach if isinstance(coach, str) else None,
        }
    except Exception:
        return {"general": user_input, "ha": None, "chefbyte": None, "coachbyte": None}


async def orchestrate(user_input: str) -> Dict[str, Any]:
    light_schema = build_light_schema_text()
    # Extract schema load errors (if any) from the light schema text so callers can surface them
    schema_errors: list[dict[str, str]] = []
    try:
        current_domain = None
        for line in (light_schema or "").splitlines():
            s = line.strip()
            if s in ("GeneralByte", "HomeAssistant", "ChefByte", "CoachByte"):
                current_domain = s
                continue
            if s.lower().startswith("- error:"):
                err = s[len("- error:"):].strip()
                schema_errors.append({"domain": current_domain or "unknown", "error": err})
    except Exception:
        pass
    t_route = time.perf_counter()
    decision = await route(user_input, light_schema, model_name=DEFAULT_MODEL_NAME)
    routing_s = round(time.perf_counter() - t_route, 3)

    tasks: Dict[str, asyncio.Task] = {}
    if decision.get("general"):
        tasks["general"] = asyncio.create_task(run_general(decision["general"], model_name=DEFAULT_MODEL_NAME))
    if decision.get("ha"):
        tasks["ha"] = asyncio.create_task(run_homeassistant(decision["ha"], model_name=DEFAULT_MODEL_NAME))
    if decision.get("chefbyte"):
        tasks["chefbyte"] = asyncio.create_task(run_chefbyte(decision["chefbyte"], model_name=DEFAULT_MODEL_NAME))
    if decision.get("coachbyte"):
        tasks["coachbyte"] = asyncio.create_task(run_coachbyte(decision["coachbyte"], model_name=DEFAULT_MODEL_NAME))

    domain_results: Dict[str, Optional[str]] = {"general": None, "ha": None, "chefbyte": None, "coachbyte": None}
    domain_timings: Dict[str, float] = {"general": 0.0, "ha": 0.0, "chefbyte": 0.0, "coachbyte": 0.0}
    domain_tools: Dict[str, Any] = {"general": [], "ha": [], "chefbyte": [], "coachbyte": []}
    if tasks:
        done = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for (k, _), val in zip(tasks.items(), done):
            if isinstance(val, Exception):
                domain_results[k] = f"ERROR: {val}"
            else:
                if isinstance(val, tuple) and len(val) == 3:
                    domain_results[k] = val[0]
                    domain_timings[k] = float(val[1])
                    domain_tools[k] = val[2]
                elif isinstance(val, tuple) and len(val) == 2:
                    domain_results[k] = val[0]
                    domain_timings[k] = float(val[1])
                else:
                    domain_results[k] = str(val)

    # Synthesize final answer
    model = make_llm(DEFAULT_MODEL_NAME)
    synth_system = SystemMessage(
        content=(
            "You are the output agent. Using the light schema and domain responses, produce a single concise plain-text answer."
        )
    )
    parts = []
    if domain_results.get("general"):
        parts.append(f"- general: {domain_results['general']}")
    if domain_results.get("ha"):
        parts.append(f"- ha: {domain_results['ha']}")
    if domain_results.get("chefbyte"):
        parts.append(f"- chefbyte: {domain_results['chefbyte']}")
    if domain_results.get("coachbyte"):
        parts.append(f"- coachbyte: {domain_results['coachbyte']}")
    domains_block = "\n".join(parts) if parts else "(no domain responses)"
    synth_human = HumanMessage(
        content=(
            f"Light schema:\n{light_schema}\n\nUser input:\n{user_input}\n\nDomain responses:\n{domains_block}"
        )
    )
    t_s = time.perf_counter()
    resp = await model.ainvoke([synth_system, synth_human])
    synth_s = round(time.perf_counter() - t_s, 3)
    final_output = str(resp.content).strip()

    return {
        "domains": [
            {"name": "general", "time_s": round(domain_timings.get("general", 0.0), 3), "output": domain_results.get("general"), "tool_calls": domain_tools.get("general")},
            {"name": "ha", "time_s": round(domain_timings.get("ha", 0.0), 3), "output": domain_results.get("ha"), "tool_calls": domain_tools.get("ha")},
            {"name": "chefbyte", "time_s": round(domain_timings.get("chefbyte", 0.0), 3), "output": domain_results.get("chefbyte"), "tool_calls": domain_tools.get("chefbyte")},
            {"name": "coachbyte", "time_s": round(domain_timings.get("coachbyte", 0.0), 3), "output": domain_results.get("coachbyte"), "tool_calls": domain_tools.get("coachbyte")},
        ],
        "synth": {"time_s": synth_s, "output": final_output},
        "timings": {"routing_s": routing_s},
        "schema_errors": schema_errors,
    }


