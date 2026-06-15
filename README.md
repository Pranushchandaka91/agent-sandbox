# Agent Sandbox

A CLI tool that demonstrates the core agent loop — intent parsing, tool 
selection, execution, and response generation — using OpenAI function calling.

## What it does

Runs 4 test prompts through an agent and prints a formatted reasoning trace 
for each. Developers can use the trace to understand and debug agent behavior.

## Tools

- get_weather — returns dummy weather data for a city
- calculate — evaluates arithmetic expressions safely
- manage_notes — saves, retrieves, lists, and deletes in-memory notes

## Setup

1. Clone the repo
2. Install dependencies: pip install openai python-dotenv
3. Create a .env file with your OpenAI key: OPENAI_API_KEY=your_key_here
4. Run: python main.py

## Output

Each prompt produces a trace showing:
- Prompt
- User Intent
- Selected Tool
- Tool Input
- Tool Output
- Final Answer

## Observability (LangSmith)

The sandbox automatically sends token usage, cost, and latency data to [LangSmith](https://smith.langchain.com/) when configured. To enable it, set the following in your `.env`:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key_here
LANGSMITH_PROJECT=agent-sandbox
```

Each call to `run_agent` appears as a named trace (`agent_run`) in the LangSmith dashboard, with all nested OpenAI calls captured automatically via the wrapped client.

The sandbox runs fine without LangSmith — if `LANGSMITH_TRACING` is not `true` or the package is unavailable, all LangSmith code is silently skipped and the existing console TOKEN USAGE table is unaffected.
