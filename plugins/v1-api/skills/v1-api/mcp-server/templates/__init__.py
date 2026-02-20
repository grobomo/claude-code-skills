"""
V1 API Templates

Each template handles a specific API call pattern. Templates are referenced
by YAML files in api_index/ and called by the MCP server.

Template functions take:
  - endpoint: str - API path (with {placeholders} already substituted)
  - params: dict - User-provided parameters
  - config: dict - Template config from YAML

Template functions return:
  - dict - API response or {"error": "message"}
"""

from .standard_list import execute as standard_list
from .search import execute as search
from .single_get import execute as single_get
from .simple_list import execute as simple_list
from .response_action import execute as response_action
from .post_action import execute as post_action
from .patch_update import execute as patch_update

TEMPLATES = {
    "standard_list": standard_list,
    "search": search,
    "single_get": single_get,
    "simple_list": simple_list,
    "response_action": response_action,
    "post_action": post_action,
    "patch_update": patch_update,
}

def get_template(name: str):
    """Get template function by name."""
    return TEMPLATES.get(name)
