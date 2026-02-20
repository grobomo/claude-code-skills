"""
Response Action Template

For POST requests that perform response actions.
Body is an array of action objects.

Used by: isolate_endpoint, quarantine_email, add_to_blocklist, etc.
"""

from .base import api_request


# Body builders for different response action types
BODY_BUILDERS = {
    'endpoint_action': lambda p: [{
        'agentGuid': p['endpoint_guid'],
        'description': p.get('description', '')
    }],
    'file_collect': lambda p: [{
        'agentGuid': p['endpoint_guid'],
        'filePath': p['file_path'],
        'description': p.get('description', '')
    }],
    'process_terminate': lambda p: [{
        'agentGuid': p['endpoint_guid'],
        'fileSha1': p['file_sha1'],
        'description': p.get('description', '')
    }],
    'email_action': lambda p: [{
        'messageId': p['message_id'],
        'mailbox': p['mailbox'],
        'description': p.get('description', '')
    }],
    'blocklist_add': lambda p: [{
        'type': p['ioc_type'],
        'value': p['value'],
        'riskLevel': p.get('risk_level', 'high'),
        'description': p.get('description', ''),
        'daysToExpiration': p.get('days_to_expiration', 0),
    }],
    'blocklist_remove': lambda p: [{
        'type': p['ioc_type'],
        'value': p['value']
    }],
}


def execute(endpoint: str, params: dict, config: dict) -> dict:
    """Execute response action API call."""
    builder_name = config.get('body_builder', 'endpoint_action')
    builder = BODY_BUILDERS.get(builder_name)

    if not builder:
        return {'error': f'Unknown body builder: {builder_name}'}

    body = builder(params)
    return api_request('POST', endpoint, body=body)
