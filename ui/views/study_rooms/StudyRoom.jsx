import { useMemo } from "react";
import { GlassSurface } from "../../shared/components/GlassSurface.jsx";
import { MapCanvas } from "../../shared/maps/MapCanvas.jsx";

const when = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short", timeZone: "America/New_York" });
const labels = { confirmed: "Reserved", pending: "Pending", cancelled: "Cancelled" };

export function StudyRoom({ view, token, theme }) {
  const reservation = view.reservation;
  const places = useMemo(() => reservation ? [reservation.place] : [], [reservation]);
  return <GlassSurface className="map-card">
    <header className="map-heading"><div><h1>Study room</h1><p>25Live</p></div>
      {reservation && <span className="room-status">{labels[reservation.status]}</span>}
    </header>
    {!reservation ? <div className="map-empty">25Live isn’t connected yet. Confirmed reservations will appear here.</div> : <>
      <MapCanvas places={places} token={token} theme={theme} />
      <div className="room-facts"><strong>{reservation.room} · {reservation.place.name}</strong>
        <p>{when.format(new Date(reservation.starts_at))} – {when.format(new Date(reservation.ends_at))}</p>
        <p>Reservation {reservation.id}</p>
      </div>
      {reservation.source_url && <a className="room-source" href={reservation.source_url} target="_blank" rel="noopener noreferrer">Open in 25Live ↗</a>}
    </>}
  </GlassSurface>;
}
