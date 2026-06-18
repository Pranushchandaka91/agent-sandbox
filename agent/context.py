from contextvars import ContextVar

# Holds the active TokenTracker for the current agent run so tools can
# track their own OpenAI calls without changing the tool interface.
current_tracker: ContextVar = ContextVar("current_tracker", default=None)
