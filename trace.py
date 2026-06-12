from dataclasses import dataclass


@dataclass
class Trace:
    prompt: str
    user_intent: str
    selected_tool: str
    tool_input: dict
    tool_output: dict
    final_answer: str
    timestamp: str
