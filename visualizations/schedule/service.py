"""Adapt existing Banner reads to the same schedule grid."""
from datetime import datetime
from html import unescape
import math
import re
from zoneinfo import ZoneInfo

import lehigh
from .models import Meeting, OptionsQuery, ScheduleOption, ScheduleQuery, ScheduleView, Section


def text(value, fallback='', limit=240):
    return ' '.join(unescape(re.sub(r'<[^>]*>', ' ', str(value or ''))).split())[:limit] or fallback


def credits(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and 0 <= number <= 60 else None
    except (TypeError, ValueError):
        return None


def meeting(raw):
    time_label = text(raw.get('time'), 'TBA', 80)
    match = re.fullmatch(r'(\d{1,2}):([0-5]\d)(am|pm)-(\d{1,2}):([0-5]\d)(am|pm)', time_label.lower())
    start = end = None
    if match:
        h1, m1, p1, h2, m2, p2 = match.groups()
        if 1 <= int(h1) <= 12 and 1 <= int(h2) <= 12:
            start = (int(h1) % 12 + (12 if p1 == 'pm' else 0)) * 60 + int(m1)
            end = (int(h2) % 12 + (12 if p2 == 'pm' else 0)) * 60 + int(m2)
            if end <= start:
                start = end = None
    first = last = None
    try:
        first_text, last_text = str(raw.get('dates', '')).split(' to ')
        first = datetime.strptime(first_text, '%m/%d/%Y').date()
        last = datetime.strptime(last_text, '%m/%d/%Y').date()
        if last < first:
            first = last = None
    except ValueError:
        first = last = None
    days = str(raw.get('days') or '').upper()
    days = ''.join(day for day in 'MTWRFSU' if day in days) if re.fullmatch(r'[MTWRFSU]+', days) else ''
    return Meeting(days=days, start_minute=start, end_minute=end, time_label=time_label,
                   location=text(raw.get('location'), 'Location TBA'), kind=text(raw.get('type'), limit=100),
                   building=text(raw.get('building')), room=text(raw.get('room'), limit=80),
                   start_date=first, end_date=last)


def sections(records, *, registered=False):
    result, skipped, omitted, seen = [], 0, 0, set()
    for raw in records:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        status = text(raw.get('status'), limit=120)
        if registered and re.search(r'drop|withdraw|wait.?list|cancel|deleted', status, re.I):
            omitted += 1
            continue
        crn = str(raw.get('crn') or '')
        if not re.fullmatch(r'\d{5}', crn):
            skipped += 1
            continue
        if crn in seen:
            continue
        seen.add(crn)
        raw_meetings = raw.get('meetings')
        if not isinstance(raw_meetings, list):
            raw_meetings = []
            skipped += 1
        meetings = []
        for item in raw_meetings:
            if not isinstance(item, dict):
                skipped += 1
                continue
            normalized = meeting(item)
            if normalized not in meetings:
                meetings.append(normalized)
        teachers = raw.get('instructors') or []
        if isinstance(teachers, str):
            teachers = [teachers]
        result.append(Section(
            crn=crn, course=text(raw.get('course'), 'Course'), section=text(raw.get('section'), limit=20),
            title=text(raw.get('title'), 'Untitled course'), kind=text(raw.get('type'), limit=100),
            credits=credits(raw.get('credits')), instructors=[text(name) for name in teachers if text(name)],
            registration_status=status, meetings=meetings,
            seats_available=raw.get('seats_available') if type(raw.get('seats_available')) is int else None,
        ))
    notes = []
    if skipped:
        notes.append('Some Banner records could not be displayed. Check the original schedule in Banner.')
    if omitted:
        notes.append(f'{omitted} dropped, withdrawn, waitlisted, or cancelled sections are excluded.')
    return result, notes


def term_label(term):
    try:
        terms = lehigh.get_terms(30)
        found = next((item for item in terms if item.get('code') == term), None)
        return text(found.get('description'), f'Term {term}').replace(' (View Only)', '') if found else f'Term {term}'
    except lehigh.LehighError:
        return f'Term {term}'


def get_class_schedule(query: ScheduleQuery) -> ScheduleView:
    raw = lehigh.get_registration(query.term)
    rows, notices = sections(raw['classes'], registered=True)
    total = sum(s.credits for s in rows) if all(s.credits is not None for s in rows) else None
    option = ScheduleOption(id='registered', label='Your classes', total_credits=total, sections=rows)
    return ScheduleView(mode='registered', term=query.term, term_label=term_label(query.term),
                        fetched_at=datetime.now(ZoneInfo('America/New_York')), options=[option], notices=notices)


def get_schedule_options(query: OptionsQuery) -> ScheduleView:
    raw = lehigh.build_schedules(**query.model_dump())
    options, notices = [], []
    for index, candidate in enumerate(raw['schedules']):
        rows, warnings = sections(candidate['sections'])
        notices.extend(warnings)
        options.append(ScheduleOption(id=f'option-{index + 1}', label=f'Option {index + 1}',
                                      total_credits=credits(candidate.get('total_credits')), sections=rows))
    if not query.open_only:
        notices.append('Includes sections without open seats.')
    if raw.get('search_capped'):
        notices.append('Banner schedule search reached its limit; more combinations may exist.')
    for code, report in raw.get('courses', {}).items():
        if report.get('note'):
            notices.append(f'{text(code)}: {text(report["note"])}')
    return ScheduleView(mode='proposed', term=query.term, term_label=term_label(query.term),
                        fetched_at=datetime.now(ZoneInfo('America/New_York')), options=options,
                        notices=list(dict.fromkeys(notices)))
