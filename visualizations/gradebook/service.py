"""Adapt the shared two-site grade reader; never add the two gradebooks together."""
import math
import re

from ..coursework.discovery import plain_text
from .models import GradebookView, GradeItem, GradeSource
from .syllabus import course_name


def number(value):
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (ValueError, TypeError):
        return None


def percentage(value):
    match = re.fullmatch(r'\s*(-?\d+(?:\.\d+)?)\s*%\s*', str(value))
    return number(match[1]) if match else None


def grade_sources(data, site_url, course_id):
    sources = []
    for site, name in [('coursesite', 'CourseSite'), ('gradescope', 'Gradescope')]:
        raw = data.get(site, {})
        notice = (raw.get('error') or {}).get('message') or raw.get('unavailable')
        source = GradeSource(site=site, name=name, notice=plain_text(notice)[:500] or None)
        matched = data.get('matched', {}).get(site, {})
        if matched.get('course_id'):
            term = plain_text(matched.get('term'))
            source.match_note = ('Matched by course code' + (f' · {term}' if term else '') + '. Confirm this is the same course.')[:500]
        if notice:
            sources.append(source)
            continue
        if site == 'coursesite':
            source.url = f'{site_url}/grade/report/user/index.php?id={course_id}'
            source.course_name = plain_text(data.get('matched', {}).get(site, {}).get('course'))[:240] or None
            rows = [i for u in raw.get('usergrades', []) for i in u.get('gradeitems', [])]
            for item in rows[:300]:
                kind = item.get('itemtype') if item.get('itemtype') in {'course', 'category'} else 'assessment'
                hidden = bool(item.get('gradeishidden') or item.get('gradehiddenbydate'))
                stale = bool(item.get('gradeneedsupdate'))
                value = None if hidden else percentage(item.get('percentageformatted'))
                display = 'Not released' if hidden else plain_text(item.get('gradeformatted'))
                status = 'Not released' if hidden else 'Updating' if stale else 'Released' if value is not None else 'No released percentage'
                source.items.append(GradeItem(ref=f'coursesite:{item["id"]}', kind=kind,
                    name=plain_text(item.get('itemname'))[:240] or ('Course total' if kind == 'course' else 'Grade item'),
                    display_score=display[:240] if display and display != '-' else '—', percent=value,
                    status=status, url=source.url,
                    usable=kind == 'assessment' and not hidden and not stale and not item.get('excluded') and value is not None and 0 <= value <= 100))
            if raw.get('warnings'):
                source.notice = 'CourseSite returned warnings; some grades may be unavailable.'
        else:
            gid = str(raw.get('course_id', ''))
            if not re.fullmatch(r'\d{1,12}', gid):
                source.notice = 'No Gradescope course was returned.'
                sources.append(source)
                continue
            source.url = f'https://www.gradescope.com/courses/{gid}'
            source.course_name = plain_text(raw.get('course'))[:240] or None
            for index, item in enumerate(raw.get('assignments', [])[:300]):
                match = re.fullmatch(re.escape(source.url) + r'/assignments/(\d+)', item.get('url') or '')
                # Missing assignment IDs remain visible but cannot be used in projections.
                ref = f'gradescope:{match[1]}' if match else f'gradescope:{index + 1000000000000}'
                score = plain_text(item.get('score'))
                ratio = re.fullmatch(r'(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)', score)
                value = (float(ratio[1]) / float(ratio[2]) * 100 if ratio and float(ratio[2]) > 0 else percentage(score))
                source.items.append(GradeItem(ref=ref, kind='assessment', name=plain_text(item.get('name'))[:240] or 'Assignment',
                    display_score=score[:240] or '—', percent=value,
                    status=plain_text(item.get('status'))[:240] or 'No released score', url=item.get('url') if match else source.url,
                    usable=bool(match) and value is not None and 0 <= value <= 100))
        if len(source.items) == 300:
            source.notice = 'Showing the first 300 grade items. Check the source for additional work.'
        sources.append(source)
    return sources


def get_gradebook(client, read_grades, course_id, gradescope_course_id=None):
    name = course_name(client, course_id)
    response = read_grades(course_id=course_id, gradescope_course_id=gradescope_course_id, source='both')
    if not response.get('ok'):
        raise ValueError(response.get('error', {}).get('message', 'Grades could not be read.'))
    data = response['data']
    sources = grade_sources(data, client.url, course_id)
    view = GradebookView(course_id=course_id, course_name=name, site_url=client.url, sources=sources)
    return GradebookView.model_validate(client.clean(view.model_dump(mode='json')))
