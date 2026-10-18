import { useEffect, useMemo, useRef, useState } from "react";
import { GlassSurface } from "../../shared/components/GlassSurface.jsx";
import { MapCanvas } from "../../shared/maps/MapCanvas.jsx";
import { readStudyRoom } from "./tool-result.js";

const date = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "America/New_York" });
const clock = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" });
const local = value => {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "America/New_York" }).formatToParts(new Date(value)).map(p => [p.type, p.value]));
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
};
const when = (start, end) => `${date.format(new Date(start))} · ${clock.format(new Date(start))}–${clock.format(new Date(end))} ET`;
const labels = { search: "Choose a room", review: "Review your request", submitting: "Reserving…", confirmed: "Reserved",
  pending: "Pending confirmation", cancelled: "Cancelled", unknown: "Check booking status" };

export function StudyRoom({ view, token, theme, bridge, onView }) {
  const [selected, setSelected] = useState(null);
  const [name, setName] = useState("Study session");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  const mounted = useRef(true);
  const search = useRef(null);
  const heading = useRef(null);
  useEffect(() => () => { mounted.current = false; }, []);
  useEffect(() => {
    if (view.phase === "search") { search.current = view; setSelected(null); }
    heading.current?.focus({ preventScroll: true });
  }, [view]);
  const room = view.selection?.room || view.rooms.find(item => item.space_id === selected);
  const places = useMemo(() => room ? [room.place] : [...new Map(view.rooms.map(item => [item.place.query, item.place])).values()], [room, view.rooms]);
  const selection = view.selection;
  const start = selection?.starts_at || view.starts_at;
  const end = selection?.ends_at || view.ends_at;

  async function call(tool, args, label) {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(label); setError("");
    try {
      const result = await bridge.callTool(tool, args);
      if (result?.isError) throw new Error(result.content?.find(item => item.type === "text")?.text || "The request failed.");
      const next = readStudyRoom(result?.structuredContent);
      if (mounted.current) {
        onView(next, result._meta);
        bridge.updateModelContext({ status: next.phase, event_id: next.booking?.event_id,
          room: next.selection?.room.name, starts_at: next.selection?.starts_at, ends_at: next.selection?.ends_at }).catch(() => {});
      }
    } catch (reason) {
      if (!mounted.current) return;
      if (tool === "confirm_study_room_booking") {
        onView({ ...view, phase: "unknown", message: "The response was interrupted. Check request status or 25Live before making another booking." });
      } else setError(reason.message || "The request couldn’t finish. Try checking your Lehigh connection.");
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy("");
    }
  }

  return <GlassSurface className="map-card study-rooms">
    <header className="map-heading"><div>
      <h1 ref={heading} tabIndex={-1}>{labels[view.phase]}</h1>
      {start && end && <p>{when(start, end)}</p>}
    </div><span className="room-status">25Live</span></header>
    <MapCanvas places={places} token={token} theme={theme} emptyMessage="No available rooms for this time." />
    {view.phase === "search" && <>
      <fieldset className="room-picker" disabled={Boolean(busy)}>
        <legend className="sr-only">Available rooms</legend>
        {view.rooms.map(item => <label key={item.space_id} className="room-option">
          <input type="radio" name="study-room" value={item.space_id} checked={selected === item.space_id} onChange={() => setSelected(item.space_id)} />
          <span><strong>{item.description || item.name}</strong><small>{item.name}{item.building && ` · ${item.building}`}</small></span>
          {item.capacity > 0 && <small>{item.capacity} seats</small>}
        </label>)}
      </fieldset>
      {!view.rooms.length && <p className="room-note">No rooms are available for this search. Try another time or building in chat.</p>}
      {view.total_matching > view.rooms.length && <p className="room-note">Showing {view.rooms.length} of {view.total_matching} rooms. Ask for a building to narrow the search.</p>}
      {view.rooms.length > 0 && <form onSubmit={event => { event.preventDefault(); if (room && name.trim()) call("prepare_study_room_booking",
        { space_id: room.space_id, start: local(start), end: local(end), event_name: name.trim() }, "Checking availability…"); }}>
        <label className="room-name">Booking name<input value={name} onChange={event => setName(event.target.value)} maxLength={100} required disabled={Boolean(busy)} /></label>
        <div className="room-actions"><button className="room-primary" disabled={!room || !name.trim() || Boolean(busy)}>Review request</button><span>Nothing reserved yet</span></div>
      </form>}
    </>}
    {selection && <div className="room-facts">
      <strong>{selection.room.description || selection.room.name}</strong>
      <p>{selection.room.name}{selection.room.building && ` · ${selection.room.building}`}</p>
      <p>{selection.event_name}</p>
      {view.booking && <p>Event {view.booking.event_id}</p>}
    </div>}
    {view.message && <p className="room-note" role="status">{view.message}</p>}
    {view.phase === "review" && <>
      <p className="room-note">Reserve this room for the time shown above? Availability is checked again when you confirm.</p>
      <div className="room-actions">
        <button className="room-primary" disabled={Boolean(busy)} onClick={() => call("confirm_study_room_booking", { request_id: view.request_id, confirm: true }, "Reserving room…")}>Reserve room</button>
        {search.current && <button disabled={Boolean(busy)} onClick={() => { setError(""); onView(search.current); }}>Back</button>}
      </div>
    </>}
    {!["search", "review"].includes(view.phase) && <div className="room-actions">
      <button disabled={Boolean(busy)} onClick={() => view.request_id
        ? call("get_study_room_request", { request_id: view.request_id }, "Checking status…")
        : call("show_study_room", { event_id: view.booking.event_id }, "Checking status…")}>Check status</button>
      <a href={view.source_url} target="_blank" rel="noopener noreferrer">Open in 25Live ↗</a>
    </div>}
    <div aria-live="polite">{busy && <p className="room-note">{busy}</p>}</div>
    {error && <p className="room-error" role="alert">{error}</p>}
  </GlassSurface>;
}
