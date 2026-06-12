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
