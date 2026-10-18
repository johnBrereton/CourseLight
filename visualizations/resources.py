"""Package a built React view as a self-contained MCP HTML resource."""
from pathlib import Path

UI_ROOT = Path(__file__).resolve().parent.parent / 'ui'


def component_html(view: str) -> str:
    source = UI_ROOT / 'views' / view
    bundle = UI_ROOT / 'dist' / view
    html = (source / 'index.html').read_text(encoding='utf-8')
    html = html.replace('<link rel="stylesheet" href="bundle.css">',
                        '<style>' + (bundle / 'bundle.css').read_text(encoding='utf-8') + '</style>')
    for script, path in (('../../shared/bridge.js', UI_ROOT / 'shared' / 'bridge.js'),
                         ('bundle.js', bundle / 'bundle.js')):
        html = html.replace(f'<script src="{script}" defer></script>',
                            '<script>' + path.read_text(encoding='utf-8') + '</script>')
    return html
