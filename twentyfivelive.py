"""Lehigh 25Live room search and Express booking, using the Lehigh SSO session saved by login.py.

25Live signs in through the same Lehigh SSO as Banner and Degree Works, so there
is no separate login: `login.py` also opens 25Live, and if its cookies lapse
while the SSO session is still good, a headless browser quietly renews them.
Searching only lists rooms you may Express-book. Booking, favoriting, and
cancelling are the only writes anywhere in CourseLight, and each acts on one
room or one event you name; nothing is edited in bulk. Only your own bookings
can be cancelled.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
import logging
import re
import time
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

import httpx
from playwright.sync_api import Error as PlaywrightError

from lehigh import SESSION_PATH, _in_browser, _on_sso, _session
from moodle import MoodleError


BASE = 'https://25live.collegenet.com'
HOST = '25live.collegenet.com'
API = f'{BASE}/25live/data/lehigh/run'
APP_URL = f'{BASE}/pro/lehigh'
LOGIN_URL = f'{API}/login.shibboleth'
TIMEZONE = ZoneInfo('America/New_York')
MEETING = 392            # Event type used by Express scheduling
CONFIRMED, CANCELLED = 2, 99
CHUNK = 40               # Spaces per availability request, as the web app sends them
EVENT_ID = re.compile(r'^\d{1,12}$')

for _name in ('httpx', 'httpcore'):
    # Match moodle.py: no transport logs with URLs or response fragments.
    logging.getLogger(_name).disabled = True


class TwentyFiveLiveError(MoodleError):
    """A 25Live failure, reported in the same envelope as Moodle errors."""


def _not_signed_in():
    return TwentyFiveLiveError('not_signed_in', 'Not signed in to Lehigh. Call the login tool to sign in with Lehigh SSO.')


def _expired():
    return TwentyFiveLiveError('sign_in_expired', 'The Lehigh sign-in expired. Call the login tool to sign in again.')


def _unavailable():
    return TwentyFiveLiveError('twentyfivelive_unavailable', '25Live is unavailable right now. Try again later.')


# Session

def _is_signed_in(data) -> bool:
    """A signed-out session is offered a Shibboleth login URL instead of a user."""
    return isinstance(data, dict) and 'login_remote' not in data


def _build_client() -> httpx.Client:
    if not SESSION_PATH.exists():
        raise _not_signed_in()
    try:
        state = json.loads(SESSION_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise _not_signed_in() from None
    cookies = httpx.Cookies()
    for cookie in state.get('cookies', []):
        domain = cookie.get('domain', '').lstrip('.')
        # Session cookies such as WSSESSIONID sit on the parent collegenet.com domain.
        if domain and (HOST == domain or HOST.endswith(f'.{domain}')) and not domain.startswith('www.'):
            cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie.get('path', '/'))
    return httpx.Client(base_url=API, cookies=cookies, timeout=30, trust_env=False, follow_redirects=False,
                        headers={'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/json',
                                 'Origin': BASE, 'Referer': APP_URL, 'User-Agent': 'CourseLight'})


def _session_info(client: httpx.Client):
    """The login.json document, or None when 25Live treats the cookies as signed out."""
    try:
        response = client.get('/login.json', params={'caller': 'pro'})
        return response.json() if response.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None


def establish_session(context, interactive: bool = False) -> bool:
    """Complete 25Live's SAML sign-in in a browser context that carries the Lehigh SSO session.

    Headless, an SSO prompt means the Lehigh session itself is stale, so this
    reports failure. Interactive, it waits for the user to finish signing in.
    """
    deadline = 5 * 60 * 1000 if interactive else 20_000
    page = context.new_page()
    try:
        page.goto(LOGIN_URL)
        page.wait_for_load_state('networkidle')
    except PlaywrightError:
        pass
    waited = 0
    while waited < deadline:
        try:
            response = context.request.get(f'{API}/login.json', params={'caller': 'pro'})
            if response.ok and _is_signed_in(response.json()):
                return True
        except (PlaywrightError, ValueError):
            pass
        if not interactive and _on_sso(page.url):
            return False
        page.wait_for_timeout(500)
        waited += 500
    return False


def _renew():
    with _session() as context:  # Saves the refreshed cookies when this exits cleanly.
        if not establish_session(context):
            raise _expired()


@contextmanager
def _client():
    client = _build_client()
    try:
        info = _session_info(client)
        if not _is_signed_in(info):
            client.close()
            _in_browser(_renew)
            client = _build_client()
            info = _session_info(client)
            if not _is_signed_in(info):
                raise _expired()
        yield client
    finally:
        client.close()


def _find(node, key):
    if isinstance(node, dict):
        if key in node:
            return node[key]
        node = list(node.values())
    if isinstance(node, list):
        for item in node:
            found = _find(item, key)
            if found is not None:
                return found
    return None


def _contact_id(client: httpx.Client) -> int:
    """The signed-in user's 25Live contact ID, asked of 25Live itself."""
    data = _send(client, 'GET', '/current/contact.json', params={'caller': 'pro-ContactService.getCurrentContactSimple'})
    try:
        contact = int(_find(data, 'contact_id'))
    except (TypeError, ValueError):
        contact = 0
    if contact <= 0:
        raise TwentyFiveLiveError('contact_unknown', 'Could not tell which 25Live contact is signed in.')
    return contact


