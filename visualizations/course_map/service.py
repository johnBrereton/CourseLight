"""Read registered course buildings for the selected week."""
from datetime import timedelta
import re

from ..maps.models import MapPlace
from ..maps.buildings import building_coordinate
from ..schedule.models import ScheduleQuery
from ..schedule.service import get_class_schedule
from .models import ClassStop, CourseMapView, MapDay


def course_map(schedule, on_date, config):
    monday = on_date - timedelta(days=on_date.weekday())
    places, place_ids, records, unavailable = [], {}, [], set()
    for section in schedule.options[0].sections:
        for index, meeting in enumerate(section.meetings):
            stop_id = f'{section.crn}-{index}'
            if meeting.start_minute is None or not meeting.days:
                unavailable.add(section.course)
                continue
            building = re.sub(r'^\d{3}\s+', '', meeting.building).strip()
            place_id = None
            if building and not re.search(r'\b(tba|tbd|online|remote|virtual|determined)\b', building, re.I):
                key = building.casefold()
                if key not in place_ids:
                    place_ids[key] = f'building-{len(places) + 1}'
                    places.append(MapPlace(id=place_ids[key], name=building, coordinate=building_coordinate(building),
                                           query=f'{building}, Lehigh University, Bethlehem, Pennsylvania'))
                place_id = place_ids[key]
            else:
                unavailable.add(section.course)
            location = f'{building} {meeting.room}'.strip() if place_id else meeting.location
            stop = ClassStop(id=stop_id, course=section.course, title=section.title,
                             instructors=section.instructors, location=location,
                             start_minute=meeting.start_minute, end_minute=meeting.end_minute, place_id=place_id)
            records.append((meeting, stop))

    days = []
    for offset, day_code in enumerate('MTWRFSU'):
        day = monday + timedelta(days=offset)
        stops = sorted((stop for meeting, stop in records if day_code in meeting.days
                        and (meeting.start_date is None or meeting.start_date <= day)
                        and (meeting.end_date is None or day <= meeting.end_date)),
                       key=lambda stop: (stop.start_minute, stop.end_minute, stop.id))
        days.append(MapDay(date=day, stops=stops))
    notices = list(schedule.notices)
    if unavailable:
        notices.append('Some classes have unconfirmed times or buildings. Their locations may be unavailable.')
    notices.append('Banner meeting dates are applied; holidays and cancellations are not checked.')
    return CourseMapView(term=schedule.term, term_label=schedule.term_label, selected_date=on_date,
                         fetched_at=schedule.fetched_at,
                         places=places, days=days, map=config, notices=notices)


def get_course_map(term, on_date, config):
    return course_map(get_class_schedule(ScheduleQuery(term=term)), on_date, config)
