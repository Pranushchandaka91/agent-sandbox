import re

_SAFE_PATTERN = re.compile(r"^[\d\s\+\-\*\/\(\)\.\%]+$")


def calculate(expression: str) -> dict:
    if not expression or not expression.strip():
        return {"status": "error", "data": None, "error": "expression parameter is required."}
    if not _SAFE_PATTERN.match(expression):
        return {
            "status": "error",
            "data":   None,
            "error":  "Invalid expression. Only arithmetic operations are allowed.",
        }
    try:
        result = eval(expression, {"__builtins__": {}})  # noqa: S307
        return {"status": "success", "data": {"expression": expression, "result": result}, "error": None}
    except Exception as e:
        return {"status": "error", "data": None, "error": str(e)}
