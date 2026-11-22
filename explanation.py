import json


def to_text(data):
    if not data["is_error"]:
        return data["summary"]

    lines = []

    heading = data["error_type"] or "Error"
    if data["location"]:
        heading += f"  ({data['location']})"
    lines.append(heading)
    lines.append("")
    lines.append(data["summary"])
    lines.append(data["details"])

    lines.append("")
    lines.append("LIKELY CAUSES")
    for number, cause in enumerate(data["causes"], start=1):
        lines.append(f"{number}. {cause}")

    lines.append("")
    lines.append("DEBUGGING STEPS")
    for number, step in enumerate(data["steps"], start=1):
        lines.append(f"{number}. {step['text']}")
        if step["code"]:
            for code_line in step["code"].splitlines():
                lines.append(f"      {code_line}")

    lines.append("")
    lines.append("NEXT TIME")
    lines.append(data["prevention"])

    return "\n".join(lines)


def load(saved_text):
    try:
        data = json.loads(saved_text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def display_text(saved_text):
    data = load(saved_text)
    if data is None:
        return saved_text
    return to_text(data)


def to_saved(data):
    return json.dumps(data, ensure_ascii=False)