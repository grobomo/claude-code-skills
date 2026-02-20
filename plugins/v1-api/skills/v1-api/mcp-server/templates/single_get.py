"""
Single Get Template

For GET requests that retrieve a single resource by ID.
No pagination or date filtering.

Used by: get_alert, get_endpoint, get_device, etc.
"""

from .base import api_request


def execute(endpoint: str, params: dict, config: dict) -> dict:
    """Execute single resource GET."""
    # Path params should already be substituted in endpoint
    # Any remaining params become query params
    return api_request('GET', endpoint, params=params if params else None)
