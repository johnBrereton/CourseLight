import { mapConfig, place, text } from "../../shared/maps/validate.js";

export function readStudyRoom(view) {
  const fail = () => { throw new Error("Invalid study-room result"); };
  if (!view || view.schema_version !== "study_room.v1" || view.timezone !== "America/New_York" || !mapConfig(view.map)) fail();
  const reservation = view.reservation;
  if (reservation !== null) {
    const timestamp = value => typeof value === "string" && /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
    if (!reservation || !/^[A-Za-z0-9_-]{1,80}$/.test(reservation.id) || !["confirmed", "pending", "cancelled"].includes(reservation.status) ||
        !text(reservation.room) || !place(reservation.place) || !timestamp(reservation.starts_at) || !timestamp(reservation.ends_at) ||
        Date.parse(reservation.ends_at) <= Date.parse(reservation.starts_at)) fail();
    if (reservation.source_url !== null) {
      const source = new URL(reservation.source_url);
      if (source.protocol !== "https:" || source.username || source.password || source.port || !(source.hostname === "25live.collegenet.com" ||
          source.hostname === "lehigh.edu" || source.hostname.endsWith(".lehigh.edu"))) fail();
    }
  }
  return view;
}
