"""Building pins from https://www2.lehigh.edu/map, checked 2026-10-18."""
from .models import Coordinate

_BUILDINGS = {
    'building c': (40.600781, -75.362075),
    'linderman library': (40.606577, -75.376961),
    'fairchild martindale library': (40.60907, -75.37805),
    'fairchild-martindale library': (40.60907, -75.37805),
    'e.w. fairchild-martindale library and computing center': (40.60907, -75.37805),
    'business innovation': (40.60855958, -75.37470575),
    'business innovation building': (40.60855958, -75.37470575),
    'packard lab': (40.607799, -75.378957),
    'packard laboratory': (40.607799, -75.378957),
    'rauch business center': (40.608206, -75.373731),
    'sinclair laboratory': (40.609094, -75.377144),
    'sinclair lab': (40.609094, -75.377144),
}


def building_coordinate(name: str) -> Coordinate | None:
    point = _BUILDINGS.get(name.casefold().strip())
    return Coordinate(latitude=point[0], longitude=point[1]) if point else None
