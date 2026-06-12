import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
import textwrap
from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("OPENAI_API_KEY"):
    sys.exit("OPENAI_API_KEY not found in .env")

from agent.orchestrator import run_agent  # noqa: E402 — must load env first
from trace import Trace  # noqa: E402

PROMPTS = [
    "What's the weather like in Hyderabad today?",
    "Calculate 847 multiplied by 23",
    "Save a note called 'standup' with content: push agent sandbox PR today",
    "What notes do I have saved?",
]

# ── box dimensions ────────────────────────────────────────────
# │  LABEL         │ CONTENT                                   │
# 1 + 2 + 13 + 3 + 51 + 2 = 72 chars total
BOX_WIDTH    = 72
LABEL_WIDTH  = 13
CONTENT_WIDTH = 51


def _render_value(value) -> list[str]:
    if isinstance(value, dict):
        raw = json.dumps(value, indent=2, ensure_ascii=False)
    else:
        raw = str(value)
    lines = raw.splitlines() or [""]
    result = []
    for line in lines:
        if len(line) <= CONTENT_WIDTH:
            result.append(line)
        else:
            result.extend(textwrap.wrap(line, CONTENT_WIDTH) or [""])
    return result


def _data_row(label: str, value) -> list[str]:
    content_lines = _render_value(value)
    rows = []
    for i, line in enumerate(content_lines):
        lbl = label if i == 0 else ""
        rows.append(f"│  {lbl:<{LABEL_WIDTH}} │ {line:<{CONTENT_WIDTH}} │")
    return rows


def print_trace(trace: Trace) -> None:
    hr  = "─" * (BOX_WIDTH - 2)
    top = "┌" + hr + "┐"
    sep = "├" + hr + "┤"
    bot = "└" + hr + "┘"

    print(top)
    print(f"│  {'AGENT TRACE — ' + trace.timestamp:<{BOX_WIDTH - 4}}  │")
    print(sep)
    for row in _data_row("PROMPT",        trace.prompt):       print(row)
    for row in _data_row("USER INTENT",   trace.user_intent):  print(row)
    for row in _data_row("SELECTED TOOL", trace.selected_tool): print(row)
    for row in _data_row("TOOL INPUT",    trace.tool_input):   print(row)
    for row in _data_row("TOOL OUTPUT",   trace.tool_output):  print(row)
    for row in _data_row("FINAL ANSWER",  trace.final_answer): print(row)
    print(bot)
    print()


if __name__ == "__main__":
    for prompt in PROMPTS:
        print(f"Running: {prompt!r}")
        trace = run_agent(prompt)
        print_trace(trace)
