notes_db: dict[str, str] = {}


def manage_notes(action: str, key: str = None, content: str = None) -> dict:
    if not action or not action.strip():
        return {"status": "error", "data": None, "error": "action parameter is required."}

    if action == "save":
        if not key:
            return {"status": "error", "data": None, "error": "key is required for save."}
        notes_db[key] = content or ""
        return {
            "status": "success",
            "data":   {"action": "save", "key": key, "message": f"Note saved under '{key}'."},
            "error":  None,
        }

    if action == "get":
        if not key:
            return {"status": "error", "data": None, "error": "key is required for get."}
        if key not in notes_db:
            return {"status": "error", "data": None, "error": f"Note '{key}' not found."}
        return {
            "status": "success",
            "data":   {"action": "get", "key": key, "content": notes_db[key]},
            "error":  None,
        }

    if action == "list":
        return {
            "status": "success",
            "data":   {"action": "list", "notes": dict(notes_db), "count": len(notes_db)},
            "error":  None,
        }

    if action == "delete":
        if not key:
            return {"status": "error", "data": None, "error": "key is required for delete."}
        if key not in notes_db:
            return {"status": "error", "data": None, "error": f"Note '{key}' not found."}
        del notes_db[key]
        return {
            "status": "success",
            "data":   {"action": "delete", "key": key, "message": f"Note '{key}' deleted."},
            "error":  None,
        }

    return {"status": "error", "data": None, "error": f"Unknown action '{action}'."}
