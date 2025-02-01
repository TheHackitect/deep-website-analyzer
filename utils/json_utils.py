# utils/json_utils.py
import json
from datetime import datetime
from typing import Any

def json_serial(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def serialize_json(data: Any) -> str:
    """Serialize data to JSON, handling datetime objects."""
    return json.dumps(data, default=json_serial, indent=4)

def generate_session_id() -> str:
    """Generate a unique session ID based on the current timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")