# Transport

def _send(client: httpx.Client, method: str, path: str, body=None, params=None):
    try:
        response = client.request(method, path, params=params, json=body)
    except httpx.HTTPError:
        raise _unavailable() from None
    if response.status_code in {301, 302, 303, 307, 308}:
        raise _expired()  # Redirected to sign in.
    if response.status_code in {401, 403}:
        raise TwentyFiveLiveError('twentyfivelive_forbidden', '25Live denied this request for the signed-in account.')
    if response.status_code >= 400:
        raise _unavailable()
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        raise _expired() from None  # An HTML page means the session is no longer valid.


def _checked(data):
    """Raise for 25Live's error documents without passing their raw text on."""
    error = (data or {}).get('results', {}).get('error') if isinstance(data, dict) else None
    if error:
        raise TwentyFiveLiveError('twentyfivelive_rejected', '25Live did not accept this request '
                                  f'({_clean(error.get("msg_id") or "error", 40)}).')
    return data


def _list(value) -> list:
    return [] if value is None else value if isinstance(value, list) else [value]


def _clean(text, limit: int) -> str:
    return re.sub(r'[\x00-\x1f\x7f]+', ' ', str(text or '')).strip()[:limit]


# Times

def _window(start: str, end: str) -> tuple[str, str]:
    """Validate one same-day window of Eastern wall-clock times and format it as 25Live expects."""
    try:
        first, last = datetime.fromisoformat(start), datetime.fromisoformat(end)
    except ValueError:
        raise TwentyFiveLiveError('invalid_time', 'Times must look like 2026-10-29T09:00.') from None
    if first.tzinfo or last.tzinfo:
        raise TwentyFiveLiveError('invalid_time', 'Give local Lehigh times without a UTC offset.')
    if last <= first or first.date() != last.date():
        raise TwentyFiveLiveError('invalid_time', 'A booking must end after it starts, on the same day.')
    return first.strftime('%Y-%m-%dT%H:%M:00'), last.strftime('%Y-%m-%dT%H:%M:00')


def _not_past(start: str):
    if datetime.fromisoformat(start).replace(tzinfo=TIMEZONE) < datetime.now(TIMEZONE):
        raise TwentyFiveLiveError('invalid_time', 'That time has already passed.')


# Spaces

def _bookable(client: httpx.Client, start: str, end: str) -> list[dict]:
    """Spaces this user may Express-book (direct-schedule) for the window."""
    data = _checked(_send(client, 'GET', '/search-criteria/space/locations.json', params={
        'page_size': 999, 'direct': 'T', 'min_ols': 'R', 'can_assign': 'T',
        'perm_start_dt': start, 'perm_end_dt': end, 'caller': 'pro-SearchCriteriaService.getLocations'}))
    return _list((data or {}).get('searchCriteria', {}).get('item'))


def _availability(client: httpx.Client, space_ids: list[int], start: str, end: str) -> dict[int, dict]:
    rows = {}
    for index in range(0, len(space_ids), CHUNK):
        data = _checked(_send(client, 'POST', '/space_avail.json', {'space_availability': {
            'event': {'event_id': '', 'profile': {'profile_id': ''}},
            'requirements': {'space': [{'space_id': item} for item in space_ids[index:index + CHUNK]],
                             'hide_conflicts': 'F', 'enable_override': 'F', 'allow_sharing': 'F'},
            'dates': [{'start_dt': start, 'end_dt': end}]}},
            params={'caller': 'pro-SpaceService.getSpaceDatesAvailability'}))
        for row in _list((data or {}).get('spaces', {}).get('space')):
            rows[row['space_id']] = row
    return rows


