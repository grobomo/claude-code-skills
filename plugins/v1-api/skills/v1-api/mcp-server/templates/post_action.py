"""
Post Action Template

For POST requests with object body (not array).

Used by: run_script, scan_iac_template, add_alert_note, etc.
"""

from .base import api_request


# Body builders for different POST action types
BODY_BUILDERS = {
    'alert_note': lambda p: {'content': p['content']},
    'script_run': lambda p: {
        'scriptId': p['script_id'],
        'agentGuids': p['endpoint_guids'],
        'parameter': p.get('parameters', '')
    },
    'iac_scan': lambda p: {
        'type': p['template_type'],
        'content': p['content']
    },
    'empty': lambda p: {},
}


def execute(endpoint: str, params: dict, config: dict) -> dict:
    """Execute POST action API call."""
    builder_name = config.get('body_builder', 'empty')
    builder = BODY_BUILDERS.get(builder_name, BODY_BUILDERS['empty'])

    body = builder(params)
    return api_request('POST', endpoint, body=body)
