"""Only a browser-scoped MapKit JS token goes to the component, never a signing key."""
import os
from urllib.parse import urlsplit

from .models import MapConfig


def map_config():
    token = os.getenv('APPLE_MAPS_TOKEN', '').strip()
    status = 'missing_token'
    if token:
        status = 'invalid_token' if len(token) > 8192 or any(c.isspace() for c in token) or 'PRIVATE KEY' in token else 'ready'
    metadata = {'courselight/mapkit': {'token': token}} if status == 'ready' else {}
    return MapConfig(status=status), metadata


def resource_meta(description):
    ui = {'prefersBorder': False, 'csp': {
        'connectDomains': ['https://*.apple-mapkit.com'],
        'resourceDomains': ['https://*.apple-mapkit.com'],
        'frameDomains': [],
    }}
    origin = os.getenv('APPLE_MAPS_WIDGET_DOMAIN', '').strip()
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError('APPLE_MAPS_WIDGET_DOMAIN must be an HTTPS origin, without a path or credentials.')
        ui['domain'] = origin.rstrip('/')
    return {'ui': ui, 'openai/ui': {'availableDisplayModes': ['inline']},
            'openai/widgetDescription': description}
