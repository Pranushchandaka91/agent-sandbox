import json
import os
import sys
from datetime import datetime
from openai import OpenAI
from agent.tool_registry import TOOL_REGISTRY, TOOL_DEFINITIONS
from agent.token_tracker import TokenTracker
from agent.context import current_tracker
from agent.mcp_client import init_client, get_client, mcp_to_openai
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

# ── MCP startup ───────────────────────────────────────────────────────────────
_mcp_tool_names: set[str] = set()
_mcp_tool_defs:  list[dict] = []

def _init_mcp() -> None:
    if not os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN"):
        return
    mcp = init_client()
    if mcp is None:
        return
    for t in mcp.list_tools():
        _mcp_tool_names.add(t.name)
        _mcp_tool_defs.append(mcp_to_openai(t))

_init_mcp()

ALL_TOOL_DEFINITIONS = TOOL_DEFINITIONS + _mcp_tool_defs


# ── intent label helpers ──────────────────────────────────────────────────────

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
    if tool_name in _mcp_tool_names:
        return f"MCP/{tool_name}: {json.dumps(tool_input)[:60]}"
    return f"Use {tool_name} with {tool_input}"


# ── tool dispatch ─────────────────────────────────────────────────────────────

def _dispatch_tool(tool_name: str, tool_input: dict, tracker: TokenTracker) -> dict:
    """Route a tool call to MCP or the local registry and return an envelope."""
    if tool_name in _mcp_tool_names:
        mcp = get_client()
        if mcp is None or not mcp.connected:
            return {"status": "error", "data": None, "error": "MCP client is not available"}
        try:
            return mcp.call_tool(tool_name, tool_input)
        except Exception as exc:
            return {"status": "error", "data": None, "error": str(exc)}

    if tool_name not in TOOL_REGISTRY:
        return {"status": "error", "data": None, "error": f"Unknown tool '{tool_name}'"}

    _token = current_tracker.set(tracker)
    try:
        return TOOL_REGISTRY[tool_name]["fn"](**tool_input)
    except Exception as exc:
        return {"status": "error", "data": None, "error": str(exc)}
    finally:
        current_tracker.reset(_token)


# ── main agent loop ───────────────────────────────────────────────────────────

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
            tools=ALL_TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        message = response.choices[0].message

        if not message.tool_calls:
            tracker.track(response.usage, "final")
            final_answer = message.content or ""
            break

        tracker.track(response.usage, f"step_{i + 1}")

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

        self_contained_answer = None
        for tc in message.tool_calls:
            step_number += 1
            tool_name  = tc.function.name
            tool_input = json.loads(tc.function.arguments)

            tool_output = _dispatch_tool(tool_name, tool_input, tracker)
            status = tool_output.get("status", "error")

            steps.append({
                "step_number": step_number,
                "tool_name":   tool_name,
                "tool_input":  tool_input,
                "tool_output": tool_output,
                "status":      status,
                "via_mcp":     tool_name in _mcp_tool_names,
            })

            if status == "success":
                data = tool_output.get("data") or {}
                if "answer" in data:
                    self_contained_answer = data["answer"]
                llm_content = json.dumps(data, ensure_ascii=False)
            else:
                llm_content = json.dumps({"error": tool_output.get("error")}, ensure_ascii=False)

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      llm_content,
            })

        if self_contained_answer is not None:
            final_answer = self_contained_answer
            break

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
