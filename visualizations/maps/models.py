from typing import Annotated, Literal

from pydantic import Field

from ..schedule.models import Label, Model


class Coordinate(Model):
    latitude: Annotated[float, Field(ge=-90, le=90)]
    longitude: Annotated[float, Field(ge=-180, le=180)]


class MapPlace(Model):
    id: Annotated[str, Field(pattern=r'^[a-z0-9-]{1,60}$')]
    name: Label
    query: Annotated[str, Field(min_length=1, max_length=400)]
    coordinate: Coordinate | None = None


class MapConfig(Model):
    provider: Literal['apple'] = 'apple'
    status: Literal['ready', 'missing_token', 'invalid_token']
