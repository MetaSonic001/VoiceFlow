"""
voiceflow.tools — @voice_tool decorator.

Lets developers register custom tools as decorated Python functions.
The framework auto-generates the LLM tool description from the function
signature and docstring — same pattern as FastMCP.

Example:
    from voiceflow.tools import voice_tool

    @voice_tool
    async def get_appointment_slots(date: str, doctor_id: str = None) -> list[str]:
        '''
        Get available appointment slots for a doctor on a given date.

        Args:
            date: ISO date string (YYYY-MM-DD)
            doctor_id: Optional doctor ID to filter by

        Returns:
            List of available time slot strings
        '''
        slots = await my_calendar_api.get_slots(date, doctor_id)
        return [s.time_str for s in slots]

    # Register with an agent:
    agent.add_tool(get_appointment_slots)
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional, get_type_hints

logger = logging.getLogger("voiceflow.tools")


def voice_tool(fn: Callable) -> Callable:
    """
    Decorator that marks a function as a callable voice tool.
    Auto-generates the LLM function-calling schema from signature + docstring.
    Works with both sync and async functions.
    """
    sig = inspect.signature(fn)
    hints = get_type_hints(fn) if fn.__annotations__ else {}
    docstring = inspect.getdoc(fn) or ""
    desc_line = docstring.split("\n")[0] if docstring else fn.__name__

    # Build JSON schema from parameters
    params_schema: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        py_type = hints.get(param_name, str)
        json_type = _py_type_to_json(py_type)
        # Extract arg description from docstring
        arg_desc = _extract_arg_doc(docstring, param_name)
        param_schema: dict[str, Any] = {"type": json_type, "description": arg_desc}
        if json_type == "array":
            param_schema["items"] = {"type": "string"}
        params_schema["properties"][param_name] = param_schema
        if param.default is inspect.Parameter.empty:
            params_schema["required"].append(param_name)

    # Attach metadata to the function
    fn._voice_tool_meta = {  # type: ignore[attr-defined]
        "name": fn.__name__,
        "description": desc_line,
        "parameters": params_schema,
    }

    @wraps(fn)
    async def wrapper(*args, **kwargs) -> Any:
        if asyncio.iscoroutinefunction(fn):
            return await fn(*args, **kwargs)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    wrapper._voice_tool_meta = fn._voice_tool_meta  # type: ignore[attr-defined]
    return wrapper


def _py_type_to_json(py_type) -> str:
    if py_type in (str, Optional[str]):
        return "string"
    if py_type in (int, Optional[int]):
        return "integer"
    if py_type in (float, Optional[float]):
        return "number"
    if py_type in (bool, Optional[bool]):
        return "boolean"
    if py_type in (list,) or str(py_type).startswith("list"):
        return "array"
    if py_type in (dict,) or str(py_type).startswith("dict"):
        return "object"
    return "string"


def _extract_arg_doc(docstring: str, param_name: str) -> str:
    """Extract per-argument description from NumPy or Google-style docstrings."""
    for line in docstring.split("\n"):
        stripped = line.strip()
        if stripped.startswith(f"{param_name}:") or stripped.startswith(f"{param_name} "):
            _, _, desc = stripped.partition(":")
            return desc.strip()
    return ""


def get_tool_schema(tool_fn: Callable) -> dict:
    """Return the LLM function-calling schema for a @voice_tool decorated function."""
    meta = getattr(tool_fn, "_voice_tool_meta", None)
    if not meta:
        raise ValueError(f"{tool_fn.__name__} is not decorated with @voice_tool")
    return {
        "type": "function",
        "function": {
            "name": meta["name"],
            "description": meta["description"],
            "parameters": meta["parameters"],
        },
    }


async def execute_tool(tool_fn: Callable, arguments: dict | str) -> Any:
    """
    Execute a @voice_tool function with the given arguments.
    arguments can be a dict or a JSON string (as returned by the LLM).
    """
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    try:
        return await tool_fn(**arguments)
    except Exception as exc:
        logger.warning("[voice_tool] execution error in %s: %s", tool_fn.__name__, exc)
        return {"error": str(exc)}