def _is_free(row: dict | None) -> bool:
    return bool(row) and row.get('has_conflicts') == 'F' and row.get('dates', {}).get('can_schedule') == 'T'


def _buildings(client: httpx.Client, space_ids: list[int]) -> dict[int, str]:
    names = {}
    for index in range(0, len(space_ids), CHUNK):
        chunk = space_ids[index:index + CHUNK]
        data = _send(client, 'POST', '/spaces.json', {'mapxml': {
            'space_id': '+'.join(str(item) for item in chunk), 'scope': 'extended', 'include': 'direct_schedule'}},
            params={'request_method': 'get', 'caller': 'pro-SpaceService.getSpacesIncludes'})
        for row in _list((data or {}).get('spaces', {}).get('space')):
            names[row['space_id']] = _clean(row.get('building_name'), 120)
    return names


def search_rooms(start: str, end: str, query: str | None, min_capacity: int, include_busy: bool,
                 max_results: int) -> dict:
    start, end = _window(start, end)
    with _client() as client:
        items = _bookable(client, start, end)
        if query:
            needle = query.casefold()
            items = [item for item in items if needle in item['itemName'].casefold()
                     or needle in item['itemDesc'].casefold()]
        rows = _availability(client, [item['itemId'] for item in items], start, end)
        matches = []
        for item in items:
            row = rows.get(item['itemId'])
            capacity = (row or {}).get('max_capacity') or 0
            free = _is_free(row)
            if capacity < min_capacity or not (free or include_busy):
                continue
            matches.append((item, capacity, free))
        shown = matches[:max_results]
        buildings = _buildings(client, [item['itemId'] for item, _, _ in shown]) if shown else {}
    return {
        'start': start, 'end': end, 'timezone': 'America/New_York',
        'rooms': [{'space_id': item['itemId'], 'name': _clean(item['itemName'], 40),
                   'description': _clean(item['itemDesc'].split(' -- ')[0], 120),
                   'building': buildings.get(item['itemId']) or None,
                   'capacity': capacity, 'available': free} for item, capacity, free in shown],
        'total_matching': len(matches), 'url': APP_URL,
        'note': ('Only rooms you may Express-book are listed. Availability is a snapshot: booking checks again. '
                 'A capacity of 0 means 25Live lists none.')}


# Events

def _my_event(client: httpx.Client, event_id: str, include: str = 'customers+reservations'):
    data = _send(client, 'POST', '/events.json', {'mapxml': {
        'event_id': event_id, 'scope': 'extended', 'include': include}},
        params={'request_method': 'get', 'caller': 'pro-EventService.getEventsInclude'})
    events = _list((_checked(data) or {}).get('events', {}).get('event'))
    if not events:
        raise TwentyFiveLiveError('event_not_found', 'No 25Live event with that ID is visible to the signed-in account.')
    return events[0]


def _mine(event: dict, contact: int) -> bool:
    return any(_find(role, 'contact_id') == contact for role in _list(event.get('role')))


def _summary(event: dict) -> dict:
    profile = _list(event.get('profile'))
    rooms = []
    for item in profile:
        for reservation in _list(item.get('reservation')):
            for space in _list(reservation.get('space_reservation')):
                rooms.append(space.get('space', {}).get('space_name') or space.get('space_id'))
    return {'event_id': event.get('event_id'), 'name': _clean(event.get('event_name'), 100),
            'status': _clean(event.get('state_name'), 30) or None, 'locator': event.get('event_locator'),
            'rooms': [_clean(room, 40) for room in rooms] or None, 'url': APP_URL}


