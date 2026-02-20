"""
Simple List Template

For GET requests with no pagination or filtering parameters.
Returns all items.

Used by: list_roles, list_policies, etc.
"""

from .base import api_request


def execute(endpoint: str, params: dict, config: dict) -> dict:
    """Execute simple list API call."""
    return api_request('GET', endpoint)
