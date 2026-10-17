#!/usr/bin/env python3
"""Sign in with Lehigh SSO once for CourseSite, Banner, and Degree Works.

The CourseSite token comes from Moodle's mobile-app login
(admin/tool/mobile/launch.php), the same flow the official Moodle app uses on
SSO sites, and is saved to .env. The same browser then opens Degree Works and
Banner, and the resulting Lehigh session is saved to
~/.lehigh-mcp/storage_state.json for those tools. You sign in yourself in a
real browser and approve Duo; the script never sees your password. A saved
Lehigh session is tried first so you may not need to sign in again.

    .venv/bin/python login.py            # Windows: .venv\\Scripts\\python.exe login.py
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import secrets
import sys
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError, sync_playwright

from lehigh import BANNER, DEGREEWORKS, SESSION_PATH as LEHIGH_SESSION, SSO_HOST


ENV_PATH = Path(__file__).resolve().parent / '.env'
DEFAULT_URL = 'https://coursesite.lehigh.edu'
SCHEME = 'moodlemobile'
LOGIN_TIMEOUT_MS = 5 * 60 * 1000
# Pages that establish each system's session after SSO, and the URL each lands on.
LEHIGH_APPS = (
    (f'{DEGREEWORKS}/worksheets/WEB31', DEGREEWORKS),
    (f'{BANNER}/registration/registration', BANNER),
)


def read_env() -> dict[str, str]:
    values = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
            key, sep, value = line.partition('=')
            if sep and not line.lstrip().startswith('#'):
                values[key.strip()] = value.strip()
    return values


def write_env(updates: dict[str, str]):
    """Set keys in .env, keeping comments and any other settings."""
    lines = ENV_PATH.read_text(encoding='utf-8').splitlines() if ENV_PATH.exists() else []
    remaining = dict(updates)
    for index, line in enumerate(lines):
        key = line.partition('=')[0].strip()
        if key in remaining and not line.lstrip().startswith('#'):
            lines[index] = f'{key}={remaining.pop(key)}'
    lines += [f'{key}={value}' for key, value in remaining.items()]
    ENV_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def parse_token(redirect: str, site_url: str, passport: str) -> str:
    """Decode moodlemobile://token=BASE64(signature:::token[:::privatetoken])."""
    encoded = redirect.split('token=', 1)[1].split('&', 1)[0].rstrip('/')
    parts = base64.b64decode(encoded + '=' * (-len(encoded) % 4)).decode().split(':::')
    if len(parts) < 2:
        raise SystemExit('CourseSite returned an unexpected login response.')
    # Moodle signs the response with md5(wwwroot + passport); check it matches.
    expected = hashlib.md5((site_url + passport).encode()).hexdigest()
    if parts[0] != expected:
        raise SystemExit('CourseSite login response failed its signature check; not saving it.')
    # parts[2], the private token, is only for the app's auto-login and is discarded.
    return parts[1]


def capture_token(site_url: str, headless: bool) -> str | None:
    passport = secrets.token_hex(16)
    launch = f'{site_url}/admin/tool/mobile/launch.php?' + urlencode(
        {'service': 'moodle_mobile_app', 'passport': passport, 'urlscheme': SCHEME})
    found: list[str] = []

    def check(url: str | None):
        if url and url.startswith(f'{SCHEME}://') and 'token=' in url and not found:
            found.append(url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            storage_state=str(LEHIGH_SESSION) if LEHIGH_SESSION.exists() else None)
        # The token arrives as a redirect to the app's URL scheme, which the
        # browser can't open; catch it from the redirect or the attempted request.
        context.on('request', lambda request: check(request.url))
        context.on('response', lambda response: check(response.headers.get('location')))
        page = context.new_page()
        try:
            page.goto(launch)
        except PlaywrightError:
            pass  # Navigating to moodlemobile:// aborts the page load.
        deadline = LOGIN_TIMEOUT_MS if not headless else 20_000
        waited = 0
        while not found and waited < deadline:
            if headless and SSO_HOST in page.url and waited > 5000:
                break  # Saved session expired: the SSO login form is showing.
            page.wait_for_timeout(250)
            waited += 250
        ready = bool(found) and open_lehigh_apps(context, headless)
        if ready:
            LEHIGH_SESSION.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(LEHIGH_SESSION))
        browser.close()
    return parse_token(found[0], site_url, passport) if ready else None


def open_lehigh_apps(context, headless: bool) -> bool:
    """Visit Degree Works and Banner so their sessions are saved with the SSO one.

    Headless, any SSO prompt means the saved session is stale, so report failure
    and let the visible browser handle it. In the visible browser, a page that
    doesn't load (Degree Works needs the VPN off campus) is skipped rather than
    failing the CourseSite sign-in.
    """
    page = context.new_page()
    for url, landed in LEHIGH_APPS:
        try:
            page.goto(url)
            page.wait_for_url(lambda current: current.startswith(landed),
                              timeout=20_000 if headless else LOGIN_TIMEOUT_MS)
            page.wait_for_load_state('networkidle')
        except PlaywrightError:
            if headless:
                return False
            print(f'Could not open {landed}; those tools may ask you to sign in again later.')
    return True


def main():
    site_url = (read_env().get('MOODLE_URL') or '').rstrip('/')
    if not site_url or 'example.edu' in site_url:
        site_url = DEFAULT_URL
    token = None
    if LEHIGH_SESSION.exists():
        print('Trying your saved Lehigh session...')
        token = capture_token(site_url, headless=True)
    if not token:
        print('A browser window will open. Sign in to Lehigh and approve Duo.')
        token = capture_token(site_url, headless=False)
    if not token:
        sys.exit('No token received. Make sure you finished signing in, then try again.')
    write_env({'MOODLE_URL': site_url, 'MOODLE_TOKEN': token})
    print(f'Saved MOODLE_URL and MOODLE_TOKEN to {ENV_PATH} and the Lehigh session to {LEHIGH_SESSION}.')


if __name__ == '__main__':
    main()
