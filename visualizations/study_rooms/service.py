"""Server-held reviews keep the approved room/time fixed and prevent a repeated POST."""
from dataclasses import dataclass
from datetime import datetime
from secrets import token_urlsafe
import re
from threading import Lock
from time import monotonic

import twentyfivelive as live

from ..maps.buildings import building_coordinate
from ..maps.config import map_config
from ..maps.models import MapPlace
from .models import Booking, EASTERN, Room, RoomQuery, Selection, StudyRoomView, eastern


def room_view(row: dict) -> Room:
    name = str(row['name'])
    building = re.sub(r'^\d+[A-Za-z]?\s+', '', row.get('building') or '')
    return Room(space_id=int(row['space_id']), name=name, description=row.get('description') or '',
                building=building, capacity=row.get('capacity') or 0,
                place=MapPlace(id=f"room-{row['space_id']}", name=building or name,
                               query=f'{building or name}, Lehigh University, Bethlehem PA',
                               coordinate=building_coordinate(building)))


def search(query: RoomQuery) -> StudyRoomView:
    data = live.search_rooms(query.start, query.end, query.query, query.min_capacity, False, query.max_results)
    return StudyRoomView(phase='search', starts_at=eastern(query.start), ends_at=eastern(query.end),
                         rooms=[room_view(row) for row in data['rooms'] if row['available']],
                         total_matching=data['total_matching'], map=map_config()[0])


def booking_view(data: dict) -> Booking:
    state = str(data.get('state'))
    active = [room for room in data.get('room_details', []) if str(room.get('reservation_state')) == '1']
    status = 'cancelled' if state == str(live.CANCELLED) else 'pending'
    selection = None
    candidates = active or data.get('room_details', [])
    if candidates:
        row = candidates[0]
        try:
            def timestamp(value):
                parsed = datetime.fromisoformat(value)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=EASTERN)
            start, end = timestamp(row['start']), timestamp(row['end'])
            if end > start:
                selection = Selection(room=room_view(row), starts_at=start, ends_at=end, event_name=data['name'])
        except (ValueError, TypeError, KeyError):
            pass
    if state == str(live.CONFIRMED) and active and selection:
        status = 'confirmed'
    return Booking(event_id=str(data['event_id']), name=data['name'], status=status, selection=selection)


def show_booking(event_id: str) -> StudyRoomView:
    booking = booking_view(live.get_booking(event_id))
    return StudyRoomView(phase=booking.status, booking=booking, selection=booking.selection, map=map_config()[0])


@dataclass
class Review:
    arguments: dict
    account: int
    created: float
    view: StudyRoomView
    event_id: str | None = None


_reviews: dict[str, Review] = {}
_lock = Lock()
REVIEW_TTL = 15 * 60
RESULT_TTL = 24 * 60 * 60
MAX_REVIEWS = 100


def _find(request_id: str) -> Review:
    review = _reviews.get(request_id)
    if review is None:
        raise ValueError('This review is no longer available. Check 25Live for an existing booking before starting again.')
    return review


def prepare(space_id: int, query: RoomQuery, event_name: str) -> StudyRoomView:
    arguments = dict(space_id=space_id, start=query.start, end=query.end, event_name=event_name, favorite=False)
    data = live.book_room(**arguments, confirm=False)
    preview = data['preview']
    selection = Selection(room=room_view(preview), starts_at=eastern(query.start), ends_at=eastern(query.end),
                          event_name=preview['event_name'])
    arguments['event_name'] = selection.event_name
    with _lock:
        now = monotonic()
        for key, saved in list(_reviews.items()):
            ttl = REVIEW_TTL if saved.view.phase == 'review' else RESULT_TTL
            if saved.view.phase != 'submitting' and now - saved.created > ttl:
                del _reviews[key]
        if len(_reviews) >= MAX_REVIEWS:
            raise ValueError('Too many room reviews are active. Try again later.')
        request_id = token_urlsafe(24)
        view = StudyRoomView(phase='review', selection=selection, request_id=request_id, map=map_config()[0])
        _reviews[request_id] = Review(arguments, data['_account_id'], now, view)
        return view.model_copy(deep=True)


def _resolve(review: Review, data: dict) -> StudyRoomView:
    booking = booking_view(data)
    args = review.arguments
    if booking.status == 'confirmed' and not live._matches_booking(data, args['space_id'], args['start'], args['end']):
        booking.status = 'pending'
    return review.view.model_copy(update={'phase': booking.status, 'booking': booking,
                                          'message': None if booking.status != 'pending' else
                                          '25Live has not confirmed this room and time. Check the event before relying on it.'})


def confirm(request_id: str, approved: bool) -> StudyRoomView:
    with _lock:
        review = _find(request_id)
        if not approved or review.view.phase != 'review':
            return review.view.model_copy(deep=True)
        if monotonic() - review.created > REVIEW_TTL:
            raise ValueError('This review expired. Review availability again before reserving.')
        review.view = review.view.model_copy(update={'phase': 'submitting'})
    try:
        data = live.book_room(**review.arguments, confirm=True, expected_contact=review.account)
        if data.get('booking'):
            view = _resolve(review, data['booking'])
            event_id = view.booking.event_id
        else:
            event_id = data.get('event_id')
            view = review.view.model_copy(update={'phase': 'unknown', 'message': data.get('message') or
                                                  'The booking outcome is unknown. Check 25Live before making another request.'})
    except live.TwentyFiveLiveError as exc:
        # Provider validation failed before its POST; approval is consumed either way.
        event_id = None
        view = review.view.model_copy(update={'phase': 'unknown', 'message': str(exc)[:500]})
    except Exception:
        event_id = None
        view = review.view.model_copy(update={'phase': 'unknown', 'message':
                                              'The booking outcome could not be verified. Check 25Live before making another request.'})
    with _lock:
        review.event_id, review.view = event_id, view
        return view.model_copy(deep=True)


def status(request_id: str) -> StudyRoomView:
    with _lock:
        review = _find(request_id)
        event_id = review.event_id
        view = review.view.model_copy(deep=True)
    if event_id:
        data = live.get_booking(event_id)
        view = _resolve(review, data)
        with _lock:
            review.view = view
    return view.model_copy(deep=True)
