"""One validated weekly-grid contract for registered and proposed schedules."""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
import re

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

Term = Annotated[str, Field(pattern=r'^\d{6}$')]
CourseCode = Annotated[str, Field(pattern=r'^[A-Za-z]{2,4} ?\d{3}$')]
Clock = Annotated[str, Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')]
Label = Annotated[str, Field(min_length=1, max_length=240)]
Notice = Annotated[str, Field(min_length=1, max_length=500)]
Credits = Annotated[float, Field(ge=0, le=60)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)


class ScheduleQuery(Model):
    term: Term


class OptionsQuery(ScheduleQuery):
    courses: Annotated[list[CourseCode], Field(min_length=1, max_length=10)]
    count: Annotated[int, Field(strict=True, ge=1, le=10)] | None = None
    open_only: bool = True
    earliest_start: Clock | None = None
    latest_end: Clock | None = None
    days_off: Annotated[str, Field(pattern=r'^[MTWRFSU]*$', max_length=7)] = ''
    max_credits: Annotated[float, Field(gt=0, le=30)] | None = None
    max_results: Annotated[int, Field(strict=True, ge=1, le=10)] = 3

    @field_validator('courses')
    @classmethod
    def normalize_courses(cls, value):
        codes = [re.sub(r'^([A-Z]+)\s*(\d+)$', r'\1 \2', code.upper()) for code in value]
        if len(set(codes)) != len(codes):
            raise ValueError('Choose each course once.')
        return codes

    @model_validator(mode='after')
    def valid_preferences(self):
        if self.count is not None and self.count > len(self.courses):
            raise ValueError('count cannot exceed the number of candidate courses.')
        if self.earliest_start and self.latest_end and self.earliest_start >= self.latest_end:
            raise ValueError('earliest_start must be before latest_end.')
        return self


class Meeting(Model):
    days: Annotated[str, Field(pattern=r'^[MTWRFSU]*$', max_length=7)]
    start_minute: Annotated[int, Field(strict=True, ge=0, lt=1440)] | None
    end_minute: Annotated[int, Field(strict=True, gt=0, le=1440)] | None
    time_label: Annotated[str, Field(min_length=1, max_length=80)]
    location: Label
    building: Annotated[str, Field(max_length=240)] = ''
    room: Annotated[str, Field(max_length=80)] = ''
    kind: Annotated[str, Field(max_length=100)]
    start_date: date | None
    end_date: date | None

    @model_validator(mode='after')
    def coherent_time(self):
        if (self.start_minute is None) != (self.end_minute is None):
            raise ValueError('A meeting needs both start and end times, or neither.')
        if self.start_minute is not None and self.end_minute <= self.start_minute:
            raise ValueError('Meeting end must follow its start.')
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError('Meeting dates must be in order.')
        if len(set(self.days)) != len(self.days):
            raise ValueError('Meeting days must be unique.')
        return self


class Section(Model):
    crn: Annotated[str, Field(pattern=r'^\d{5}$')]
    course: Label
    section: Annotated[str, Field(max_length=20)]
    title: Label
    kind: Annotated[str, Field(max_length=100)]
    credits: Credits | None
    instructors: Annotated[list[Label], Field(max_length=20)]
    registration_status: Annotated[str, Field(max_length=120)] = ''
    meetings: Annotated[list[Meeting], Field(max_length=40)]
    seats_available: Annotated[int, Field(strict=True)] | None = None


class ScheduleOption(Model):
    id: Annotated[str, Field(pattern=r'^[a-z0-9-]{1,40}$')]
    label: Label
    total_credits: Credits | None
    sections: Annotated[list[Section], Field(max_length=40)]

    @model_validator(mode='after')
    def unique_sections(self):
        if len({s.crn for s in self.sections}) != len(self.sections):
            raise ValueError('Section CRNs must be unique within a schedule.')
        return self


class ScheduleView(Model):
    schema_version: Literal['schedule.v1'] = 'schedule.v1'
    mode: Literal['registered', 'proposed']
    term: Term
    term_label: Label
    timezone: Literal['America/New_York'] = 'America/New_York'
    fetched_at: AwareDatetime
    options: Annotated[list[ScheduleOption], Field(max_length=10)]
    notices: Annotated[list[Notice], Field(max_length=16)] = Field(default_factory=list)

    @model_validator(mode='after')
    def coherent_options(self):
        if self.mode == 'registered' and len(self.options) != 1:
            raise ValueError('A registered view has one schedule.')
        if len({s.id for s in self.options}) != len(self.options):
            raise ValueError('Schedule IDs must be unique.')
        return self
