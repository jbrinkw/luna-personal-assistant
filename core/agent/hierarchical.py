"""Hierarchical agent shim.

Exposes the required async API by delegating to the planner+tools agent
implemented in `core/agent/simple_passthough.py`.

The OpenAI-compatible server discovers agents by importing modules under
`core/agent/` that export an async `run_agent(...)` function. This shim allows
the historical model id `hierarchical` to resolve to the current hierarchical
planner implementation without duplicating code.
"""

from core.agent.simple_passthough import (  # type: ignore
    run_agent as run_agent,
    initialize_runtime as initialize_runtime,
    _active_models as _active_models,
    AgentResult as AgentResult,
)

# Optional: If a streaming implementation is needed later, it can be added here
# to enable token-by-token SSE in the OpenAI-compatible server. For now, the
# server will fall back to single-chunk streaming when `run_agent_stream` is not
# present.

