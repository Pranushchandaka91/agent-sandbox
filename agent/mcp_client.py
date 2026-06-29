import asyncio
import base64
import json
import os
import sys
import threading
from contextlib import AsyncExitStack
from typing import Optional

_GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


class MCPClient:
    """Synchronous wrapper around the async MCP SDK.

    Runs a dedicated event loop in a background thread so the rest of the
    codebase stays synchronous.  The SSE/HTTP connection is kept alive for
    the lifetime of the process via AsyncExitStack.
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._session = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._tools: list = []
        self.connected = False

    def _run_sync(self, coro, timeout: int = 30):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=timeout)

    async def _do_connect(self) -> list:
        token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            raise RuntimeError(
                "GITHUB_PERSONAL_ACCESS_TOKEN is not set. "
                "This token is required to connect to the GitHub MCP server."
            )

        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        headers = {
            "Authorization": f"Bearer {token}",
            "X-MCP-Readonly": "true",
            "X-MCP-Toolsets": "repos",
        }

        self._exit_stack = AsyncExitStack()
        read, write, _ = await self._exit_stack.enter_async_context(
            streamablehttp_client(url=_GITHUB_MCP_URL, headers=headers)
        )
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self._session.initialize()

        result = await self._session.list_tools()
        self._tools = list(result.tools)
        self.connected = True
        return self._tools

    def connect(self) -> list:
        self._tools = self._run_sync(self._do_connect(), timeout=30)
        return self._tools

    def list_tools(self) -> list:
        return self._tools

    async def _do_call_tool(self, name: str, arguments: dict):
        return await self._session.call_tool(name, arguments)

    def call_tool_raw(self, name: str, arguments: dict):
        """Return the raw CallToolResult for callers that need full content access."""
        return self._run_sync(self._do_call_tool(name, arguments))

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool and return the normalized {status, data, error} envelope."""
        return normalize(self.call_tool_raw(name, arguments))


def _collect_text(result) -> list[str]:
    """Collect all text from a CallToolResult, including EmbeddedResource bodies.

    The GitHub MCP server puts file content in EmbeddedResource items and uses
    TextContent only for short status messages.  We gather both so callers can
    decide what to use.
    """
    parts: list[str] = []
    for c in result.content:
        if hasattr(c, "text") and c.text:
            parts.append(c.text)
        elif hasattr(c, "resource"):
            resource = c.resource
            if hasattr(resource, "text") and resource.text:
                parts.append(resource.text)
            elif hasattr(resource, "blob") and resource.blob:
                try:
                    parts.append(
                        base64.b64decode(resource.blob).decode("utf-8", errors="replace")
                    )
                except Exception:
                    pass
    return parts


def extract_resource_content(result) -> Optional[str]:
    """Return the primary file/resource content from a CallToolResult.

    Prefers EmbeddedResource over TextContent because GitHub MCP wraps file
    bodies in EmbeddedResource and uses TextContent for status messages like
    "successfully downloaded text file (SHA: ...)".
    """
    # Prefer EmbeddedResource (actual file body)
    for c in result.content:
        if hasattr(c, "resource"):
            resource = c.resource
            if hasattr(resource, "text") and resource.text:
                return resource.text
            if hasattr(resource, "blob") and resource.blob:
                try:
                    return base64.b64decode(resource.blob).decode("utf-8", errors="replace")
                except Exception:
                    pass

    # Fallback: join all TextContent
    parts = [c.text for c in result.content if hasattr(c, "text") and c.text]
    return "\n".join(parts) if parts else None


def normalize(result) -> dict:
    """Wrap an MCP CallToolResult into the {status, data, error} envelope."""
    if getattr(result, "isError", False):
        error_text = " ".join(
            c.text for c in result.content if hasattr(c, "text")
        ) or "MCP tool call failed"
        return {"status": "error", "data": None, "error": error_text}

    parts = _collect_text(result)
    combined = "\n".join(parts)

    try:
        data = json.loads(combined)
    except (json.JSONDecodeError, ValueError):
        data = {"text": combined}

    return {"status": "success", "data": data, "error": None}


def mcp_to_openai(mcp_tool) -> dict:
    """Convert an MCP tool definition to the OpenAI function-calling format."""
    schema = mcp_tool.inputSchema
    if not isinstance(schema, dict):
        schema = {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description or "",
            "parameters": schema,
        },
    }


# Module-level singleton — initialised once by the orchestrator at startup.
_client: Optional[MCPClient] = None


def get_client() -> Optional[MCPClient]:
    return _client


def init_client() -> Optional[MCPClient]:
    """Connect to the GitHub MCP server and return the client.

    Returns None (and prints a warning) on any failure so the rest of the
    sandbox keeps working with local tools only.
    """
    global _client
    try:
        _client = MCPClient()
        _client.connect()
        tool_names = [t.name for t in _client.list_tools()]
        print(
            f"[MCP] Connected to GitHub MCP server. "
            f"{len(tool_names)} tools available: {', '.join(tool_names[:6])}"
            + (" …" if len(tool_names) > 6 else ""),
            file=sys.stderr,
        )
        return _client
    except Exception as exc:
        print(f"[MCP] Connection failed — falling back to local tools only. ({exc})", file=sys.stderr)
        _client = None
        return None
