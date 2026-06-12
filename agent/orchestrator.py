import json
from datetime import datetime
from openai import OpenAI
from agent.intent_parser import parse
from agent.tool_registry import TOOL_REGISTRY
from trace import Trace

client = OpenAI()


def run_agent(prompt: str) -> Trace:
    intent = parse(prompt)
    tool_name = intent["tool_name"]
    tool_input = intent["tool_input"]
    tool_call_id = intent["tool_call_id"]

    tool_output: dict = {}
    if tool_name and tool_name in TOOL_REGISTRY:
        try:
            tool_output = TOOL_REGISTRY[tool_name]["fn"](**tool_input)
        except Exception as e:
            tool_output = {"status": "error", "message": str(e)}

    if tool_name and tool_output and tool_call_id:
        messages = [
            {"role": "user", "content": prompt},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": tool_name, "arguments": json.dumps(tool_input)},
                }],
            },
            {"role": "tool", "tool_call_id": tool_call_id, "content": json.dumps(tool_output)},
        ]
        response = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
        final_answer = response.choices[0].message.content
    else:
        final_answer = intent["intent_summary"]

    return Trace(
        prompt=prompt,
        user_intent=intent["intent_summary"],
        selected_tool=tool_name or "none",
        tool_input=tool_input,
        tool_output=tool_output,
        final_answer=final_answer,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
