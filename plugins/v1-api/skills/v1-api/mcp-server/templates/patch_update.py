"""
Patch Update Template

For PATCH requests that update resources.

Used by: update_alert, etc.
"""

from .base import api_request


# Body builders for different PATCH types
BODY_BUILDERS = {
    'alert_update': lambda p: {
        'investigationStatus': p.get('status'),
        **({"investigationResult": p['result']} if p.get('result') else {})
    },
}


def execute(endpoint: str, params: dict, config: dict) -> dict:
    """Execute PATCH update API call."""
    builder_name = config.get('body_builder', 'alert_update')
    builder = BODY_BUILDERS.get(builder_name)

    if not builder:
        return {'error': f'Unknown body builder: {builder_name}'}

    body = builder(params)
    return api_request('PATCH', endpoint, body=body)
