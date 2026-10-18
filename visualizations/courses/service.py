"""Read selected enrollments and filter assignment deadlines to one local week."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from html import unescape
import re
from zoneinfo import ZoneInfo

from moodle import Moodle, MoodleError
from .models import Assignment, Course, CoursesQuery, CoursesView

MAX_EXTENSION_READS = 60


def label(value, fallback: str) -> str:
    text = unescape(re.sub(r'<[^>]*>', '', str(value or '')))
    return ' '.join(text.split())[:240] or fallback


def integer(value, default=0):
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def get_courses(client: Moodle, query: CoursesQuery) -> CoursesView:
    zone = ZoneInfo(query.timezone)
    now = datetime.now(zone)
    monday = query.week_start or now.date() - timedelta(days=now.weekday())
    start = datetime.combine(monday, time.min, zone)
    stop = datetime.combine(monday + timedelta(days=7), time.min, zone)
    start_timestamp, stop_timestamp = int(start.timestamp()), int(stop.timestamp())
    identity = client.identity()
    enrollments = client.call('core_enrol_get_users_courses', userid=identity['userid'])
    if not isinstance(enrollments, list):
        raise MoodleError('invalid_response', 'CourseSite did not return an enrollment list.')
    by_id = {c['id']: c for c in enrollments if isinstance(c, dict) and integer(c.get('id')) > 0}
    if any(course_id not in by_id for course_id in query.course_ids):
        raise MoodleError('course_unavailable', 'One of the selected courses is not in the connected account’s enrollments.')

    extension_reads = 0
    can_check_extensions = any(f.get('name') == 'mod_assign_get_submission_status'
                               for f in identity.get('functions', []) if isinstance(f, dict))
    courses = []
    for course_id in query.course_ids:
        enrolled = by_id[course_id]
        code = label(enrolled.get('shortname'), f'Course {course_id}')
        name = label(enrolled.get('fullname'), code)
        if name.startswith(code + '-'):
            name = name[len(code) + 1:] or code
        course = Course(id=course_id, name=name, code=code,
                        url=f'{client.url}/course/view.php?id={course_id}', status='ready')
        courses.append(course)
        try:
            data = client.call('mod_assign_get_assignments', courseids=[course_id])
            if not isinstance(data, dict) or not isinstance(data.get('courses'), list):
                raise MoodleError('invalid_response', 'Assignment data was unavailable.')
            returned = next((c for c in data['courses'] if isinstance(c, dict) and c.get('id') == course_id), None)
            if returned is None or not isinstance(returned.get('assignments'), list):
                raise MoodleError('course_unavailable', 'Assignment data was unavailable.')
        except MoodleError:
            course.status = 'unavailable'
            course.warnings.append('Assignments could not be loaded. Open this course in CourseSite to check deadlines.')
            continue

        if data.get('warnings'):
            course.warnings.append('CourseSite withheld some assignment data. This list may be incomplete.')
        skipped, extension_unknown, seen = 0, 0, set()
        for raw in returned['assignments']:
            if not isinstance(raw, dict):
                skipped += 1
                continue
            assignment_id, cmid = integer(raw.get('id')), integer(raw.get('cmid'))
            if assignment_id <= 0 or cmid <= 0 or assignment_id in seen:
                skipped += 1
                continue
            seen.add(assignment_id)
            due = integer(raw.get('duedate'), -1)
            if due < 0:
                skipped += 1
                continue
            # get_assignments applies user/group overrides. An extension can move
            # an earlier deadline into this week, so check earlier assignments too.
            if due >= stop_timestamp:
                continue
            basis = 'unverified'
            if can_check_extensions and extension_reads < MAX_EXTENSION_READS:
                extension_reads += 1
                try:
                    status = client.call('mod_assign_get_submission_status', assignid=assignment_id,
                                         userid=identity['userid'])
                    attempt = status.get('lastattempt') if isinstance(status, dict) else None
                    if isinstance(attempt, dict) and not status.get('warnings'):
                        extension = integer(attempt.get('extensionduedate'), -1)
                        if extension >= 0:
                            basis = 'extension' if extension > due else 'course'
                            due = max(due, extension)
                except MoodleError:
                    pass
            if basis == 'unverified':
                extension_unknown += 1
            if not due:
                course.undated_count += 1
                continue
            if not start_timestamp <= due < stop_timestamp:
                continue
            course.assignments.append(Assignment(
                id=assignment_id, name=label(raw.get('name'), 'Untitled assignment'),
                url=f'{client.url}/mod/assign/view.php?id={cmid}',
                due_at=datetime.fromtimestamp(due, zone), due_basis=basis,
            ))

        course.assignments.sort(key=lambda item: (item.due_at, item.name.casefold()))
        if len(course.assignments) > 100:
            course.assignments = course.assignments[:100]
            course.warnings.append('Showing the first 100 assignments due this week. Open CourseSite for the rest.')
        if extension_unknown:
            course.warnings.append('Some personal deadline extensions could not be checked. Verify dates in CourseSite.')
        if skipped:
            course.warnings.append('Some assignment records were unreadable and could not be included.')
        if course.warnings:
            course.status = 'partial'

    output = CoursesView(week_start=monday, week_end=monday + timedelta(days=6),
                         timezone=query.timezone, fetched_at=now, site_url=client.url, courses=courses)
    return CoursesView.model_validate(client.clean(output.model_dump(mode='json')))
