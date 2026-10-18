from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from ..schedule.models import Label, Model

Page = Annotated[int, Field(ge=1)]
PageSize = Annotated[int, Field(ge=1, le=50)]


class Reservation(Model):
    event_id: Annotated[str, Field(pattern=r'^\d{1,12}$')]
    name: Label
    reference: Annotated[str, Field(max_length=30)] | None = None
    status: Annotated[str, Field(max_length=30)] | None = None
    tone: Literal['confirmed', 'cancelled', 'pending', 'unknown']
    starts_at: AwareDatetime | None
    rooms: Annotated[list[Label], Field(max_length=100)]
    repeats: Annotated[str, Field(max_length=20)] | None = None


class ReservationsView(Model):
    schema_version: Literal['room_reservations.v1'] = 'room_reservations.v1'
    timezone: Literal['America/New_York'] = 'America/New_York'
    from_date: date
    include_cancelled: bool
    events: Annotated[list[Reservation], Field(max_length=50)]
    page: Page
    pages: Annotated[int, Field(ge=0)]
    page_size: PageSize
    cancelled_hidden: Annotated[int, Field(ge=0)] = 0
    source_url: Literal['https://25live.collegenet.com/pro/lehigh'] = 'https://25live.collegenet.com/pro/lehigh'
