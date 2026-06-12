import re

_SAFE_PATTERN = re.compile(r"^[\d\s\+\-\*\/\(\)\.\%]+$")


def calculate(expression: str) -> dict:
    if not _SAFE_PATTERN.match(expression):
        return {
            "expression": expression,
            "result": None,
            "status": "error",
            "message": "Invalid expression. Only arithmetic operations are allowed.",
        }
    try:
        result = eval(expression, {"__builtins__": {}})  # noqa: S307
        return {"expression": expression, "result": result, "status": "success"}
    except Exception as e:
        return {"expression": expression, "result": None, "status": "error", "message": str(e)}
