"""Moodle transport restricted to the reads CourseLight needs."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import time
from urllib.parse import unquote_plus, urlsplit, urlunsplit

from dotenv import load_dotenv
import httpx


ENV_PATH = Path(__file__).resolve().parent / '.env'
# Credentials already in the environment take precedence and are never reloaded from .env.
EXTERNAL_KEYS = frozenset(key for key in ('MOODLE_URL', 'MOODLE_TOKEN') if os.environ.get(key))
load_dotenv(ENV_PATH, override=False, interpolate=False)

# This is the complete upstream API surface. There are no assessment, upload,
# submission, or generic API tools, even when a token permits those operations.
READ_FUNCTIONS = frozenset({
    'core_webservice_get_site_info',
    'core_enrol_get_users_courses',
    'core_course_get_contents',
    'mod_assign_get_assignments',
    'mod_assign_get_submission_status',
    'gradereport_user_get_grade_items',
    'core_calendar_get_action_events_by_timesort',
    'core_calendar_get_action_events_by_course',
    'mod_page_get_pages_by_courses',
})
SECRET_KEYS = frozenset({
    'token', 'wstoken', 'privatetoken', 'password', 'access_token', 'refresh_token',
    'sesskey', 'debug', 'debuginfo', 'stacktrace',
})
MAX_RESPONSE_BYTES = 20 * 1024 * 1024


class MoodleError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def flatten(value, prefix=''):
    """Encode Moodle's nested REST parameters without accepting raw form fields."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from flatten(child, f'{prefix}[{key}]' if prefix else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from flatten(child, f'{prefix}[{index}]')
    elif value is not None:
        yield prefix, str(int(value)) if isinstance(value, bool) else str(value)


class Moodle:
    def __init__(self):
        # Avoid transport logs containing credentials or response fragments.
        for name in ('httpx', 'httpcore'):
            logger = logging.getLogger(name)
            logger.disabled = True
            logger.propagate = False
        self.token = os.getenv('MOODLE_TOKEN', '').strip()
        self.url = os.getenv('MOODLE_URL', '').strip().rstrip('/')
        if not self.token or not self.url:
            raise MoodleError('not_signed_in', 'Not signed in to CourseSite. Call the login tool to sign in with Lehigh SSO, '
                              'or set MOODLE_URL and MOODLE_TOKEN in .env.')
        try:
            parts = urlsplit(self.url)
            valid = (parts.scheme == 'https' and parts.hostname
                     and not parts.username and not parts.password
                     and not parts.query and not parts.fragment)
            parts.port  # Reject malformed port numbers before making a request.
        except ValueError:
            valid = False
        if not valid:
            raise MoodleError('configuration', 'MOODLE_URL must be an HTTPS base URL without credentials, query parameters, or a fragment.')
        self.http = httpx.Client(
            headers={'User-Agent': 'CourseLight/0.1', 'Accept': 'application/json'},
            timeout=30, follow_redirects=False, trust_env=False,
        )
        self._identity = None

    def close(self):
        self.http.close()

    def clean(self, value):
        """Strip credential fields, exact token occurrences, and credential queries."""
        if isinstance(value, dict):
            return {self.clean(str(key)): self.clean(child)
                    for key, child in value.items() if str(key).lower() not in SECRET_KEYS}
        if isinstance(value, list):
            return [self.clean(child) for child in value]
        if isinstance(value, str):
            value = value.replace(self.token, '[REDACTED]')
            value = re.sub(
                r'(?i)(?<![\w-])((?:wstoken|privatetoken|access_token|refresh_token|token|password|sesskey)=)[^&\s"<>]+',
                r'\1[REDACTED]', value,
            )
            if value.startswith(('https://', 'http://')):
                try:
                    parts = urlsplit(value)
                    query = '&'.join(field for field in parts.query.split('&')
                                     if unquote_plus(field.partition('=')[0]).lower() not in SECRET_KEYS)
                    # Userinfo and fragments are unnecessary for source citations.
                    value = urlunsplit((parts.scheme, parts.netloc.rsplit('@', 1)[-1], parts.path, query, ''))
                except ValueError:
                    return '[invalid URL]'
        return value

    def call(self, function: str, **params):
        if function not in READ_FUNCTIONS:
            raise MoodleError('unsupported_function', 'This operation is outside CourseLight\'s read-only API.')
        if function != 'core_webservice_get_site_info':
            advertised = {item['name'] for item in self.identity().get('functions', [])}
            if function not in advertised:
                raise MoodleError('function_unavailable', f'The configured Moodle service does not provide {function}.')
        data = dict(flatten(params))
        data.update(wstoken=self.token, wsfunction=function, moodlewsrestformat='json')
        # Moodle uses POST even for reads. Only the fixed read allowlist above
        # reaches this endpoint, and redirects never receive the token.
        for attempt in range(3):
            try:
                with self.http.stream('POST', self.url + '/webservice/rest/server.php', data=data) as response:
                    if response.status_code in {429, 502, 503, 504} and attempt < 2:
                        time.sleep(0.5 * 2 ** attempt)
                        continue
                    if response.status_code != 200:
                        raise MoodleError('http_error', f'Moodle returned HTTP {response.status_code}.')
                    payload = bytearray()
                    for chunk in response.iter_bytes(chunk_size=65536):
                        if len(payload) + len(chunk) > MAX_RESPONSE_BYTES:
                            raise MoodleError('response_too_large', 'Moodle returned too much data. Select a narrower course section where supported.')
                        payload.extend(chunk)
            except httpx.HTTPError:
                if attempt < 2:
                    time.sleep(0.5 * 2 ** attempt)
                    continue
                raise MoodleError('network_error', 'Could not reach Moodle. Check the site URL and your network connection.') from None
            try:
                result = json.loads(payload)
            except (ValueError, UnicodeError):
                raise MoodleError('invalid_response', 'Moodle did not return valid JSON.') from None
            if isinstance(result, dict) and result.get('errorcode') == 'invalidtoken':
                raise MoodleError('sign_in_expired', 'The CourseSite sign-in expired or was reset. Call the login tool to sign in again.')
            if isinstance(result, dict) and any(key in result for key in ('exception', 'errorcode', 'error')):
                # Do not expose Moodle's raw messages, debug traces, or tokens.
                raise MoodleError('moodle_error', 'Moodle rejected the request. Check token validity, web-service permissions, and course availability.')
            if not isinstance(result, (dict, list)):
                raise MoodleError('invalid_response', 'Moodle returned an unexpected response shape.')
            return result

    def identity(self):
        if self._identity is None:
            info = self.call('core_webservice_get_site_info')
            if not isinstance(info, dict) or not isinstance(info.get('userid'), int) or info['userid'] <= 0:
                raise MoodleError('invalid_response', 'Moodle did not identify the connected user.')
            self._identity = info
        return self._identity