def book_room(space_id: int, start: str, end: str, event_name: str, confirm: bool, favorite: bool) -> dict:
    start, end = _window(start, end)
    _not_past(start)
    name = _clean(event_name, 100)
    if not name:
        raise TwentyFiveLiveError('invalid_name', 'Give the booking a name.')
    with _client() as client:
        listed = next((item for item in _bookable(client, start, end) if item['itemId'] == space_id), None)
        if listed is None:
            raise TwentyFiveLiveError('room_not_bookable', 'That room is not one you can Express-book. Use search_rooms.')
        row = _availability(client, [space_id], start, end).get(space_id)
        room = {'space_id': space_id, 'name': _clean(listed['itemName'], 40),
                'description': _clean(listed['itemDesc'].split(' -- ')[0], 120),
                'start': start, 'end': end, 'timezone': 'America/New_York', 'event_name': name}
        if not _is_free(row):
            raise TwentyFiveLiveError('room_unavailable', f'{room["name"]} is not free for that time. Use search_rooms.')
        if not confirm:
            return {'booked': False, 'preview': room,
                    'message': 'Nothing was booked. Show the user this room and time, and call book_room again with '
                               'confirm=true only after they approve it.'}
        contact = _contact_id(client)
        data = _send(client, 'POST', '/events.json', {'events': {'event': {
            'status': 'new', '_source': 'direct_sched_event_xml.html', 'event_id': '', 'parent_id': 0,
            'event_name': name, 'alien_uid': f'Express_Pro{int(time.time() * 1000)}', 'event_type_id': MEETING,
            'state': CONFIRMED, 'primary': 'T',
            'profile': {'status': 'new', 'rec_type_id': 0, 'init_start_dt': start, 'init_end_dt': end,
                        'reservation': [{'status': 'new', 'reservation_id': '', 'reservation_state': 1,
                                         'reservation_start_dt': start, 'reservation_end_dt': end,
                                         'space_reservation': [{'status': 'new', 'space_id': space_id}]}]},
            'role': [{'status': 'new', 'role_id': -2, 'contact': {'status': 'new', 'contact_id': contact}},
                     {'status': 'new', 'role_id': -1, 'contact': {'status': 'new', 'contact_id': contact}}]}}},
            params={'return_doc': 'T', 'caller': 'pro-EventService.postEvent'})
        created = _list((_checked(data) or {}).get('events', {}).get('event'))
        if not created:
            raise TwentyFiveLiveError('booking_not_confirmed', '25Live did not return the new booking. '
                                      'Check 25Live before trying again.')
        # Read the booking back; only report it as made once 25Live shows it.
        event = _my_event(client, str(created[0]['event_id']))
        summary = _summary(event)
        booked = event.get('state') == CONFIRMED and bool(summary['rooms'])
        favorited = False
        if booked and favorite:
            try:
                _favorite(client, str(event['event_id']))
                favorited = True
            except TwentyFiveLiveError:
                pass
    return {'booked': booked, 'booking': summary, 'start': start, 'end': end, 'timezone': 'America/New_York',
            'favorited': favorited,
            'message': None if booked else 'The event exists but 25Live did not show it as confirmed with the room. '
                                           'Check it in 25Live before relying on it.'}


def _names(cell) -> list[str]:
    """Names inside a list cell: a plain string, an item, or a list of subjects."""
    if isinstance(cell, dict):
        items = _list(cell.get('subject')) or ([cell] if cell.get('itemName') else [])
        return [_clean(item.get('itemName'), 80) for item in items]
    return [_clean(cell, 80)] if cell else []


def list_events(from_date: str | None, include_cancelled: bool, page: int, page_size: int) -> dict:
    """The user's own events (as requestor or scheduler) ending on or after a date, soonest first."""
    after = from_date or datetime.now(TIMEZONE).strftime('%Y-%m-%d')
    with _client() as client:
        data = _checked(_send(client, 'GET', '/list/listdata.json', params={
            'compsubject': 'event', 'node_type': 'E', 'end_after': f'{after}T00:00:00', 'sort': 'start_date',
            'order': 'asc', 'page': page, 'page_size': page_size, 'obj_cache_accl': 0, 'role_id': -1,
            'caller': 'pro-ListService.getData'}))
    rows = _list((data or {}).get('rows'))
    columns = [column.get('prefname') or column.get('name') for column in _list((data or {}).get('cols'))]
    events, hidden = [], 0
    for row in rows:
        cells = dict(zip(columns, _list(row.get('row'))))
        state = _clean(cells.get('state_name'), 30)
        if state == 'Cancelled' and not include_cancelled:
            hidden += 1
            continue
        favorite = cells.get('IsFav')
        events.append({
            'event_id': row.get('contextId'), 'name': next(iter(_names(cells.get('event_name'))), None),
            'title': _clean(cells.get('event_title'), 100) or None, 'locator': _clean(cells.get('event_locator'), 30) or None,
            'status': state or None, 'start': _clean(cells.get('start_date'), 23).replace(' ', 'T')[:19] or None,
            'rooms': _names(cells.get('locations')) or None,
            'organizations': _names(cells.get('organization')) or None,
            'type': _clean(cells.get('event_type_name'), 40) or None,
            'role': _clean(cells.get('role'), 40) or None,
            'favorite': bool(favorite.get('isFav')) if isinstance(favorite, dict) else None,
            'repeats': _clean(cells.get('meeting_pattern'), 20) or None})
    head = rows[0] if rows else {}
    return {'events': events, 'page': page, 'pages': head.get('pages', 1 if rows else 0),
            'total': head.get('count', len(rows)), 'from_date': after, 'cancelled_hidden': hidden or None,
            'timezone': 'America/New_York', 'url': APP_URL,
            'note': ('Events where you are the requestor or scheduler, soonest first. Start is the first '
                     'occurrence in Lehigh local time; end times are not listed. Counts include cancelled events. '
                     'Follow pages with the same from_date until page reaches pages.')}


