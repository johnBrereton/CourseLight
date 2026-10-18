from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, Field, field_validator, model_validator

from ..maps.models import MapConfig, MapPlace
from ..schedule.models import Label, Model

ReservationID = Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')]


class RoomReservation(Model):
    id: ReservationID
    status: Literal['confirmed', 'pending', 'cancelled']
    room: Label
    place: MapPlace
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    source_url: str | None = None

    @field_validator('source_url')
    @classmethod
    def trusted_source(cls, value):
        if value is None:
            return value
        url = urlsplit(value)
        host = url.hostname or ''
        if url.scheme != 'https' or url.username or url.password or url.port not in (None, 443) or not (
            host == '25live.collegenet.com' or host == 'lehigh.edu' or host.endswith('.lehigh.edu')
        ):
            raise ValueError('Reservation links must point to Lehigh or 25Live over HTTPS.')
        return value

    @model_validator(mode='after')
    def ordered_times(self):
        if self.ends_at <= self.starts_at:
            raise ValueError('Reservation end must follow its start.')
        return self


class StudyRoomView(Model):
    schema_version: Literal['study_room.v1'] = 'study_room.v1'
    timezone: Literal['America/New_York'] = 'America/New_York'
    reservation: RoomReservation | None
    map: MapConfig
