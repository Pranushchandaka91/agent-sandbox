from tools.weather import get_weather
from tools.calculator import calculate
from tools.notes import manage_notes

TOOL_REGISTRY = {
    "get_weather": {
        "fn": get_weather,
        "definition": {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather information for a given city. Use when the user asks about weather, temperature, or climate conditions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "The name of the city to get weather for."},
                    },
                    "required": ["city"],
                },
            },
        },
    },
    "calculate": {
        "fn": calculate,
        "definition": {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Evaluate a mathematical expression and return the numeric result. Use for arithmetic, calculations, or any math the user needs solved.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "The arithmetic expression to evaluate."},
                    },
                    "required": ["expression"],
                },
            },
        },
    },
    "manage_notes": {
        "fn": manage_notes,
        "definition": {
            "type": "function",
            "function": {
                "name": "manage_notes",
                "description": "Save, retrieve, list, or delete text notes. Use when the user wants to remember something, store information, or recall something they saved earlier.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["save", "get", "list", "delete"],
                            "description": "The action to perform.",
                        },
                        "key": {"type": "string", "description": "Note key/name. Required for save, get, delete."},
                        "content": {"type": "string", "description": "Note content. Required for save."},
                    },
                    "required": ["action"],
                },
            },
        },
    },
}

TOOL_DEFINITIONS = [entry["definition"] for entry in TOOL_REGISTRY.values()]
