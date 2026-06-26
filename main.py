import sys
sys.stdout.reconfigure(encoding='utf-8')
import argparse
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
    "What is the weather in Hyderabad and Mumbai, and what is the temperature difference between them?",
    "Save a note called 'weather' with the current temperature in Delhi, then list all my notes.",
    "Tell me about the GitHub repo sahithsundarw/sentinel — how many stars does it have and what language is it in?",
    "Fetch the README for sahithsundarw/sentinel and give me a two-sentence summary of what the project does.",
    "Using the README, what was the key finding about supervised fine-tuning in sahithsundarw/sentinel?",
    "According to its README, what reward does the Q-learner get for a correct block in sahithsundarw/sentinel?",
]

GITHUB_PROMPTS = PROMPTS[6:8]
RAG_PROMPTS    = PROMPTS[8:10]

# ── trace box dimensions ──────────────────────────────────────
BOX_WIDTH     = 72
LABEL_WIDTH   = 13
CONTENT_WIDTH = 51

# ── token table column widths ─────────────────────────────────
TC1, TC2, TC3, TC4 = 13, 8, 12, 7


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
    for row in _data_row("PROMPT",        trace.prompt):        print(row)
    for row in _data_row("USER INTENT",   trace.user_intent):   print(row)
    for row in _data_row("SELECTED TOOL", trace.selected_tool): print(row)
    for row in _data_row("TOOL INPUT",    trace.tool_input):    print(row)
    for row in _data_row("TOOL OUTPUT",   trace.tool_output):   print(row)
    for row in _data_row("FINAL ANSWER",  trace.final_answer):  print(row)
    print(bot)
    print()
    print_token_usage(trace)


def print_token_usage(trace: Trace) -> None:
    divider = "  " + "─" * (TC1 + TC2 + TC3 + TC4 + 11)
    header  = f"  {'call':<{TC1}} │ {'prompt':<{TC2}} │ {'completion':<{TC3}} │ {'total':<{TC4}}"

    print("TOKEN USAGE")
    print(header)
    for call in trace.token_calls:
        print(
            f"  {call['label']:<{TC1}} │ "
            f"{call['prompt_tokens']:<{TC2}} │ "
            f"{call['completion_tokens']:<{TC3}} │ "
            f"{call['total_tokens']:<{TC4}}"
        )

    total_prompt     = sum(c["prompt_tokens"]     for c in trace.token_calls)
    total_completion = sum(c["completion_tokens"] for c in trace.token_calls)

    print(divider)
    print(
        f"  {'TOTAL':<{TC1}} │ "
        f"{total_prompt:<{TC2}} │ "
        f"{total_completion:<{TC3}} │ "
        f"{trace.total_tokens:<{TC4}}"
    )
    print(f"  {'EST. COST':<{TC1}} │ ${trace.estimated_cost_usd:.6f}")
    print()


def run_prompts(prompts: list[str]) -> None:
    for prompt in prompts:
        print(f"Running: {prompt!r}")
        trace = run_agent(prompt)
        print_trace(trace)


def run_interactive() -> None:
    repo = input("Enter GitHub repo (owner/name): ").strip()
    if not repo or "/" not in repo:
        print("Invalid repo format. Expected owner/name.")
        return

    print(f"\nRepo: {repo}  |  Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if question.lower() in ("exit", "quit"):
            print("Goodbye.")
            break
        if not question:
            continue

        prompt = f"Answer this question about the {repo} GitHub repo using its code and documentation: {question}"
        trace = run_agent(prompt)
        print_trace(trace)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Sandbox runner")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all",         action="store_true", help="Run all test prompts")
    group.add_argument("--github",      action="store_true", help="Run the 2 GitHub prompts")
    group.add_argument("--rag",         action="store_true", help="Run the 2 RAG prompts")
    group.add_argument("--interactive", action="store_true", help="Launch interactive CLI")
    args = parser.parse_args()

    if args.all:
        run_prompts(PROMPTS)
    elif args.github:
        run_prompts(GITHUB_PROMPTS)
    elif args.rag:
        run_prompts(RAG_PROMPTS)
    else:
        run_interactive()
