import { array, integer, mapConfig, place, text } from "../../shared/maps/validate.js";

const timestamp = value => typeof value === "string" && /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
const room = value => value && integer(value.space_id, 1, Number.MAX_SAFE_INTEGER) && text(value.name) &&
  typeof value.description === "string" && value.description.length <= 240 && typeof value.building === "string" && value.building.length <= 240 &&
  integer(value.capacity, 0, Number.MAX_SAFE_INTEGER) && place(value.place);
const selection = value => value && room(value.room) && text(value.event_name, 100) && timestamp(value.starts_at) &&
  timestamp(value.ends_at) && Date.parse(value.ends_at) > Date.parse(value.starts_at);

export function readStudyRoom(view) {
  const fail = () => { throw new Error("Invalid study-room result. Ask ChatGPT to refresh this view."); };
  if (!view || view.schema_version !== "study_rooms.v2" || view.timezone !== "America/New_York" || !mapConfig(view.map) ||
      !["search", "review", "submitting", "confirmed", "pending", "cancelled", "unknown"].includes(view.phase) ||
      !array(view.rooms, 30) || !view.rooms.every(room) || !integer(view.total_matching, 0, Number.MAX_SAFE_INTEGER) ||
      view.source_url !== "https://25live.collegenet.com/pro/lehigh") fail();
  if (view.selection !== null && !selection(view.selection)) fail();
  if (view.request_id !== null && (typeof view.request_id !== "string" || !/^[A-Za-z0-9_-]{32}$/.test(view.request_id))) fail();
  if (view.message !== null && !text(view.message, 500)) fail();
  if (view.booking !== null && (!view.booking || !/^\d{1,12}$/.test(view.booking.event_id) || !text(view.booking.name) ||
      !["confirmed", "pending", "cancelled"].includes(view.booking.status) ||
      view.booking.selection !== null && !selection(view.booking.selection))) fail();
  if (view.phase === "search" && (!timestamp(view.starts_at) || !timestamp(view.ends_at) || Date.parse(view.ends_at) <= Date.parse(view.starts_at))) fail();
  if (view.phase === "review" && (!view.selection || !view.request_id)) fail();
  if (!["search", "review"].includes(view.phase) && !view.request_id && !view.booking) fail();
  if (["confirmed", "pending", "cancelled"].includes(view.phase) && view.booking?.status !== view.phase) fail();
  return view;
}
