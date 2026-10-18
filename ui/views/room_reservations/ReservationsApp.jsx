import { useCallback, useEffect, useRef, useState } from "react";
import { GlassProvider } from "../../shared/components/GlassSurface.jsx";
import { CourseLightHeader } from "../../shared/components/CourseLightHeader.jsx";
import { Reservations } from "./Reservations.jsx";
import { readReservations } from "./tool-result.js";

export function ReservationsApp({ bridge, onTeardown }) {
  const [view, setView] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const mounted = useRef(true);
  const receive = useCallback(result => { setView(readReservations(result)); setError(""); }, []);
  useEffect(() => {
    mounted.current = true;
    const stop = bridge.start({
      appName: "CourseLight Room Reservations",
      onResult(result) { try { receive(result); } catch { setError("Reservations couldn’t load. Ask ChatGPT to check your Lehigh connection."); } },
      onError(message) { setError(message); },
      onContext(context) { if (["light", "dark"].includes(context.theme)) document.documentElement.dataset.theme = context.theme; },
      onTeardown,
    });
    return () => { mounted.current = false; stop(); };
  }, [bridge, onTeardown, receive]);

  async function load(page, includeCancelled) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError("");
    try {
      const result = await bridge.callTool("show_room_reservations", { from_date: view.from_date,
        page, max_results: view.page_size, include_cancelled: includeCancelled });
      if (result?.isError) throw new Error(result.content?.find(item => item.type === "text")?.text || "Couldn’t refresh reservations.");
      if (mounted.current) receive(result?.structuredContent);
    } catch (reason) {
      if (mounted.current) setError(reason.message || "Couldn’t refresh reservations. Try again.");
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  return <GlassProvider><main className="planner reservations-panel" aria-label="Your room reservations" aria-busy={busy}>
    <CourseLightHeader />
    {!view && !error && <p className="reservations-message" role="status">Reading your reservations…</p>}
    {view && <Reservations view={view} busy={busy} onLoad={load} />}
    {error && <p className="reservations-message" role="alert">{error}</p>}
    <span className="reservations-sr" role="status">{busy ? "Refreshing reservations…" : view ? `${view.events.length} reservations on page ${view.page}` : ""}</span>
  </main></GlassProvider>;
}
