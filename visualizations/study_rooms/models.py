from datetime import datetime, timezone
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, model_validator

from ..maps.models import MapConfig, MapPlace
from ..schedule.models import Label, Model, Notice

EASTERN = ZoneInfo('America/New_York')
LocalTime = Annotated[str, Field(pattern=r'^\d{4}-\d\d-\d\dT\d\d:\d\d$')]
EventID = Annotated[str, Field(pattern=r'^\d{1,12}$')]
RequestID = Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{32}$')]
SpaceID = Annotated[int, Field(strict=True, gt=0)]


def eastern(value: str) -> datetime:
    local = datetime.fromisoformat(value)
    aware = local.replace(tzinfo=EASTERN)
    if (aware.astimezone(timezone.utc).astimezone(EASTERN).replace(tzinfo=None) != local
            or aware.utcoffset() != local.replace(tzinfo=EASTERN, fold=1).utcoffset()):
        raise ValueError('Choose an unambiguous Eastern time outside the daylight-saving transition.')
    return aware


class RoomQuery(Model):
    start: LocalTime
    end: LocalTime
    query: Annotated[str, Field(max_length=100)] | None = None
    min_capacity: Annotated[int, Field(strict=True, ge=0, le=1000)] = 0
    max_results: Annotated[int, Field(strict=True, ge=1, le=30)] = 12

    @model_validator(mode='after')
    def valid_window(self):
        start, end = eastern(self.start), eastern(self.end)
        if start.date() != end.date() or end <= start:
            raise ValueError('Choose a start and later end on the same Eastern calendar day.')
        if start <= datetime.now(EASTERN):
            raise ValueError('Choose a future time for the room search.')
        return self


class Room(Model):
    space_id: SpaceID
    name: Label
    description: Annotated[str, Field(max_length=240)] = ''
    building: Annotated[str, Field(max_length=240)] = ''
    capacity: Annotated[int, Field(ge=0)] = 0
    place: MapPlace


class Selection(Model):
    room: Room
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    event_name: Annotated[str, Field(min_length=1, max_length=100)]


class Booking(Model):
    event_id: EventID
    name: Label
    status: Literal['confirmed', 'pending', 'cancelled']
    selection: Selection | None = None


class StudyRoomView(Model):
    schema_version: Literal['study_rooms.v2'] = 'study_rooms.v2'
    timezone: Literal['America/New_York'] = 'America/New_York'
    phase: Literal['search', 'review', 'submitting', 'confirmed', 'pending', 'cancelled', 'unknown']
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    rooms: Annotated[list[Room], Field(max_length=30)] = Field(default_factory=list)
    total_matching: Annotated[int, Field(ge=0)] = 0
    selection: Selection | None = None
    request_id: RequestID | None = None
    booking: Booking | None = None
    message: Notice | None = None
    source_url: Literal['https://25live.collegenet.com/pro/lehigh'] = 'https://25live.collegenet.com/pro/lehigh'
    map: MapConfig
