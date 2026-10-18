"""Add heuristic coursework candidates to the validated assignment view."""
from __future__ import annotations

from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, model_validator

from ..courses.models import Course, CoursesView, Label, Model, Notice, PositiveID

CourseworkKind = Literal['resource', 'url', 'page', 'folder', 'label', 'forum', 'lti', 'book']
RISK_NOTICE = ('Riskier, keyword-based search: matches may be unrelated or from another week, '
               'and real work can be missed. Verify these candidates in CourseSite.')


class CourseworkItem(Model):
    id: PositiveID
    name: Label
    url: Annotated[str, Field(max_length=2048)]
    kind: CourseworkKind
    section: Label
    excerpt: Annotated[str, Field(max_length=500)] = ''
    matched_by: Literal['name', 'section', 'description']
    due_at: AwareDatetime | None = None


class CourseworkCourse(Course):
    other_work: Annotated[list[CourseworkItem], Field(max_length=20)] = Field(default_factory=list)


class CourseworkView(CoursesView):
    schema_version: Literal['coursework.v1'] = 'coursework.v1'
    courses: Annotated[list[CourseworkCourse], Field(max_length=12)]
    coverage: Notice = (RISK_NOTICE + ' Includes assignment deadlines and possible coursework from course posts. '
                        'Undated candidates are week-unverified. File contents, discussion replies, '
                        'and external-tool contents are not inspected.')

    @model_validator(mode='after')
    def coherent_candidates(self):
        zone = ZoneInfo(self.timezone)
        for course in self.courses:
            if len({item.id for item in course.other_work}) != len(course.other_work):
                raise ValueError('Coursework module IDs must be unique within a course.')
            for item in course.other_work:
                expected = (course.url if item.kind == 'label' else
                            f'{self.site_url}/mod/{item.kind}/view.php?id={item.id}')
                if item.url != expected:
                    raise ValueError('Coursework links must refer to their Moodle module.')
                if item.due_at and not self.week_start <= item.due_at.astimezone(zone).date() <= self.week_end:
                    raise ValueError('Dated coursework must fall within the selected week.')
        return self
