INPUT_COST_PER_1K  = 0.00015
OUTPUT_COST_PER_1K = 0.00060


class TokenTracker:
    def __init__(self):
        self.calls: list[dict] = []

    def track(self, usage, call_label: str) -> None:
        self.calls.append({
            "label":             call_label,
            "prompt_tokens":     usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens":      usage.total_tokens,
        })

    def summary(self) -> dict:
        total_prompt     = sum(c["prompt_tokens"]     for c in self.calls)
        total_completion = sum(c["completion_tokens"] for c in self.calls)
        total            = sum(c["total_tokens"]      for c in self.calls)
        cost = (total_prompt / 1000 * INPUT_COST_PER_1K) + (total_completion / 1000 * OUTPUT_COST_PER_1K)
        return {
            "calls":                   self.calls,
            "total_prompt_tokens":     total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens":            total,
            "estimated_cost_usd":      round(cost, 6),
        }
