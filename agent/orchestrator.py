import json
from datetime import datetime
from openai import OpenAI
from agent.tool_registry import TOOL_REGISTRY, TOOL_DEFINITIONS
from agent.token_tracker import TokenTracker
from trace import Trace

client = OpenAI()
MAX_STEPS = 10


def _intent_label(tool_name: str, tool_input: dict) -> str:
    if tool_name == "get_weather":
        return f"Get current weather for {tool_input.get('city', 'a city')}"
    if tool_name == "calculate":
        return f"Evaluate arithmetic expression: {tool_input.get('expression', '')}"
    if tool_name == "manage_notes":
        action = tool_input.get("action", "")
        key = tool_input.get("key", "")
        return {
            "save":   f"Save note '{key}' with provided content",
            "get":    f"Retrieve note '{key}'",
            "list":   "List all saved notes",
            "delete": f"Delete note '{key}'",
        }.get(action, f"Manage notes: {action}")
    return f"Use {tool_name} with {tool_input}"


def run_agent(prompt: str) -> Trace:
    tracker = TokenTracker()
    messages = [{"role": "user", "content": prompt}]
    steps: list[dict] = []
    step_number = 0
    final_answer = "Max steps reached without a final response."

    for i in range(MAX_STEPS):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        message = response.choices[0].message

        if not message.tool_calls:
            tracker.track(response.usage, "final")
            final_answer = message.content or ""
            break

        tracker.track(response.usage, f"step_{i + 1}")

        # Append the assistant turn with all tool calls
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        })

        # Execute each tool call and append results
        for tc in message.tool_calls:
            step_number += 1
            tool_name = tc.function.name
            tool_input = json.loads(tc.function.arguments)

            if tool_name not in TOOL_REGISTRY:
                tool_output = {"status": "error", "message": f"Unknown tool '{tool_name}'"}
                status = "error"
            else:
                try:
                    tool_output = TOOL_REGISTRY[tool_name]["fn"](**tool_input)
                    status = "success"
                except Exception as e:
                    tool_output = {"status": "error", "message": str(e)}
                    status = "error"

            steps.append({
                "step_number": step_number,
                "tool_name":   tool_name,
                "tool_input":  tool_input,
                "tool_output": tool_output,
                "status":      status,
            })

            messages.append({
                "role":        "tool",
                "tool_call_id": tc.id,
                "content":     json.dumps(tool_output, ensure_ascii=False),
            })

    summary = tracker.summary()
    first = steps[0] if steps else {}

    return Trace(
        prompt=prompt,
        user_intent=_intent_label(first.get("tool_name", ""), first.get("tool_input", {})) if first else "No tool required",
        selected_tool=first.get("tool_name", "none"),
        tool_input=first.get("tool_input", {}),
        tool_output=first.get("tool_output", {}),
        final_answer=final_answer,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        steps=steps,
        token_calls=summary["calls"],
        total_tokens=summary["total_tokens"],
        estimated_cost_usd=summary["estimated_cost_usd"],
    )
