# Study rooms

`show_study_rooms(start, end, query=None, min_capacity=0, max_results=12)` renders
`ui://courselight/study_rooms/v2.html`. Start/end are future, same-day local
Eastern times (`YYYY-MM-DDTHH:MM`). Lehigh sign-in supplies the 25Live session.
Apple Maps uses the existing browser-scoped token; rooms still work without it.

The flow is:

1. Search Express-bookable rooms and choose one. Availability is a snapshot.
2. `prepare_study_room_booking` rechecks availability and returns the exact
   room, time, and event name. It writes nothing to 25Live.
3. The user presses **Reserve room**. `confirm_study_room_booking` consumes the
   server-held review and checks availability and the signed-in account again.
4. Read back the event. Only a confirmed event with the requested active room
   and matching start/end times is labeled **Reserved**.

The last three UI tools (prepare, confirm, and `get_study_room_request`) are
app-only. The shared bridge sends `tools/call` requests through the MCP Apps
host; the browser never receives Lehigh cookies or calls 25Live directly.
The card also updates chat context with the outcome and provider event ID so a
later request can refer to the booking.
The confirmation tool is explicitly annotated as a write. Evan's existing
chat-facing search/book/favorite/cancel tools remain available.

Reviews expire after 15 minutes and are tied to the reviewing account. Each
opaque request ID submits at most once in this process, including concurrent
clicks. Completed/uncertain results are retained up to 24 hours in a bounded
in-memory store. A server restart loses these records; an old ID cannot submit.
If a response is interrupted, **Check status** reads the saved outcome and,
when an event ID is known, refreshes it from 25Live. If no ID is known, check
25Live manually before starting another request. This is not provider-level
idempotency across separately created reviews or server restarts.

`show_study_room(event_id)` reads only an event belonging to the signed-in user.
Cancellation remains the existing chat tool: preview the named booking, obtain
approval, then cancel. No bulk actions are added. Maps mark buildings rather
than indoor rooms, and missing building metadata does not hide a booking.

Read in this order: `resource.py` (tools), `models.py` (contracts), `service.py`
(flow), `../../twentyfivelive.py` (provider), then
`../../ui/views/study_rooms/StudyRoom.jsx` (interaction) and
`../../ui/shared/bridge.js` (host calls).
