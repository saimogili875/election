import json

def sse_message(event_type: str, data: dict) -> str:
    """Format a message string according to the Server-Sent Events protocol."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"

def sse_comment(comment: str = "keep-alive") -> str:
    """Format an SSE comment (useful as heartbeat)."""
    return f": {comment}\n\n"
