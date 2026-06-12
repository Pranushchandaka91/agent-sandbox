import json
from openai import OpenAI
from agent.tool_registry import TOOL_DEFINITIONS

client = OpenAI()

_INTENT_LABELS = {
    "get_weather":  lambda p: f"Get current weather for {p.get('city', 'a city')}",
    "calculate":    lambda p: f"Evaluate arithmetic expression: {p.get('expression', '')}",
    "manage_notes": lambda p: {
        "save":   f"Save note '{p.get('key', '')}' with provided content",
        "get":    f"Retrieve note '{p.get('key', '')}'",
        "list":   "List all saved notes",
        "delete": f"Delete note '{p.get('key', '')}'",
    }.get(p.get("action", ""), f"Manage notes: {p.get('action', '')}"),
}


def parse(prompt: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
    )
    message = response.choices[0].message

    if message.tool_calls:
        tool_call = message.tool_calls[0]
        tool_name = tool_call.function.name
        tool_input = json.loads(tool_call.function.arguments)
        labeler = _INTENT_LABELS.get(tool_name)
        intent_summary = labeler(tool_input) if labeler else f"Use {tool_name} with {tool_input}"
        return {
            "intent_summary": intent_summary,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_call_id": tool_call.id,
        }

    return {
        "intent_summary": message.content or "No tool required",
        "tool_name": None,
        "tool_input": {},
        "tool_call_id": None,
    }
