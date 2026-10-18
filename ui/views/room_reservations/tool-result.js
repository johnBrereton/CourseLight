import { array, integer, isoDate, text } from "../../shared/maps/validate.js";

export function readReservations(view) {
  const fail = () => { throw new Error("Invalid reservations result"); };
  if (!view || view.schema_version !== "room_reservations.v1" || view.timezone !== "America/New_York" ||
      !isoDate(view.from_date) || typeof view.include_cancelled !== "boolean" || !array(view.events, 50) ||
      !integer(view.page, 1, Number.MAX_SAFE_INTEGER) || !integer(view.pages, 0, Number.MAX_SAFE_INTEGER) ||
      !integer(view.page_size, 1, 50) || !integer(view.cancelled_hidden, 0, Number.MAX_SAFE_INTEGER) ||
      view.source_url !== "https://25live.collegenet.com/pro/lehigh") fail();
  for (const event of view.events) {
    if (!event || typeof event.event_id !== "string" || !/^\d{1,12}$/.test(event.event_id) || !text(event.name) ||
        !array(event.rooms, 100) || !event.rooms.every(name => text(name)) ||
        !["confirmed", "cancelled", "pending", "unknown"].includes(event.tone) ||
        event.reference !== null && !text(event.reference, 30) || event.status !== null && !text(event.status, 30) ||
        event.repeats !== null && !text(event.repeats, 20)) fail();
    if (event.starts_at !== null && (typeof event.starts_at !== "string" || !/(?:Z|[+-]\d{2}:\d{2})$/.test(event.starts_at) || !Number.isFinite(Date.parse(event.starts_at)))) fail();
  }
  return view;
}
