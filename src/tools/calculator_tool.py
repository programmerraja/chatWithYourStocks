import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

CALCULATOR_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_calculator",
        "description": "Perform mathematical calculations. Supports basic arithmetic (+, -, *, /) and math functions",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate (e.g., '2 + 2', '15 * 0.2').",
                }
            },
            "required": ["expression"],
        },
    },
}


def execute_calculator(expression: str) -> str:
    try:
        allowed_names = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
        }

        result = eval(expression, {"__builtins__": None}, allowed_names)

        logger.info(f"Calculator executed: {expression} = {result}")

        return json.dumps({"success": True, "result": result, "expression": expression})

    except Exception as e:
        logger.error(f"Calculator failed for expression '{expression}': {e}")
        return json.dumps({"success": False, "error": str(e), "expression": expression})


def get_tool_schema() -> Dict[str, Any]:
    return CALCULATOR_TOOL_SCHEMA
