import json
import os
from datetime import datetime
from openai import OpenAI
from agent.tool_registry import TOOL_REGISTRY, TOOL_DEFINITIONS
from agent.token_tracker import TokenTracker
from agent.context import current_tracker
from trace import Trace


def _make_client():
    base = OpenAI()
    if os.environ.get("LANGSMITH_TRACING", "").lower() == "true":
        try:
            from langsmith.wrappers import wrap_openai
            return wrap_openai(base)
        except Exception:
            pass
    return base


def _noop(f):
    return f


try:
    if os.environ.get("LANGSMITH_TRACING", "").lower() == "true":
        from langsmith import traceable as _traceable_factory
        _traceable = _traceable_factory(name="agent_run")
    else:
        _traceable = _noop
except Exception:
    _traceable = _noop


client = _make_client()
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
    if tool_name == "github_repo_info":
        return f"Fetch GitHub repository info for {tool_input.get('repo', 'a repo')}"
    if tool_name == "github_readme":
        return f"Fetch README for GitHub repository {tool_input.get('repo', 'a repo')}"
    if tool_name == "query_document":
        return f"RAG query on {tool_input.get('repo', 'a repo')}: {tool_input.get('question', '')[:40]}"
    return f"Use {tool_name} with {tool_input}"


@_traceable
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
                tool_output = {"status": "error", "data": None, "error": f"Unknown tool '{tool_name}'"}
            else:
                _token = current_tracker.set(tracker)
                try:
                    tool_output = TOOL_REGISTRY[tool_name]["fn"](**tool_input)
                except Exception as e:
                    tool_output = {"status": "error", "data": None, "error": str(e)}
                finally:
                    current_tracker.reset(_token)

            status = tool_output.get("status", "error")

            steps.append({
                "step_number": step_number,
                "tool_name":   tool_name,
                "tool_input":  tool_input,
                "tool_output": tool_output,
                "status":      status,
            })

            if status == "success":
                llm_content = json.dumps(tool_output.get("data"), ensure_ascii=False)
            else:
                llm_content = json.dumps({"error": tool_output.get("error")}, ensure_ascii=False)

            messages.append({
                "role":        "tool",
                "tool_call_id": tc.id,
                "content":     llm_content,
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
