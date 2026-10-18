"""Reuse released grades and verify the syllabus before creating a scenario."""
import re

from ..gradebook.service import get_gradebook
from ..gradebook.syllabus import course_modules, read_syllabi
from .models import GradingPlan, ProjectedWork, Projection, GradeTargetView


def projection_for(plan: GradingPlan, syllabi, sources, target):
    syllabus = next((s for s in syllabi if s.module_id == plan.syllabus_module_id), None)
    normalize = lambda text: ' '.join(text.split()).casefold()
    if not syllabus or not syllabus.text or normalize(plan.evidence) not in normalize(syllabus.text):
        raise ValueError('Projection evidence must be a passage returned by read_grading_policy for this syllabus.')
    lookup = {item.ref: item for source in sources for item in source.items}
    work = []
    names = set()
    for selected in plan.work:
        item = lookup.get(selected.grade_ref) if selected.grade_ref else None
        if selected.grade_ref and item is None:
            raise ValueError(f'Grade reference {selected.grade_ref} was not returned. Re-read the gradebook.')
        if item:
            if item.kind != 'assessment' or (item.percent is not None and not item.usable):
                raise ValueError('Use released assessment percentages, not totals, excluded items, extra credit, or stale scores.')
            name = re.sub(r'\W+', '', item.name.casefold())
            if name in names:
                raise ValueError('A mirrored assignment appears twice. Select only one source for each assessment.')
            names.add(name)
        work.append(ProjectedWork(**selected.model_dump(), percent=item.percent if item else None))
    return Projection(source_url=syllabus.url, explanation=plan.explanation,
                      assumptions=plan.assumptions, work=work, target=target)


def get_grade_target(client, read_grades, course_id, gradescope_course_id, plan, target):
    grades = get_gradebook(client, read_grades, course_id, gradescope_course_id)
    _, modules = course_modules(client, course_id)
    syllabi = read_syllabi(client, course_id, modules, plan.syllabus_module_id if plan else None)
    projection, notice = None, None
    if plan:
        try:
            projection = projection_for(plan, syllabi, grades.sources, target)
        except ValueError as exc:
            notice = str(exc)[:500]
    else:
        notice = 'Read the syllabus grading rules and map the full course weights to calculate a target.'
    view = GradeTargetView(course_id=course_id, course_name=grades.course_name, site_url=client.url,
                          syllabi=[s.model_copy(update={'text': ''}) for s in syllabi],
                          projection=projection, projection_notice=notice)
    return GradeTargetView.model_validate(client.clean(view.model_dump(mode='json')))
