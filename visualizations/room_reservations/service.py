"""Adapt Evan's own-events reader without inventing end times or booking status."""
from datetime import date, datetime

import twentyfivelive as live

from .models import Reservation, ReservationsView


def _start(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=live.TIMEZONE)
    except (ValueError, TypeError):
        return None


def get_reservations(from_date: date | None, include_cancelled: bool, page: int, page_size: int) -> ReservationsView:
    data = live.list_events(from_date.isoformat() if from_date else None, include_cancelled, page, page_size)
    events = []
    for row in data['events']:
        status = row.get('status')
        state = (status or '').casefold()
        tone = ('confirmed' if state == 'confirmed' else 'cancelled' if state in ('cancelled', 'canceled')
                else 'pending' if state in ('tentative', 'pending', 'requested', 'draft') else 'unknown')
        events.append(Reservation(event_id=str(row['event_id']), name=row.get('name') or 'Untitled reservation',
                                  reference=row.get('locator'), status=status, tone=tone,
                                  starts_at=_start(row.get('start')), rooms=row.get('rooms') or [], repeats=row.get('repeats')))
    return ReservationsView(from_date=data['from_date'], include_cancelled=include_cancelled,
                            events=events, page=data['page'], pages=data['pages'], page_size=page_size,
                            cancelled_hidden=data.get('cancelled_hidden') or 0)
