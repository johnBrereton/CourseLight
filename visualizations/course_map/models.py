from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from ..maps.models import MapConfig, MapPlace
from ..schedule.models import Label, Model, Notice, Term


class ClassStop(Model):
    id: str
    course: Label
    title: Label
    location: Label
    instructors: Annotated[list[Label], Field(max_length=20)]
    start_minute: Annotated[int, Field(ge=0, lt=1440)]
    end_minute: Annotated[int, Field(gt=0, le=1440)]
    place_id: str | None



class MapDay(Model):
    date: date
    stops: Annotated[list[ClassStop], Field(max_length=200)]


class CourseMapView(Model):
    schema_version: Literal['course_map.v1'] = 'course_map.v1'
    term: Term
    term_label: Label
    timezone: Literal['America/New_York'] = 'America/New_York'
    selected_date: date
    fetched_at: AwareDatetime
    places: Annotated[list[MapPlace], Field(max_length=100)]
    days: Annotated[list[MapDay], Field(min_length=7, max_length=7)]
    map: MapConfig
    notices: Annotated[list[Notice], Field(max_length=20)]
