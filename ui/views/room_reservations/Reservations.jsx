import { GlassSurface } from "../../shared/components/GlassSurface.jsx";

const options = { timeZone: "America/New_York" };
const day = new Intl.DateTimeFormat("en-US", { ...options, weekday: "short", month: "short", day: "numeric", year: "numeric" });
const clock = new Intl.DateTimeFormat("en-US", { ...options, hour: "numeric", minute: "2-digit", timeZoneName: "short" });

export function Reservations({ view, busy, onLoad }) {
  const groups = new Map();
  for (const event of view.events) {
    const label = event.starts_at ? day.format(new Date(event.starts_at)) : "Start time unavailable";
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(event);
  }
  return <>
    <div className="reservations-toolbar"><h2>Room reservations</h2>
      <div className="reservations-controls"><label><input type="checkbox" checked={view.include_cancelled} disabled={busy}
        onChange={event => onLoad(1, event.target.checked)} />Include cancelled</label>
        <button type="button" disabled={busy} onClick={() => onLoad(view.page, view.include_cancelled)} aria-label="Refresh reservations" title="Refresh reservations">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 6.1A8 8 0 0 1 20 12M4 12a8 8 0 0 0 13.9 5.9"/></svg>
        </button>
      </div>
    </div>
    {view.events.length ? <div className="reservations-groups">{[...groups].map(([date, events]) => <section key={date} aria-label={date}>
      <h3 className="reservation-date">{date}</h3>
      <ol className="reservations-list">{events.map(event => <li key={event.event_id} className="reservation-card">
        <GlassSurface className="reservation-material" aria-hidden="true" />
        <details>
          <summary>
            <span className="reservation-info"><strong>{event.name}</strong>
              <span>{event.rooms.length ? event.rooms.join(" · ") : "Room not listed"}
                {event.starts_at && <> · <time dateTime={event.starts_at}>{event.repeats ? "First start" : "Starts"} {clock.format(new Date(event.starts_at))}</time></>}
              </span>
            </span>
            <span className={`reservation-status ${event.tone}`}>{event.status || "Status unavailable"}</span>
            <svg className="reservation-chevron" width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="m6 8 4 4 4-4"/></svg>
          </summary>
          <div className="reservation-details">
            <dl><div><dt>Reference</dt><dd>{event.reference || "Not provided"}</dd></div><div><dt>Event ID</dt><dd>{event.event_id}</dd></div>
              {event.repeats && <div><dt>Repeats</dt><dd>{event.repeats}</dd></div>}
            </dl>
            <a href={view.source_url} target="_blank" rel="noopener noreferrer">Open in 25Live ↗</a>
          </div>
        </details>
      </li>)}</ol>
    </section>)}</div> : <p className="reservations-message">{view.cancelled_hidden
      ? `This page only contains cancelled events. Include cancelled events${view.page < view.pages ? " or continue to the next page" : ""}.`
      : `No reservations returned for events ending on or after ${view.from_date}.`}</p>}
    {(view.pages > 1 || view.page > 1) && <nav className="reservations-pagination" aria-label="Reservation pages">
      <button disabled={busy || view.page <= 1} onClick={() => onLoad(view.page - 1, view.include_cancelled)}>Previous</button>
      <span>Page {view.page}{view.pages >= view.page && ` of ${view.pages}`}</span>
      <button disabled={busy || view.page >= view.pages} onClick={() => onLoad(view.page + 1, view.include_cancelled)}>Next</button>
    </nav>}
  </>;
}
