"""Small, validated input/output contracts for the Courses visualization."""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

PositiveID = Annotated[int, Field(strict=True, gt=0)]
CourseIDs = Annotated[list[PositiveID], Field(min_length=1, max_length=12)]
Label = Annotated[str, Field(min_length=1, max_length=240)]
Notice = Annotated[str, Field(min_length=1, max_length=500)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class CoursesQuery(Model):
    course_ids: CourseIDs
    timezone: Annotated[str, Field(min_length=1, max_length=80)]
    week_start: date | None = None

    @field_validator('course_ids')
    @classmethod
    def unique_courses(cls, value):
        if len(value) != len(set(value)):
            raise ValueError('Select each course only once.')
        return value

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('Use an IANA timezone such as America/New_York.') from None
        return value

    @field_validator('week_start')
    @classmethod
    def monday(cls, value):
        if value is not None and (value.weekday() != 0 or not 2000 <= value.year <= 2100):
            raise ValueError('week_start must be a Monday between 2000 and 2100.')
        return value


class Assignment(Model):
    id: PositiveID
    name: Label
    url: Annotated[str, Field(max_length=2048)]
    due_at: AwareDatetime
    due_basis: Literal['course', 'extension', 'unverified']


class Course(Model):
    id: PositiveID
    name: Label
    code: Label
    url: Annotated[str, Field(max_length=2048)]
    status: Literal['ready', 'partial', 'unavailable']
    assignments: Annotated[list[Assignment], Field(max_length=100)] = Field(default_factory=list)
    undated_count: Annotated[int, Field(ge=0)] = 0
    warnings: Annotated[list[Notice], Field(max_length=8)] = Field(default_factory=list)


class CoursesView(Model):
    schema_version: Literal['courses.v1'] = 'courses.v1'
    week_start: date
    week_end: date
    timezone: str
    fetched_at: AwareDatetime
    site_url: Annotated[str, Field(max_length=2048)]
    courses: Annotated[list[Course], Field(max_length=12)]
    coverage: Notice = 'CourseSite assignment activities only. Other activities and syllabus deadlines may differ.'

    @model_validator(mode='after')
    def coherent_result(self):
        zone = ZoneInfo(self.timezone)
        if (self.week_end - self.week_start).days != 6 or self.week_start.weekday() != 0:
            raise ValueError('The view must cover Monday through Sunday.')
        site = urlsplit(self.site_url)
        if site.scheme != 'https' or not site.hostname or site.username or site.password or site.query or site.fragment:
            raise ValueError('Use the configured HTTPS Moodle site.')
        if len({course.id for course in self.courses}) != len(self.courses):
            raise ValueError('Course IDs must be unique.')
        for course in self.courses:
            if course.url != f'{self.site_url}/course/view.php?id={course.id}':
                raise ValueError('Course links must refer to the configured Moodle site.')
            if len({item.id for item in course.assignments}) != len(course.assignments):
                raise ValueError('Assignment IDs must be unique within a course.')
            for item in course.assignments:
                prefix = self.site_url + '/mod/assign/view.php?id='
                if not item.url.startswith(prefix) or not item.url[len(prefix):].isdigit():
                    raise ValueError('Assignment links must refer to the configured Moodle site.')
                if not self.week_start <= item.due_at.astimezone(zone).date() <= self.week_end:
                    raise ValueError('Every assignment must be due during the selected week.')
        return self
