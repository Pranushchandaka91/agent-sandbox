notes_db: dict[str, str] = {}


def manage_notes(action: str, key: str = None, content: str = None) -> dict:
    if action == "save":
        notes_db[key] = content
        return {"action": "save", "key": key, "status": "success", "message": f"Note saved under '{key}'."}

    if action == "get":
        if key not in notes_db:
            return {"action": "get", "key": key, "status": "error", "message": f"Note '{key}' not found."}
        return {"action": "get", "key": key, "content": notes_db[key], "status": "success"}

    if action == "list":
        return {"action": "list", "notes": dict(notes_db), "count": len(notes_db)}

    if action == "delete":
        if key not in notes_db:
            return {"action": "delete", "key": key, "status": "error", "message": f"Note '{key}' not found."}
        del notes_db[key]
        return {"action": "delete", "key": key, "status": "success", "message": f"Note '{key}' deleted."}

    return {"action": action, "status": "error", "message": f"Unknown action '{action}'."}
