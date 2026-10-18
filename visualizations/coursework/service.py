"""Opt-in broader search; the ordinary Courses service never calls this path."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from moodle import Moodle
from ..courses.models import CoursesQuery
from ..courses.service import get_courses
from .discovery import find_coursework
from .models import CourseworkCourse, CourseworkView


def get_coursework(client: Moodle, query: CoursesQuery) -> CourseworkView:
    assignments = get_courses(client, query)
    start = datetime.combine(assignments.week_start, time.min, ZoneInfo(query.timezone))
    stop = start + timedelta(days=7)
    courses = []
    for source in assignments.courses:
        course = CourseworkCourse(**source.model_dump())
        course.other_work, warnings = find_coursework(client, course, start, stop)
        course.warnings.extend(warnings)
        if ((course.status == 'unavailable' and course.other_work)
                or (course.status == 'ready' and warnings)):
            course.status = 'partial'
        courses.append(course)
    output = CourseworkView(
        **assignments.model_dump(exclude={'schema_version', 'courses', 'coverage'}),
        courses=courses,
    )
    return CourseworkView.model_validate(client.clean(output.model_dump(mode='json')))
