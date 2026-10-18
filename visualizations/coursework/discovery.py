"""Find possible coursework outside Moodle assignment activities."""
from __future__ import annotations

from datetime import datetime
from html import unescape
import re
from typing import get_args

from moodle import Moodle, MoodleError
from ..courses.models import Course
from .models import CourseworkItem, CourseworkKind

WORK = re.compile(r'\b(?:assignments?|homeworks?|problem[\s-]*sets?|projects?|labs?|exercises?|'
                  r'worksheets?|readings?|reflections?|essays?|reports?|presentations?|discussions?)\b'
                  r'|\b(?:hw|ps|pa)[\s_#-]*\d+\b', re.I)
REFERENCE = re.compile(r'\b(?:solutions?|answer[\s-]*keys?|syllabus|lecture|slides?|recordings?|'
                       r'attendance|polic(?:y|ies)|content improvement)\b', re.I)


def plain_text(value) -> str:
    if not isinstance(value, str):
        return ''
    value = re.sub(r'<(script|style|template|noscript)\b[^>]*>.*?</\1\s*>', ' ', value[:20000], flags=re.I | re.S)
    return ' '.join(unescape(re.sub(r'<[^>]*>', ' ', value)).split())


def find_coursework(client: Moodle, course: Course, start: datetime, stop: datetime):
    warnings = []
    try:
        sections = client.call('core_course_get_contents', courseid=course.id,
                               options=[{'name': 'excludecontents', 'value': 1}])
        if not isinstance(sections, list):
            raise MoodleError('invalid_response', 'Course contents were unavailable.')
    except MoodleError:
        return [], ['Other course posts could not be checked. Open CourseSite for additional coursework.']

    modules = []
    skipped = False
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get('modules'), list):
            skipped = True
            continue
        if section.get('uservisible') is False or section.get('visible') == 0:
            continue
        section_name = plain_text(section.get('name'))[:240] or 'Course content'
        for module in section['modules']:
            if not isinstance(module, dict):
                skipped = True
                continue
            if module.get('uservisible') is False or module.get('visible') == 0:
                continue
            if module.get('modname') in get_args(CourseworkKind):
                modules.append((section_name, module))

    pages = {}
    if any(module.get('modname') == 'page' for _, module in modules):
        try:
            data = client.call('mod_page_get_pages_by_courses', courseids=[course.id])
            if not isinstance(data, dict) or not isinstance(data.get('pages'), list):
                raise MoodleError('invalid_response', 'Page text was unavailable.')
            pages = {page['id']: page for page in data['pages']
                     if isinstance(page, dict) and type(page.get('id')) is int and page.get('course') == course.id}
            if data.get('warnings'):
                warnings.append('Some Moodle Page text could not be checked for coursework.')
        except MoodleError:
            warnings.append('Moodle Page text could not be checked; titles and visible descriptions were used.')

    found = []
    seen = set()
    for section_name, module in modules:
        module_id = module.get('id')
        if type(module_id) is not int or module_id <= 0:
            skipped = True
            continue
        if module_id in seen:
            continue
        seen.add(module_id)
        name = plain_text(module.get('name'))[:240]
        if not name or REFERENCE.search(name):
            continue
        description = plain_text(module.get('description'))
        if module['modname'] == 'page':
            instance = module.get('instance')
            page = pages.get(instance) if type(instance) is int else None
            if page:
                description = ' '.join(filter(None, (description, plain_text(page.get('content')))))
        matched_by = next((source for source, text in
                           (('name', name), ('section', section_name), ('description', description))
                           if WORK.search(text)), None)
        if not matched_by:
            continue

        # Only explicit due-date metadata establishes a date. Posted/modified
        # times and dates mentioned in prose never become weekly deadlines.
        dates = module.get('dates') or []
        if not isinstance(dates, list):
            skipped = True
            continue
        due_dates = [item for item in dates if isinstance(item, dict) and
                     (item.get('dataid') == 'duedate' or plain_text(item.get('label')).rstrip(':').casefold() == 'due')]
        if any(type(item.get('timestamp')) is not int or item['timestamp'] < 0 for item in due_dates):
            skipped = True
            continue
        timestamps = {item['timestamp'] for item in due_dates if item['timestamp'] > 0}
        if len(timestamps) > 1:
            skipped = True
            continue
        due_at = None
        if timestamps:
            try:
                due_at = datetime.fromtimestamp(timestamps.pop(), start.tzinfo)
            except (ValueError, OverflowError, OSError):
                skipped = True
                continue
            if not start <= due_at < stop:
                continue
        kind = module['modname']
        url = (course.url if kind == 'label' else
               f'{client.url}/mod/{kind}/view.php?id={module_id}')
        found.append(CourseworkItem(id=module_id, name=name, url=url, kind=kind, section=section_name,
                                   excerpt=description[:497] + ('…' if len(description) > 497 else ''),
                                   matched_by=matched_by, due_at=due_at))

    if skipped:
        warnings.append('Some course posts or their dates were unreadable and could not be included.')
    if len(found) > 20:
        warnings.append('Showing the first 20 possible coursework items. Open CourseSite for the rest.')
    return found[:20], warnings
