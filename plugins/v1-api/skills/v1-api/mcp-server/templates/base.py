"""
Base utilities for V1 API templates.
"""

import os
import requests
from datetime import datetime, timedelta

# Connection pooling for performance
_session = None

def get_session() -> requests.Session:
    """Get or create reusable session with connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=requests.adapters.Retry(total=2, backoff_factor=0.5)
        )
        _session.mount('https://', adapter)
    return _session

REGION_URLS = {
    'us': 'https://api.xdr.trendmicro.com',
    'eu': 'https://api.eu.xdr.trendmicro.com',
    'jp': 'https://api.xdr.trendmicro.co.jp',
    'sg': 'https://api.sg.xdr.trendmicro.com',
    'au': 'https://api.au.xdr.trendmicro.com',
    'in': 'https://api.in.xdr.trendmicro.com',
    'ae': 'https://api.mea.xdr.trendmicro.com',
}


def get_base_url() -> str:
    """Get base URL for current region."""
    region = os.environ.get('V1_REGION', 'us')
    return REGION_URLS.get(region, REGION_URLS['us'])


def get_headers(extra_headers: dict = None) -> dict:
    """Get standard API headers."""
    api_key = os.environ.get('V1_API_KEY', '')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'v1-lite-mcp/1.0'
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def build_date_range(params: dict, config: dict) -> dict:
    """Build date range query params from config."""
    query_params = {}
    date_cfg = config.get('date_params')
    if not date_cfg:
        return query_params

    unit = date_cfg.get('unit', 'days')
    if unit == 'days' and 'days' in params:
        end = datetime.utcnow()
        start = end - timedelta(days=params.pop('days'))
        query_params[date_cfg['start']] = start.strftime('%Y-%m-%dT%H:%M:%SZ')
        query_params[date_cfg['end']] = end.strftime('%Y-%m-%dT%H:%M:%SZ')
    elif unit == 'hours' and 'hours' in params:
        end = datetime.utcnow()
        start = end - timedelta(hours=params.pop('hours'))
        query_params[date_cfg['start']] = start.strftime('%Y-%m-%dT%H:%M:%SZ')
        query_params[date_cfg['end']] = end.strftime('%Y-%m-%dT%H:%M:%SZ')

    return query_params


def build_pagination(params: dict, config: dict) -> dict:
    """Build pagination query params from config."""
    query_params = {}
    pag = config.get('pagination')
    if not pag or 'limit' not in params:
        params.pop('limit', None)
        return query_params

    limit = params.pop('limit')
    if pag['type'] == 'enum':
        values = pag['values']
        top_val = min(values, key=lambda x: abs(x - limit) if limit <= x else float('inf'))
        if limit > max(values):
            top_val = max(values)
        query_params[pag['param']] = str(top_val)
    elif pag['type'] == 'int':
        query_params[pag['param']] = str(min(limit, pag['max']))

    return query_params


def build_odata_filters(params: dict) -> list:
    """Build OData filter expressions from common params."""
    filters = []

    filter_mappings = {
        'severity': "severity eq '{}'",
        'status': "investigationStatus eq '{}'",
        'risk_level': "riskLevel eq '{}'",
        'provider': "provider eq '{}'",
        'ioc_type': "type eq '{}'",
        'endpoint_name': "endpointName eq '{}'",
        'key': "key eq '{}'",
    }

    for param, template in filter_mappings.items():
        if param in params and params[param]:
            filters.append(template.format(params.pop(param)))

    # Special case for risk_score (numeric comparison)
    if 'risk_score' in params and params['risk_score'] > 0:
        filters.append(f"latestRiskScore ge {params.pop('risk_score')}")

    # Custom filter expression
    if 'filter' in params and params['filter']:
        filters.append(params.pop('filter'))
    elif 'filter' in params:
        params.pop('filter')

    return filters


def api_request(method: str, endpoint: str, params: dict = None,
                body: dict = None, headers: dict = None, timeout: int = 30) -> dict:
    """Make API request and return response."""
    url = f"{get_base_url()}{endpoint}"
    hdrs = get_headers(headers)
    session = get_session()

    try:
        if method == 'GET':
            r = session.get(url, headers=hdrs, params=params, timeout=timeout)
        elif method == 'POST':
            r = session.post(url, headers=hdrs, params=params, json=body, timeout=timeout)
        elif method == 'PATCH':
            r = session.patch(url, headers=hdrs, json=body, timeout=timeout)
        elif method == 'DELETE':
            r = session.delete(url, headers=hdrs, json=body, timeout=timeout)
        else:
            return {'error': f'Unsupported method: {method}'}

        if r.status_code not in (200, 201, 202, 204):
            return {'error': f'HTTP {r.status_code}: {r.text[:500]}'}

        if r.status_code == 204 or not r.text:
            return {'success': True}

        return r.json()
    except Exception as e:
        return {'error': str(e)}