def _favorite(client: httpx.Client, event_id: str):
    _send(client, 'PUT', '/favorites.json', params={
        'object_type': 1, 'object_id': event_id, 'caller': 'pro-FavoriteService.add'})


def favorite_booking(event_id: str) -> dict:
    if not EVENT_ID.match(event_id):
        raise TwentyFiveLiveError('invalid_event', 'Give the numeric event ID returned by book_room.')
    with _client() as client:
        summary = _summary(_my_event(client, event_id))
        _favorite(client, event_id)
    return {'favorited': True, 'booking': summary}


def cancel_booking(event_id: str, confirm: bool) -> dict:
    if not EVENT_ID.match(event_id):
        raise TwentyFiveLiveError('invalid_event', 'Give the numeric event ID returned by book_room.')
    with _client() as client:
        event = _my_event(client, event_id, include=(
            'customers+reservations+attributes+workflow+workflow_history+text+requirements+categories+relationships+draft'))
        summary = _summary(event)
        if not _mine(event, _contact_id(client)):
            raise TwentyFiveLiveError('not_your_booking', 'Only bookings you requested can be cancelled here.')
        if event.get('state') == CANCELLED:
            return {'cancelled': True, 'already_cancelled': True, 'booking': summary}
        if not confirm:
            return {'cancelled': False, 'preview': summary,
                    'message': 'Nothing was cancelled. Show the user this booking, and call cancel_room_booking again '
                               'with confirm=true only after they approve it.'}
        _checked(_send(client, 'PUT', '/rose/event.json', _cancel_document(event),
                       params={'event_id': event_id, 'caller': 'pro-EventService.putEvent'}))
        after = _my_event(client, event_id)  # Read back; report cancelled only once 25Live shows it.
        cancelled = after.get('state') == CANCELLED
    return {'cancelled': cancelled, 'booking': _summary(after),
            'message': None if cancelled else '25Live did not show the event as cancelled. Check it in 25Live.'}


# The fields the 25Live web app sends back when it cancels an event.
CANCEL_KEYS = ('end_date', 'registration_url', 'version_number', 'event_type_id', 'cabinet_id', 'cabinet_name',
               'node_type', 'crc', 'state_name', 'id', 'event_priority', 'node_type_name', 'start_date',
               'last_mod_dt', 'profile', 'event_title', 'event_locator', 'event_type_name', 'event_id', 'parent_id',
               'creation_dt', 'alien_uid', 'last_mod_user', 'event_name', 'favorite', 'custom_attribute')
KEEP_OFFSET = {'last_mod_dt', 'creation_dt'}
LOCAL_DATETIME = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d')


def _local(node, key=''):
    """25Live returns datetimes with offsets but expects local ones back."""
    if isinstance(node, dict):
        return {name: _local(value, name) for name, value in node.items()}
    if isinstance(node, list):
        return [_local(value, key) for value in node]
    if isinstance(node, str) and key not in KEEP_OFFSET and LOCAL_DATETIME.fullmatch(node):
        return node[:19]
    if isinstance(node, str) and key in {'start_date', 'end_date'} and re.fullmatch(r'\d{4}-\d\d-\d\d', node):
        return f'{node}T00:00:00'
    return node


def _cancel_document(event: dict) -> dict:
    document = {key: event[key] for key in CANCEL_KEYS if key in event}
    document.update(state=CANCELLED, status='mod',
                    custom_attribute=_list(document.get('custom_attribute')))
    profiles = _list(document.get('profile'))
    for profile in profiles:
        profile['status'] = 'mod'
        profile['reservation'] = _list(profile.get('reservation'))
        for reservation in profile['reservation']:
            reservation.update(reservation_state=CANCELLED, status='mod',
                               space_reservation=_list(reservation.get('space_reservation')))
    document['profile'] = profiles
    return {'events': {'event': _local(document)}}
