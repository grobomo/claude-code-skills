"""
Search Template

For search/log query GET requests with:
- TMV1-Query header for filter expressions
- Hours-based date range
- top parameter for pagination

Used by: search_endpoint_logs, search_network_logs, search_email_logs, etc.
"""

from .base import api_request, build_date_range, build_pagination


def execute(endpoint: str, params: dict, config: dict) -> dict:
    """Execute search API call."""
    query_params = {}
    extra_headers = {}

    # Build date range (hours-based)
    query_params.update(build_date_range(params, config))

    # Build pagination
    query_params.update(build_pagination(params, config))

    # Handle TMV1-Query header
    if 'filter' in params and params['filter']:
        extra_headers['TMV1-Query'] = params.pop('filter')
    else:
        params.pop('filter', None)
        extra_headers['TMV1-Query'] = config.get('default_filter', '*')

    return api_request('GET', endpoint, params=query_params, headers=extra_headers)
