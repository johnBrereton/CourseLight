"""Lehigh Banner and Degree Works reads, using the Lehigh SSO session saved by login.py.

Banner class search is public. Your registration and Degree Works audit need
the saved session (~/.lehigh-mcp/storage_state.json), which a headless browser
reuses so SAML sign-in to each system completes without prompting. Everything
here is read-only: there is no registration, add/drop, or planner write.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime
import html
import json
import logging
import os
from pathlib import Path
import re

import httpx
from playwright.sync_api import Error as PlaywrightError, sync_playwright

from moodle import MoodleError


BANNER = 'https://reg-prod.ec.lehigh.edu/StudentRegistrationSsb/ssb'
DEGREEWORKS = 'https://dw-prod.ec.lehigh.edu/responsiveDashboard'
SSO_HOST = 'sso.cc.lehigh.edu'
SESSION_PATH = Path(os.getenv('LEHIGH_MCP_HOME', Path.home() / '.lehigh-mcp')) / 'storage_state.json'
DAYS = (('monday', 'M'), ('tuesday', 'T'), ('wednesday', 'W'), ('thursday', 'R'),
        ('friday', 'F'), ('saturday', 'S'), ('sunday', 'U'))

for _name in ('httpx', 'httpcore'):
    # Match moodle.py: no transport logs with URLs or response fragments.
    logging.getLogger(_name).disabled = True

# Playwright's sync API cannot run on the MCP server's event loop thread.
_browser_thread = ThreadPoolExecutor(max_workers=1, thread_name_prefix='lehigh-browser')


class LehighError(MoodleError):
    """A Banner or Degree Works failure, reported in the same envelope as Moodle errors."""


def _not_signed_in():
    return LehighError('not_signed_in', 'Not signed in to Lehigh. Call the login tool to sign in with Lehigh SSO.')


def _expired():
    return LehighError('sign_in_expired', 'The Lehigh sign-in expired. Call the login tool to sign in again.')


def _on_sso(url: str) -> bool:
    return SSO_HOST in url or '/saml/login' in url


@contextmanager
def _session():
    """A headless browser context carrying the saved Lehigh cookies."""
    if not SESSION_PATH.exists():
        raise _not_signed_in()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(storage_state=str(SESSION_PATH))
            yield context
            context.storage_state(path=str(SESSION_PATH))  # Keep refreshed cookies.
        finally:
            browser.close()


def _open(context, url: str):
    page = context.new_page()
    page.goto(url)
    page.wait_for_load_state('networkidle')
    if _on_sso(page.url):
        raise _expired()
    return page


def _get_json(context, url: str, params: dict | None = None):
    response = context.request.get(url, params=params)
    text = response.text()
    if _on_sso(response.url) or text.lstrip().startswith('<'):
        raise _expired()
    return json.loads(text)


def _in_browser(function, *args):
    return _browser_thread.submit(function, *args).result()


# Banner

def _time(value: str | None) -> str | None:
    if not value:
        return None
    hour, minute = int(value[:2]), value[2:]
    return f"{(hour - 1) % 12 + 1}:{minute}{'am' if hour < 12 else 'pm'}"


def _meetings(meeting_times: list[dict]) -> list[dict]:
    out = []
    for meeting in meeting_times:
        start, end = _time(meeting.get('beginTime')), _time(meeting.get('endTime'))
        out.append({
            'days': ''.join(code for key, code in DAYS if meeting.get(key)) or 'TBA',
            'time': f'{start}-{end}' if start and end else 'TBA',
            'location': ' '.join(filter(None, [meeting.get('buildingDescription'), meeting.get('room')])) or 'TBA',
            'dates': f"{meeting.get('startDate')} to {meeting.get('endDate')}",
            'type': meeting.get('meetingTypeDescription'),
        })
    return out


def _section(section: dict) -> dict:
    credits = section.get('creditHours')
    return {
        'crn': section.get('courseReferenceNumber'),
        'course': f"{section.get('subject')} {section.get('courseNumber')}",
        'section': section.get('sequenceNumber'),
        'title': html.unescape(section.get('courseTitle') or ''),
        'type': section.get('scheduleTypeDescription'),
        'credits': credits if credits is not None else section.get('creditHourLow'),
        'instructors': [faculty.get('displayName') for faculty in section.get('faculty') or []],
        'meetings': _meetings([item.get('meetingTime') or {} for item in section.get('meetingsFaculty') or []]),
        'seats_available': section.get('seatsAvailable'),
        'enrollment': f"{section.get('enrollment')}/{section.get('maximumEnrollment')}",
        'waitlist': f"{section.get('waitCount')}/{section.get('waitCapacity')}",
        'open': section.get('openSection'),
        'campus': html.unescape(section.get('campusDescription') or ''),
    }


def _banner(method: str, path: str, client: httpx.Client | None = None, **kwargs):
    try:
        if client is not None:
            response = client.request(method, BANNER + path, **kwargs)
        else:
            with httpx.Client(timeout=30, trust_env=False) as fresh:
                response = fresh.request(method, BANNER + path, **kwargs)
        response.raise_for_status()
        return response
    except httpx.HTTPError:
        raise LehighError('network_error', 'Could not reach Lehigh Banner. Check your network connection.') from None


def get_terms(max_terms: int) -> list[dict]:
    return _banner('GET', '/classSearch/getTerms', params={'searchTerm': '', 'offset': 1, 'max': max_terms}).json()


@contextmanager
def _search_session(term: str):
    """An HTTP client with `term` selected; Banner ties searches to a term chosen in the session."""
    with httpx.Client(timeout=30, follow_redirects=True, trust_env=False) as client:
        _banner('GET', '/term/termSelection', client, params={'mode': 'search'})
        _banner('POST', '/term/search', client, params={'mode': 'search'},
                data={'term': term, 'studyPath': '', 'studyPathText': '', 'startDatepicker': '', 'endDatepicker': ''})
        yield client


def _search(client: httpx.Client, term: str, filters: dict, offset: int, size: int) -> dict:
    # Without a reset, Banner can return the previous search's results in the same session.
    _banner('POST', '/classSearch/resetDataForm', client)
    params = {'txt_term': term, 'pageOffset': offset, 'pageMaxSize': size,
              'sortColumn': 'subjectDescription', 'sortDirection': 'asc', **filters}
    return _banner('GET', '/searchResults/searchResults', client, params=params).json()


def search_classes(term: str, subject: str | None, course_number: str | None, course_number_from: str | None,
                   course_number_to: str | None, attribute: str | None, keyword: str | None,
                   open_only: bool, offset: int, max_results: int) -> dict:
    filters = {}
    if subject:
        filters['txt_subject'] = subject.upper()
    if course_number:
        filters['txt_courseNumber'] = course_number
    if course_number_from or course_number_to:
        filters['txt_course_number_range'] = course_number_from or '000'
        filters['txt_course_number_range_to'] = course_number_to or '999'
    if attribute:
        filters['txt_attribute'] = attribute.upper()
    if keyword:
        filters['txt_keywordlike'] = keyword
    if open_only:
        filters['chk_open_only'] = 'true'
    with _search_session(term) as client:
        body = _search(client, term, filters, offset, max_results)
    sections = [_section(item) for item in body.get('data') or []]
    total = body.get('totalCount', len(sections))
    end = offset + len(sections)
    return {'total_matches': total, 'offset': offset, 'returned': len(sections),
            'next_offset': end if sections and end < total else None, 'sections': sections}


def get_course_description(term: str, crn: str) -> str:
    fragment = _banner('POST', '/searchResults/getCourseDescription',
                       data={'term': term, 'courseReferenceNumber': crn}).text
    return html.unescape(re.sub(r'<[^>]+>', ' ', fragment)).strip()


# Schedule building

MAX_SCHEDULES_EXAMINED = 20_000
MAX_PACKAGES_PER_COURSE = 60


def _minutes(value: str) -> int:
    return int(value[:2]) * 60 + int(value[2:])


def _date(value: str | None) -> date | None:
    try:
        return datetime.strptime(value or '', '%m/%d/%Y').date()
    except ValueError:
        return None


def _slots(section: dict) -> list[tuple]:
    """(day, start, end, first date, last date) for each timed weekly meeting; TBA and online meetings have none."""
    out = []
    for item in section.get('meetingsFaculty') or []:
        meeting = item.get('meetingTime') or {}
        if not (meeting.get('beginTime') and meeting.get('endTime')):
            continue
        start, end = _minutes(meeting['beginTime']), _minutes(meeting['endTime'])
        first, last = _date(meeting.get('startDate')), _date(meeting.get('endDate'))
        out += [(code, start, end, first, last) for key, code in DAYS if meeting.get(key)]
    return out


def _clash(a: list[tuple], b: list[tuple]) -> bool:
    for day, start, end, first, last in a:
        for other_day, other_start, other_end, other_first, other_last in b:
            dates_overlap = not (first and last and other_first and other_last) or (first <= other_last and other_first <= last)
            if day == other_day and start < other_end and other_start < end and dates_overlap:
                return True
    return False


def _credits(section: dict) -> float:
    credits = section.get('creditHours')
    return float(credits if credits is not None else section.get('creditHourLow') or 0)


def _fits(section: dict, open_only: bool, earliest: int | None, latest: int | None, days_off: str) -> bool:
    if open_only and (section.get('seatsAvailable') or 0) <= 0:
        return False
    for day, start, end, _, _ in _slots(section):
        if day in days_off or (earliest is not None and start < earliest) or (latest is not None and end > latest):
            return False
    return True


def _packages(sections: list[dict]) -> list[list[dict]]:
    """Every registrable set for one course: a lone section, or a lecture with its linked lab/recitation.

    Banner link identifiers are two characters: a section with "3C" is in group 3
    and needs a section from group C; the "C3" labs point back to group 3.
    """
    def linked(section):
        link = section.get('linkIdentifier') or ''
        return bool(section.get('isSectionLinked')) and len(link) == 2

    groups: dict[str, list[dict]] = {}
    for section in sections:
        if linked(section):
            groups.setdefault(section['linkIdentifier'][0], []).append(section)
    packages = [[section] for section in sections if not linked(section)]
    starts = [section for members in groups.values() for section in members
              if section.get('scheduleTypeDescription') == 'Lecture'] or next(iter(groups.values()), [])

    def extend(chosen):
        needed = chosen[-1]['linkIdentifier'][1]
        if needed in {section['linkIdentifier'][0] for section in chosen}:
            yield chosen
            return
        for section in groups.get(needed, []):
            if not any(_clash(_slots(section), _slots(other)) for other in chosen):
                yield from extend(chosen + [section])

    for start in starts:
        for package in extend([start]):
            packages.append(package)
            if len(packages) >= MAX_PACKAGES_PER_COURSE:
                return packages
    return packages


def _course_sections(client: httpx.Client, term: str, course: str) -> list[dict]:
    subject, number = course.split()
    sections, offset = [], 0
    while True:
        body = _search(client, term, {'txt_subject': subject, 'txt_courseNumber': number}, offset, 100)
        page = body.get('data') or []
        sections += page
        offset += len(page)
        if not page or offset >= body.get('totalCount', 0) or offset >= 500:
            return sections


def _clock(minutes: int) -> str:
    hour, minute = divmod(minutes, 60)
    return f"{(hour - 1) % 12 + 1}:{minute:02d}{'am' if hour < 12 else 'pm'}"


def _rank(slots: list[tuple]) -> tuple[int, int, int]:
    """Sort key: fewest days on campus, then least time between classes, then latest first class."""
    by_day: dict[str, list[tuple[int, int]]] = {}
    for day, start, end, _, _ in slots:
        by_day.setdefault(day, []).append((start, end))
    gaps = 0
    for meetings in by_day.values():
        meetings.sort()
        gaps += sum(max(0, later[0] - earlier[1]) for earlier, later in zip(meetings, meetings[1:]))
    return len(by_day), gaps, -min((m[0][0] for m in by_day.values()), default=0)


def _describe(schedule: list[tuple[str, list[dict]]]) -> dict:
    sections = [section for _, package in schedule for section in package]
    slots = [(day, start, end, f"{section.get('subject')} {section.get('courseNumber')} {section.get('scheduleTypeDescription')}")
             for section in sections for day, start, end, _, _ in _slots(section)]
    week = {code: [f'{_clock(start)}-{_clock(end)} {label}' for _, start, end, label in sorted(
                (slot for slot in slots if slot[0] == code), key=lambda slot: slot[1])]
            for _, code in DAYS if any(slot[0] == code for slot in slots)}
    days, gaps, _ = _rank([(day, start, end, None, None) for day, start, end, _ in slots])
    return {
        'courses': [course for course, _ in schedule],
        'total_credits': sum(_credits(section) for section in sections),
        'days_on_campus': days,
        'earliest_start': _clock(min(start for _, start, _, _ in slots)) if slots else None,
        'latest_end': _clock(max(end for _, _, end, _ in slots)) if slots else None,
        'minutes_between_classes': gaps,
        'week': week,
        'sections': [_section(section) for section in sections],
    }


def build_schedules(term: str, courses: list[str], count: int | None, open_only: bool, earliest_start: str | None,
                    latest_end: str | None, days_off: str, max_credits: float | None, max_results: int) -> dict:
    earliest = _minutes(earliest_start.replace(':', '')) if earliest_start else None
    latest = _minutes(latest_end.replace(':', '')) if latest_end else None
    courses = list(dict.fromkeys(re.sub(r'^([A-Z]+)\s*(\d+)$', r'\1 \2', course.upper().strip()) for course in courses))
    count = min(count or len(courses), len(courses))
    options, report = {}, {}
    with _search_session(term) as client:
        for course in courses:
            sections = _course_sections(client, term, course)
            packages = [package for package in _packages(sections)
                        if all(_fits(section, open_only, earliest, latest, days_off) for section in package)]
            report[course] = {'sections_offered': len(sections), 'options_after_filters': len(packages)}
            if not sections:
                report[course]['note'] = 'Not offered this term.'
            elif not packages:
                report[course]['note'] = 'No section fits the filters (seats, times, or days off).'
            if packages:
                options[course] = packages

    found, examined = [], 0
    available = [course for course in courses if course in options]

    def search(index: int, chosen: list[tuple[str, list[dict]]], slots: list[tuple], credits: float):
        nonlocal examined
        if examined >= MAX_SCHEDULES_EXAMINED:
            return
        if len(chosen) == count:
            examined += 1
            found.append((_rank(slots), chosen))
            return
        if len(available) - index < count - len(chosen):
            return
        course = available[index]
        for package in options[course]:
            package_slots = [slot for section in package for slot in _slots(section)]
            package_credits = sum(_credits(section) for section in package)
            if max_credits is not None and credits + package_credits > max_credits:
                continue
            if not _clash(package_slots, slots):
                search(index + 1, chosen + [(course, package)], slots + package_slots, credits + package_credits)
        search(index + 1, chosen, slots, credits)  # Leave this course out when picking `count` of them.

    if len(available) >= count:
        search(0, [], [], 0.0)
    found.sort(key=lambda item: item[0])
    return {
        'term': term, 'courses_requested': courses, 'courses_per_schedule': count,
        'schedules_found': len(found), 'search_capped': examined >= MAX_SCHEDULES_EXAMINED,
        'schedules': [_describe(chosen) for _, chosen in found[:max_results]], 'courses': report,
        'ranking': _rank.__doc__.split(': ', 1)[1],
        'note': 'Prerequisites, restrictions, and registration holds are not checked. Register yourself in Banner.',
    }


def _registration(term: str) -> dict:
    with _session() as context:
        # Loading View Registration Information sets up the Banner session.
        _open(context, f'{BANNER}/registrationHistory/registrationHistory').close()
        body = _get_json(context, f'{BANNER}/registrationHistory/reset', {'term': term})
    data = body.get('data') or {}
    classes = [{
        'crn': item.get('courseReferenceNumber'),
        'course': f"{item.get('subject')} {item.get('courseNumber')}",
        'section': item.get('sequenceNumber'),
        'title': html.unescape(item.get('courseTitle') or ''),
        'type': item.get('scheduleDescription'),
        'credits': item.get('creditHour'),
        'status': (item.get('courseRegistrationStatusDescription') or '').strip('* '),
        'registered_on': item.get('registrationStatusDate'),
        'grading_mode': item.get('gradingModeDescription'),
        'instructors': item.get('instructorNames') or [],
        'meetings': _meetings(item.get('meetingTimes') or []),
        'midterm_grade': item.get('gradeMidTerm'),
        'final_grade': item.get('grade'),
    } for item in data.get('registrations') or []]
    return {'term': term, 'total_credits': data.get('totalCredit'), 'classes': classes}


def get_registration(term: str) -> dict:
    return _in_browser(_registration, term)


# Degree Works

def _audit() -> dict:
    """Load the Degree Works dashboard and keep the audit JSON its own front end fetches."""
    with _session() as context:
        page = context.new_page()
        try:
            with page.expect_response(lambda r: '/api/audit' in r.url and r.status == 200, timeout=45_000) as info:
                page.goto(f'{DEGREEWORKS}/worksheets/WEB31')
            return info.value.json()
        except PlaywrightError:
            if _on_sso(page.url):
                raise _expired() from None
            raise LehighError('degreeworks_unavailable', 'Degree Works did not return an audit. '
                              'Off campus, connect to the Lehigh VPN and try again.') from None


def fetch_audit() -> dict:
    return _in_browser(_audit)


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _classes(audit: dict) -> list[dict]:
    return [{
        'course': f"{item.get('discipline')} {item.get('number')}",
        'title': item.get('courseTitle'),
        'term': item.get('termLiteral') or item.get('term'),
        'term_code': item.get('term'),
        'grade': item.get('letterGrade'),
        'credits': _num(item.get('credits')),
        'in_progress': item.get('inProgress') == 'Y',
        'transfer': item.get('transfer') == 'T',
        '_gpa_points': _num(item.get('gpaGradePoints')) or 0.0,
        '_gpa_credits': _num(item.get('gpaCredits')) or 0.0,
    } for item in (audit.get('classInformation') or {}).get('classArray') or []]


def _public(course: dict) -> dict:
    return {key: value for key, value in course.items() if not key.startswith('_')}


def _gpa(classes: list[dict]) -> float | None:
    hours = sum(course['_gpa_credits'] for course in classes)
    return round(sum(course['_gpa_points'] for course in classes) / hours, 3) if hours else None


def _course_option(course: dict) -> str:
    """One acceptable course, e.g. "CSE 340" or "any course with attribute HU or SS"."""
    discipline, number = course.get('discipline') or '', course.get('number') or ''
    if course.get('numberEnd'):
        number = f"{number}-{course['numberEnd']}"
    condition = ' or '.join(f"{item.get('code', '').lower()} {'/'.join(item.get('valueList') or [])}"
                            for item in course.get('withArray') or [])
    if discipline == '@' and number == '@':
        return f'any course with {condition}' if condition else 'any course'
    label = f"{discipline} {'(any number)' if number == '@' else number}".strip()
    return f'{label} with {condition}' if condition else label


def _rule(rule: dict) -> dict:
    percent = _num(rule.get('percentComplete'))
    out = {'label': rule.get('label'), 'percent_complete': percent,
           'status': 'complete' if percent == 100 else 'in progress' if 'inProgressIncomplete' in rule else 'not met'}
    applied = (rule.get('classesAppliedToRule') or {}).get('classArray') or []
    if applied:
        out['applied'] = [f"{item.get('discipline')} {item.get('number')}" for item in applied]
    requirement = rule.get('requirement') or {}
    if percent != 100 and requirement.get('courseArray'):
        if requirement.get('classesBegin'):
            out['needs'] = f"{requirement['classesBegin']} class(es)"
        elif requirement.get('creditsBegin'):
            out['needs'] = f"{requirement['creditsBegin']} credits"
        out['options'] = [_course_option(item) for item in requirement['courseArray'][:20]]
    children = [_rule(item) for item in rule.get('ruleArray') or []]
    if children:
        out['rules'] = children
    return out


def _credits_required(block: dict) -> float | None:
    for qualifier in (block.get('header') or {}).get('qualifierArray') or []:
        if qualifier.get('name') == 'CLASSESCREDITS':
            return _num(qualifier.get('credits'))
    return None


def summarize_audit(audit: dict) -> dict:
    header = audit.get('auditHeader') or {}
    info = audit.get('degreeInformation') or {}
    goals = info.get('goalArray') or []
    return {
        'student': header.get('studentName'),
        'audit_date': header.get('dateYear') and f"{header.get('dateMonth')}/{header.get('dateDay')}/{header.get('dateYear')}",
        'degree_percent_complete': _num(header.get('percentComplete')),
        'gpa': _num(header.get('studentSystemGpa')),
        'degrees': [{'degree': item.get('degreeLiteral'), 'level': item.get('studentLevelLiteral'),
                     'catalog_year': item.get('catalogYearLit'), 'active_term': item.get('activeTermLiteral')}
                    for item in info.get('degreeDataArray') or []],
        'programs': [{'type': goal.get('code'), 'value': goal.get('valueLiteral') or goal.get('value')}
                     for goal in goals if goal.get('code') != 'ADVISOR'],
        'advisors': [{'name': goal.get('advisorName'), 'email': goal.get('advisorEmail'), 'type': goal.get('attachCode')}
                     for goal in goals if goal.get('code') == 'ADVISOR'],
        'blocks': [{
            'title': block.get('title'),
            'type': block.get('requirementType'),
            'percent_complete': _num(block.get('percentComplete')),
            'credits_required': _credits_required(block),
            'credits_applied': _num(block.get('creditsApplied')),
            'gpa': _num(block.get('gpa')),
            'rules': [_rule(item) for item in block.get('ruleArray') or []],
        } for block in audit.get('blockArray') or []],
    }


def summarize_gpa(audit: dict) -> dict:
    header = audit.get('auditHeader') or {}
    degrees = (audit.get('degreeInformation') or {}).get('degreeDataArray') or [{}]
    classes = _classes(audit)
    reported = _num(header.get('studentSystemGpa'))
    major = next((block for block in audit.get('blockArray') or [] if block.get('requirementType') == 'MAJOR'), None)
    terms: dict[str, list[dict]] = {}
    for course in sorted((c for c in classes if not c['in_progress']), key=lambda c: c['term_code'] or ''):
        terms.setdefault(course['term'] or 'Unknown', []).append(course)
    return {
        'cumulative_gpa': reported if reported is not None else _gpa(classes),
        'major_gpa': _num(major.get('gpa')) if major else None,
        'credits_earned': _num(degrees[0].get('studentSystemCumulativeTotalCreditsEarned')),
        'credits_in_progress': sum(course['credits'] or 0 for course in classes if course['in_progress']),
        'by_term': [{'term': term, 'term_gpa': _gpa(courses), 'courses': [_public(c) for c in courses]}
                    for term, courses in terms.items()],
    }


def course_history(audit: dict) -> list[dict]:
    return [_public(course) for course in sorted(_classes(audit), key=lambda c: c['term_code'] or '')]
