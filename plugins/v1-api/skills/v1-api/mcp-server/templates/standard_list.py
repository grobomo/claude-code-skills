"""
Standard List Template

For paginated GET requests with:
- top parameter for pagination
- Date range filtering (startDateTime/endDateTime)
- OData filter expressions

Used by: list_alerts, list_blocklist, list_oat, etc.
"""

from .base import api_request, build_date_range, build_pagination, build_odata_filters


def execute(endpoint: str, params: dict, config: dict) -> dict:
    """Execute standard list API call."""
    query_params = {}

    # Build date range
    query_params.update(build_date_range(params, config))

    # Build pagination
    query_params.update(build_pagination(params, config))

    # Build filters
    filters = build_odata_filters(params)
    if filters:
        query_params['filter'] = ' and '.join(filters)

    # Add orderBy if configured
    if config.get('order_by'):
        query_params['orderBy'] = config['order_by']

    return api_request('GET', endpoint, params=query_params)
