from tools.weather import get_weather
from tools.calculator import calculate
from tools.notes import manage_notes
from tools.github import github_repo_info, github_readme
from tools.rag_tool import query_document

TOOL_REGISTRY = {
    "get_weather": {
        "fn": get_weather,
        "definition": {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather information for a given city. Use when the user asks about weather, temperature, or climate conditions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "The name of the city to get weather for."},
                    },
                    "required": ["city"],
                },
            },
        },
    },
    "calculate": {
        "fn": calculate,
        "definition": {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Evaluate a mathematical expression and return the numeric result. Use for arithmetic, calculations, or any math the user needs solved.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "The arithmetic expression to evaluate."},
                    },
                    "required": ["expression"],
                },
            },
        },
    },
    "manage_notes": {
        "fn": manage_notes,
        "definition": {
            "type": "function",
            "function": {
                "name": "manage_notes",
                "description": "Save, retrieve, list, or delete text notes. Use when the user wants to remember something, store information, or recall something they saved earlier.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["save", "get", "list", "delete"],
                            "description": "The action to perform.",
                        },
                        "key": {"type": "string", "description": "Note key/name. Required for save, get, delete."},
                        "content": {"type": "string", "description": "Note content. Required for save."},
                    },
                    "required": ["action"],
                },
            },
        },
    },
    "github_repo_info": {
        "fn": github_repo_info,
        "definition": {
            "type": "function",
            "function": {
                "name": "github_repo_info",
                "description": "Get information about a GitHub repository including stars, language, description, and open issues. Input is 'owner/repo'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "Repository in 'owner/name' format, e.g. 'Pranushchandaka91/agent-sandbox'."},
                    },
                    "required": ["repo"],
                },
            },
        },
    },
    "github_readme": {
        "fn": github_readme,
        "definition": {
            "type": "function",
            "function": {
                "name": "github_readme",
                "description": "Fetch the README content of a GitHub repository as plain text. Input is 'owner/repo'. Use when the user wants to read or summarize what a repository is about.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "Repository in 'owner/name' format, e.g. 'Pranushchandaka91/agent-sandbox'."},
                    },
                    "required": ["repo"],
                },
            },
        },
    },
    "query_document": {
        "fn": query_document,
        "definition": {
            "type": "function",
            "function": {
                "name": "query_document",
                "description": "Answer a specific question about a GitHub repository's README using retrieval. Use when the user asks a detailed or specific question about what a repo does, rather than just basic repo stats. Inputs: 'repo' (owner/name) and 'question'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo":     {"type": "string", "description": "Repository in 'owner/name' format, e.g. 'Pranushchandaka91/agent-sandbox'."},
                        "question": {"type": "string", "description": "The specific question to answer from the repository's README."},
                    },
                    "required": ["repo", "question"],
                },
            },
        },
    },
}

TOOL_DEFINITIONS = [entry["definition"] for entry in TOOL_REGISTRY.values()]
