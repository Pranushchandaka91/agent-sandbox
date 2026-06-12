from dataclasses import dataclass, field


@dataclass
class Trace:
    prompt: str
    user_intent: str
    selected_tool: str
    tool_input: dict
    tool_output: dict
    final_answer: str
    timestamp: str
    steps: list = field(default_factory=list)
    token_calls: list = field(default_factory=list)
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
