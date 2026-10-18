# 25Live adapter handoff

This is a scaffold. The HTML resource is registered, but no reservation tool is
exposed until a real reader is supplied. There are no booking or cancellation
requests, invented endpoints, sample confirmations, or stored 25Live credentials.

Implement a server-side `read_reservation(reservation_id) -> RoomReservation`
that reads the authenticated user's reservation from 25Live. Pass that reader to
`register_study_rooms(mcp, read_reservation=...)` in `visualizations/__init__.py`.
It then exposes `show_study_room(reservation_id)`. Keep provider errors safe and
never return raw credentials or response dumps.

The contract in `models.py` needs the provider's ID and status, room label,
building name, a public building search query (or verified coordinates), and
timezone-aware start/end times. Only map a provider status to `confirmed` after
the provider confirms the booking. `pending` and `cancelled` render differently.
An optional source link must point to Lehigh or 25Live. Do not include attendee
names, emails, tokens, or access codes.

For a future booking tool, attach `RESOURCE_URI` in its UI metadata and return
`reservation_result()` using a validated read-back of the successful booking.
The booking tool must declare write annotations and obtain the user's approval
for the actual room and time. Do not reuse this read-only tool to create a booking.

`ui/views/study_rooms/` consumes the contract and reuses
`ui/shared/maps/MapCanvas.jsx`. Without an API response it explicitly says that
25Live is not connected. The shared Apple Maps token setup is documented in
`visualizations/README.md`.
