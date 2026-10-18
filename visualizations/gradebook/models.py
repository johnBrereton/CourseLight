"""Released grade rows from CourseSite and Gradescope."""
from typing import Annotated, Literal

from pydantic import Field

from ..courses.models import Label, Model, Notice, PositiveID

GradeRef = Annotated[str, Field(pattern=r'^(coursesite|gradescope):\d+$')]
URL = Annotated[str, Field(max_length=2048)]


class GradeItem(Model):
    ref: GradeRef
    name: Label
    kind: Literal['assessment', 'category', 'course']
    display_score: Label
    percent: Annotated[float, Field(allow_inf_nan=False)] | None = None
    status: Label
    url: URL
    usable: bool = False


class GradeSource(Model):
    site: Literal['coursesite', 'gradescope']
    name: Label
    course_name: Label | None = None
    match_note: Notice | None = None
    url: URL | None = None
    notice: Notice | None = None
    items: Annotated[list[GradeItem], Field(max_length=300)] = Field(default_factory=list)


class Syllabus(Model):
    module_id: PositiveID
    title: Label
    url: URL
    text: Annotated[str, Field(max_length=60000)] = ''
    notice: Notice | None = None


class GradebookView(Model):
    schema_version: Literal['gradebook.v1'] = 'gradebook.v1'
    course_id: PositiveID
    course_name: Label
    site_url: URL
    sources: Annotated[list[GradeSource], Field(min_length=1, max_length=2)]
